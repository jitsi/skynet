"""
Customer token usage reporting.

Skynet performs LLM inference (summaries, action items, table of contents,
assistant) on behalf of 8x8 customers. This module captures the number of tokens
each job actually consumes -- as reported by the inference engine itself (OCI,
OpenAI, Azure, or the local model) -- and reports it to AI Studio's usage
registry, which is 8x8's single source of truth for "tokens spent by customers".

Two independent sinks, both best-effort (a failure here must never affect a
summary):

  1. Prometheus (`summary_tokens_total`, labelled by app / processor / customer /
     direction) -- Skynet's own Grafana, available regardless of the AI Studio
     integration.
  2. AI Studio (`POST {AI_STUDIO_USAGE_URL}`) -- one usage event per job, so the
     tokens flow into the same `usage_events` store that feeds the customer-token
     north star. Disabled unless `AI_STUDIO_USAGE_ENABLED` is set.

Token capture uses a LangChain callback (`UsageCollector`) attached to every
model in `LLMSelector.select`, mirroring the existing `RateLimitCallbackHandler`
pattern. The collector is shared for the duration of a job via a `ContextVar`, so
map-reduce fan-out and the language-detection / assistant sub-calls all accumulate
into one total.
"""

import asyncio
from contextvars import ContextVar
from typing import Any, Optional

import aiohttp

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

from skynet.env import (
    ai_studio_usage_channel,
    ai_studio_usage_enabled,
    ai_studio_usage_timeout,
    ai_studio_usage_token,
    ai_studio_usage_url,
)
from skynet.logs import get_logger
from skynet.modules.monitoring import SUMMARY_TOKENS_METRIC

log = get_logger(__name__)


def _extract_usage(response: LLMResult) -> tuple[int, int, Optional[str]]:
    """Pull (input_tokens, output_tokens, model) out of an LLM response.

    Prefers LangChain's provider-agnostic `usage_metadata` on the message; falls
    back to the OpenAI-style `llm_output.token_usage`. Returns zeros when the
    engine reported no usage (e.g. a provider that doesn't surface it).
    """

    input_tokens = 0
    output_tokens = 0
    model: Optional[str] = None

    for generations in response.generations or []:
        for generation in generations:
            message = getattr(generation, 'message', None)
            if message is None:
                continue

            usage = getattr(message, 'usage_metadata', None)
            if usage:
                input_tokens += usage.get('input_tokens', 0) or 0
                output_tokens += usage.get('output_tokens', 0) or 0

            metadata = getattr(message, 'response_metadata', None) or {}
            model = model or metadata.get('model_name') or metadata.get('model')

    # Fallback: OpenAI-style token_usage on llm_output (older / non-standardised responses).
    if not input_tokens and not output_tokens and response.llm_output:
        token_usage = response.llm_output.get('token_usage') or response.llm_output.get('usage') or {}
        input_tokens = token_usage.get('prompt_tokens', 0) or 0
        output_tokens = token_usage.get('completion_tokens', 0) or 0
        model = model or response.llm_output.get('model_name')

    return input_tokens, output_tokens, model


class UsageCollector(BaseCallbackHandler):
    """Accumulates token usage across every LLM call made while processing one job.

    Increments the Prometheus counter per call and totals input/output tokens so
    the job runner can report a single usage event once the job completes.
    """

    def __init__(self, app_id: Optional[str], customer_id: Optional[str], processor: Optional[str]):
        self.app_id = app_id or 'unknown'
        self.customer_id = customer_id or 'unknown'
        self.processor = processor or 'unknown'
        self.input_tokens = 0
        self.output_tokens = 0
        self.model: Optional[str] = None

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        # Never let token accounting break inference: a malformed / unexpected
        # response must be swallowed, not raised back into the LLM call.
        try:
            input_tokens, output_tokens, model = _extract_usage(response)

            if model and not self.model:
                self.model = model

            if not input_tokens and not output_tokens:
                return

            self.input_tokens += input_tokens
            self.output_tokens += output_tokens

            if input_tokens:
                SUMMARY_TOKENS_METRIC.labels(self.app_id, self.processor, self.customer_id, 'input').inc(input_tokens)
            if output_tokens:
                SUMMARY_TOKENS_METRIC.labels(self.app_id, self.processor, self.customer_id, 'output').inc(output_tokens)
        except Exception as e:  # pragma: no cover - defensive
            log.warning(f'Failed to record token usage: {e}')


# The collector for the job currently being processed on this async task. Set by
# the job runner; read by LLMSelector.select so every model call is captured
# without threading the collector through the processing functions.
_current_collector: ContextVar[Optional[UsageCollector]] = ContextVar('skynet_usage_collector', default=None)


def set_usage_collector(collector: UsageCollector):
    """Install the collector for the current job; returns a token for reset."""
    return _current_collector.set(collector)


def reset_usage_collector(token) -> None:
    _current_collector.reset(token)


def attach_usage_callback(model):
    """Attach the current job's collector to a model so its calls are counted.

    No-op when there's no active collector (e.g. calls outside a job). Best-effort
    -- a failure to attach must never break inference.
    """
    collector = _current_collector.get()
    if collector is not None:
        try:
            model.callbacks = [*(model.callbacks or []), collector]
        except Exception as e:  # pragma: no cover - defensive
            log.warning(f'Failed to attach usage callback: {e}')
    return model


async def report_usage_to_ai_studio(
    *,
    customer_id: Optional[str],
    app_id: Optional[str],
    job_id: str,
    event_type: str,
    provider: str,
    model: Optional[str],
    input_tokens: int,
    output_tokens: int,
) -> None:
    """Report one job's token usage to AI Studio's usage registry (best-effort).

    Never raises: token reporting is telemetry, not part of the summary contract.
    """

    if not ai_studio_usage_enabled:
        return

    if not ai_studio_usage_url or not ai_studio_usage_token:
        log.warning('AI_STUDIO_USAGE_ENABLED is set but AI_STUDIO_USAGE_URL / AI_STUDIO_USAGE_TOKEN is missing')
        return

    # No customer id means we can't attribute the spend -- skip rather than send
    # an unattributed row (the north star counts per customer).
    if not customer_id:
        log.debug(f'Skipping AI Studio usage report for job {job_id}: no customer id')
        return

    if not input_tokens and not output_tokens:
        return

    payload = {
        'tenant_id': customer_id,
        'channel': ai_studio_usage_channel,
        'provider': provider,
        'model': model or 'unknown',
        'event_type': event_type,
        'agent_name': app_id,  # carries the calling app (meetings / cc / jaas) for later splitting
        'interaction_id': job_id,
        'input_tokens': input_tokens,
        'output_tokens': output_tokens,
    }

    try:
        result = await http_post(payload)
        if not (isinstance(result, dict) and result.get('success')):
            log.warning(f'AI Studio usage report not accepted for job {job_id}: {result}')
    except Exception as e:
        log.warning(f'AI Studio usage report failed for job {job_id}: {e}')


async def http_post(payload: dict) -> Any:
    """POST a usage event to AI Studio. Split out so tests can stub the network."""
    from skynet import http_client

    return await http_client.post(
        ai_studio_usage_url,
        json=payload,
        headers={'Authorization': f'Bearer {ai_studio_usage_token}'},
        timeout=aiohttp.ClientTimeout(total=ai_studio_usage_timeout),
    )


# Fire-and-forget bookkeeping so a scheduled report task isn't garbage-collected
# before it runs (see https://docs.python.org/3/library/asyncio-task.html#asyncio.create_task).
_pending_reports: set = set()


def schedule_usage_report(**kwargs) -> None:
    """Fire-and-forget `report_usage_to_ai_studio` without blocking the job runner."""
    task = asyncio.create_task(report_usage_to_ai_studio(**kwargs))
    _pending_reports.add(task)
    task.add_done_callback(_pending_reports.discard)
