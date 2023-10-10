from prometheus_fastapi_instrumentator import Instrumentator, metrics
from prometheus_client import Histogram

PROMETHEUS_NAMESPACE = 'Skynet'
PROMETHEUS_SUMMARIES_SUBSYSTEM = 'Summaries'
PROMETHEUS_OPENAI_API_SUBSYSTEM = 'OpenAI_API'
SUMMARY_DURATION_METRIC = Histogram(
    'summary_duration_seconds',
    documentation='Measures the duration of the summary / action items inference in seconds',
    namespace=PROMETHEUS_NAMESPACE,
    subsystem=PROMETHEUS_SUMMARIES_SUBSYSTEM,
    buckets=[5**n for n in range(4)],
)

instrumentator = Instrumentator(
    excluded_handlers=["/healthz", "/metrics"],
)

instrumentator.add(
    metrics.latency(buckets=[n for n in range(1, 6)]),
)
