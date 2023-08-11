import os
import sys
from logging import Filter, LogRecord

is_mac = sys.platform == 'darwin'

llama_path = os.environ.get('LLAMA_PATH')

# auth
bypass_auth = os.environ.get('BYPASS_AUTHORIZATION', "False").lower() == 'true'
asap_pub_keys_url = os.getenv('ASAP_PUB_KEYS_REPO_URL', None)

if not bypass_auth and not asap_pub_keys_url:
    raise RuntimeError('The ASAP public keys repo url must be set')

llama_n_gpu_layers = int(os.environ.get('LLAMA_N_GPU_LAYERS', 1 if is_mac else 40))
llama_n_batch = int(os.environ.get('LLAMA_N_BATCH', 512))


# suppress some logs
class AccessLogSuppressor(Filter):

    exclude_paths = (
        '/healthz',
        '/metrics'
    )

    def filter(self, record: LogRecord) -> bool:
        log_msg = record.getMessage()
        is_excluded = any(excluded in log_msg for excluded in self.exclude_paths)
        return False if is_excluded else True
