import logging
import sys

from logging import Filter, LogRecord
from uvicorn.logging import DefaultFormatter


# Suppress some logs from uvicorn
class AccessLogSuppressor(Filter):
    exclude_paths = ('/favicon.ico', '/healthz', '/metrics')

    def filter(self, record: LogRecord) -> bool:
        log_msg = record.getMessage()
        is_excluded = any(excluded in log_msg for excluded in self.exclude_paths)

        return not is_excluded


logging.getLogger('uvicorn.access').addFilter(AccessLogSuppressor())


sh = logging.StreamHandler(sys.stdout)
sh.setFormatter(DefaultFormatter('%(asctime)s %(name)s %(levelprefix)s %(message)s'))

logging.basicConfig(level=logging.INFO, handlers=[sh])


def get_logger(name):
    return logging.getLogger(name)


# Modified from the defaults in uvicorn.config.LOGGING_CONFIG
uvicorn_log_config = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            '()': 'uvicorn.logging.DefaultFormatter',
            'fmt': '%(asctime)s %(name)s %(levelprefix)s %(message)s',
            'use_colors': None,
        },
        'access': {
            '()': 'uvicorn.logging.AccessFormatter',
            'fmt': '%(asctime)s %(name)s %(levelprefix)s %(client_addr)s - "%(request_line)s" %(status_code)s',
        },
    },
    'handlers': {
        'default': {'formatter': 'default', 'class': 'logging.StreamHandler', 'stream': 'ext://sys.stdout'},
        'access': {'formatter': 'access', 'class': 'logging.StreamHandler', 'stream': 'ext://sys.stdout'},
    },
    'loggers': {
        'uvicorn': {'handlers': ['default'], 'level': 'DEBUG', 'propagate': False},
        'uvicorn.error': {'level': 'DEBUG'},
        'uvicorn.access': {'handlers': ['access'], 'level': 'DEBUG', 'propagate': False},
    },
}
