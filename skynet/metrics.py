from fastapi import FastAPI

from skynet.env import enable_metrics, modules
from skynet.logs import get_logger

from skynet.modules.monitoring import (
    SUMMARY_QUEUE_SIZE_METRIC,
    instrumentator,
    PROMETHEUS_NAMESPACE,
    PROMETHEUS_SUMMARIES_SUBSYSTEM,
    PROMETHEUS_OPENAI_API_SUBSYSTEM,
)

log = get_logger('skynet.metrics')

metrics = FastAPI()

if enable_metrics:

    @metrics.get('/healthz')
    def health():
        '''
        Health checking.
        '''

        return {'status': 'ok'}

    @metrics.get('/metrics/autoscaler')
    def autoscaler_metrics():
        '''
        Metrics required for the autoscaler.
        '''

        return {'queueSize': int(SUMMARY_QUEUE_SIZE_METRIC._value.get())}

    if 'openai-api' in modules:
        from skynet.modules.ttt.openai_api.app import app as openai_api_app

        instrumentator.instrument(
            openai_api_app, metric_namespace=PROMETHEUS_NAMESPACE, metric_subsystem=PROMETHEUS_OPENAI_API_SUBSYSTEM
        ).expose(metrics)

    if 'summaries' in modules:
        from skynet.modules.ttt.summaries.app import app as summaries_app

        instrumentator.instrument(
            summaries_app, metric_namespace=PROMETHEUS_NAMESPACE, metric_subsystem=PROMETHEUS_SUMMARIES_SUBSYSTEM
        ).expose(metrics)
