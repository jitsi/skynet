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


def extract_ratelimit_from_response(response, processor: str) -> None:
    """Extract rate limit headers from LangChain response and update Prometheus metrics."""
    if not hasattr(response, 'response_metadata'):
        return

    headers = response.response_metadata.get('headers', {})
    if not headers:
        return

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
