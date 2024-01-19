from fastapi import FastAPI

from skynet.env import enable_metrics, modules
from skynet.logs import get_logger
from skynet.modules.monitoring import (
    instrumentator,
    PROMETHEUS_NAMESPACE,
    PROMETHEUS_OPENAI_API_SUBSYSTEM,
    PROMETHEUS_STREAMING_WHISPER_SUBSYSTEM,
    PROMETHEUS_SUMMARIES_SUBSYSTEM,
)
from skynet.modules.ttt.summaries.jobs import PENDING_JOBS_KEY
from skynet.modules.ttt.summaries.persistence import db

log = get_logger(__name__)
metrics = FastAPI()

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

        queue_size = await db.llen(PENDING_JOBS_KEY)
        return {'queueSize': queue_size}

    if 'openai-api' in modules:
        from skynet.modules.ttt.openai_api.app import app as openai_api_app

        instrumentator.instrument(
            openai_api_app, metric_namespace=PROMETHEUS_NAMESPACE, metric_subsystem=PROMETHEUS_OPENAI_API_SUBSYSTEM
        ).expose(metrics)

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
