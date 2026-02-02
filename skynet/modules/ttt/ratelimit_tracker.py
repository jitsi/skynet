from typing import Any, Optional

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

from skynet.env import default_customer_id
from skynet.logs import get_logger
from skynet.modules.monitoring import (
    OPENAI_RATELIMIT_LIMIT_REQUESTS,
    OPENAI_RATELIMIT_LIMIT_TOKENS,
    OPENAI_RATELIMIT_REMAINING_REQUESTS,
    OPENAI_RATELIMIT_REMAINING_TOKENS,
)

log = get_logger(__name__)


def should_track_ratelimit(customer_id: str) -> bool:
    """Only track rate limits for system's own API key (default customer)."""
    return default_customer_id is not None and customer_id == default_customer_id


class RateLimitCallbackHandler(BaseCallbackHandler):
    """Callback handler to capture rate limit headers from LLM responses."""

    def __init__(self, processor: str):
        self.processor = processor

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Called when LLM finishes. Extract rate limit headers from response."""
        if not response.generations:
            return

        # Get the first generation's message (if available)
        for generation_list in response.generations:
            for generation in generation_list:
                if hasattr(generation, 'message') and hasattr(generation.message, 'response_metadata'):
                    headers = generation.message.response_metadata.get('headers', {})
                    if headers:
                        _update_ratelimit_metrics(headers, self.processor)
                        return


def get_ratelimit_callback(processor: str) -> RateLimitCallbackHandler:
    """Get a callback handler for tracking rate limits."""
    return RateLimitCallbackHandler(processor)


def extract_ratelimit_from_response(response, processor: str) -> None:
    """Extract rate limit headers from LangChain response and update Prometheus metrics."""
    if not hasattr(response, 'response_metadata'):
        return

    headers = response.response_metadata.get('headers', {})
    if not headers:
        return

    _update_ratelimit_metrics(headers, processor)


def _update_ratelimit_metrics(headers: dict, processor: str) -> None:
    """Update Prometheus metrics from rate limit headers."""
    _set_gauge(OPENAI_RATELIMIT_REMAINING_REQUESTS, headers.get('x-ratelimit-remaining-requests'), processor)
    _set_gauge(OPENAI_RATELIMIT_LIMIT_REQUESTS, headers.get('x-ratelimit-limit-requests'), processor)
    _set_gauge(OPENAI_RATELIMIT_REMAINING_TOKENS, headers.get('x-ratelimit-remaining-tokens'), processor)
    _set_gauge(OPENAI_RATELIMIT_LIMIT_TOKENS, headers.get('x-ratelimit-limit-tokens'), processor)


def _set_gauge(gauge, value, processor: str) -> None:
    """Safely set a gauge value, handling None and invalid values."""
    if value is None:
        return

    try:
        gauge.labels(processor=processor).set(int(value))
    except (ValueError, TypeError):
        log.warning(f'Invalid gauge value: {value}')
