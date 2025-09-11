from skynet.constants import (
    PENDING_JOBS_AZURE_KEY,
    PENDING_JOBS_LOCAL_KEY,
    PENDING_JOBS_OCI_KEY,
    PENDING_JOBS_OPENAI_KEY,
)
from skynet.env import enable_metrics, modules
from skynet.logs import get_logger
from skynet.modules.monitoring import (
    instrumentator,
    PROMETHEUS_NAMESPACE,
    PROMETHEUS_STREAMING_WHISPER_SUBSYSTEM,
    PROMETHEUS_SUMMARIES_SUBSYSTEM,
)
from skynet.modules.ttt.persistence import db
from skynet.utils import create_app

log = get_logger(__name__)
metrics = create_app()

if enable_metrics:

    @metrics.get('/healthz')
    def health():
        '''
        Health checking.
        '''

        return {'status': 'ok'}

    @metrics.get('/metrics/autoscaler')
    async def autoscaler_metrics():
        '''
        Metrics required for the autoscaler.
        '''

        # Sum up queue sizes from all processor-specific queues
        total_queue_size = 0
        for queue_key in [
            PENDING_JOBS_OPENAI_KEY,
            PENDING_JOBS_AZURE_KEY,
            PENDING_JOBS_OCI_KEY,
            PENDING_JOBS_LOCAL_KEY,
        ]:
            queue_size = await db.llen(queue_key)
            total_queue_size += queue_size

        return {'queueSize': total_queue_size}

    if 'summaries:dispatcher' in modules:
        from skynet.modules.ttt.summaries.app import app as summaries_app

        instrumentator.instrument(
            summaries_app, metric_namespace=PROMETHEUS_NAMESPACE, metric_subsystem=PROMETHEUS_SUMMARIES_SUBSYSTEM
        ).expose(metrics)

    if 'streaming_whisper' in modules:
        from skynet.modules.stt.streaming_whisper.app import app as streaming_whisper_app

        instrumentator.instrument(
            streaming_whisper_app,
            metric_namespace=PROMETHEUS_NAMESPACE,
            metric_subsystem=PROMETHEUS_STREAMING_WHISPER_SUBSYSTEM,
        ).expose(metrics)
