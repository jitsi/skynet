from prometheus_fastapi_instrumentator import Instrumentator, metrics
from prometheus_client import Gauge, Histogram

PROMETHEUS_NAMESPACE = 'Skynet'
PROMETHEUS_SUMMARIES_SUBSYSTEM = 'Summaries'
PROMETHEUS_OPENAI_API_SUBSYSTEM = 'OpenAI_API'

SUMMARY_INPUT_LENGTH_METRIC = Histogram(
    'summary_input_length',
    documentation='Measures the length of the input text',
    namespace=PROMETHEUS_NAMESPACE,
    subsystem=PROMETHEUS_SUMMARIES_SUBSYSTEM,
    buckets=[50, 100, 500, 1000, 2000, 5000, 10000],
)

SUMMARY_DURATION_METRIC = Histogram(
    'summary_duration_seconds',
    documentation='Measures the duration of the summary / action items inference in seconds',
    namespace=PROMETHEUS_NAMESPACE,
    subsystem=PROMETHEUS_SUMMARIES_SUBSYSTEM,
    buckets=[5**n for n in range(4)],
)

SUMMARY_TIME_IN_QUEUE_METRIC = Histogram(
    'summary_queue_time_seconds',
    documentation='Measures the time spent in the queue in seconds',
    namespace=PROMETHEUS_NAMESPACE,
    subsystem=PROMETHEUS_SUMMARIES_SUBSYSTEM,
    buckets=[5**n for n in range(4)],
)

SUMMARY_QUEUE_SIZE_METRIC = Gauge(
    'summary_queue_size',
    documentation='Number of jobs in the queue',
    namespace=PROMETHEUS_NAMESPACE,
    subsystem=PROMETHEUS_SUMMARIES_SUBSYSTEM,
)

instrumentator = Instrumentator(
    excluded_handlers=["/healthz", "/metrics"],
)

instrumentator.add(
    metrics.latency(buckets=[n for n in range(1, 6)]),
)
