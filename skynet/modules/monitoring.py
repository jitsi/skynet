from prometheus_client import Counter, Gauge, Histogram
from prometheus_fastapi_instrumentator import Instrumentator, metrics

PROMETHEUS_NAMESPACE = 'Skynet'
PROMETHEUS_SUMMARIES_SUBSYSTEM = 'Summaries'
PROMETHEUS_STREAMING_WHISPER_SUBSYSTEM = 'Streaming_Whisper'

REDIS_CONNECTION_STATUS = Gauge(
    'redis_connection_status',
    documentation='Status of the connection to Redis',
    namespace=PROMETHEUS_NAMESPACE,
    subsystem=PROMETHEUS_SUMMARIES_SUBSYSTEM,
)

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
    labelnames=['app_id'],
)

SUMMARY_FULL_DURATION_METRIC = Histogram(
    'summary_full_duration_seconds',
    documentation='Measures the duration of the summary / action items since they were submitted until they are done in seconds',
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

SUMMARY_ERROR_COUNTER = Counter(
    'summary_errors',
    documentation='Number of jobs that have failed',
    namespace=PROMETHEUS_NAMESPACE,
    subsystem=PROMETHEUS_SUMMARIES_SUBSYSTEM,
)

CONNECTIONS_METRIC = Gauge(
    'LiveWsConnections',
    documentation='Number of active WS connections',
    namespace=PROMETHEUS_NAMESPACE,
    subsystem=PROMETHEUS_STREAMING_WHISPER_SUBSYSTEM,
)

TRANSCRIBE_STRESS_LEVEL_METRIC = Gauge(
    'stress_level',
    documentation='Whisper stress level',
    namespace=PROMETHEUS_NAMESPACE,
    subsystem=PROMETHEUS_STREAMING_WHISPER_SUBSYSTEM,
)

TRANSCRIBE_CONNECTIONS_COUNTER = Counter(
    'LiveWsConnectionsCounter',
    documentation='Number of active WS connections',
    namespace=PROMETHEUS_NAMESPACE,
    subsystem=PROMETHEUS_STREAMING_WHISPER_SUBSYSTEM,
)

TRANSCRIBE_DURATION_METRIC = Histogram(
    'WhisperTranscriptionDuration',
    documentation='Measures the duration of the transcription process in seconds',
    namespace=PROMETHEUS_NAMESPACE,
    subsystem=PROMETHEUS_STREAMING_WHISPER_SUBSYSTEM,
    buckets=[x / 10.0 for x in range(1, 31)],
)

OPENAI_API_RESTART_COUNTER = Counter(
    'forced_exit',
    documentation='Number of restarts of the OpenAI API server',
    namespace=PROMETHEUS_NAMESPACE,
    subsystem=PROMETHEUS_SUMMARIES_SUBSYSTEM,
)

instrumentator = Instrumentator(
    excluded_handlers=["/healthz", "/metrics"],
)

instrumentator.add(
    metrics.latency(buckets=[n for n in range(1, 6)]),
    metrics.requests(metric_namespace=PROMETHEUS_NAMESPACE, metric_subsystem=PROMETHEUS_SUMMARIES_SUBSYSTEM),
)
