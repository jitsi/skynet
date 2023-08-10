import os
import sys

is_mac = sys.platform == 'darwin'

llama_path = os.environ.get('LLAMA_PATH')

# auth
bypass_auth = os.environ.get('BYPASS_AUTHORIZATION', "False").lower() == 'true'
asap_pub_keys_url = os.getenv('ASAP_PUB_KEYS_REPO_URL', None)

if not bypass_auth and not asap_pub_keys_url:
    raise RuntimeError('The ASAP public keys repo url must be set')

llama_n_gpu_layers = os.environ.get('LLAMA_N_GPU_LAYERS', 1 if is_mac else 40)
llama_n_batch = os.environ.get('LLAMA_N_BATCH', 512)
