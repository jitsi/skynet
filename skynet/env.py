import os
import sys

is_mac = sys.platform == 'darwin'

# apps
enabled_apps = set(os.environ.get('ENABLED_APPS', 'openai-api,summaries').split(','))

# models
llama_path = os.environ.get('LLAMA_PATH')
llama_n_gpu_layers = int(os.environ.get('LLAMA_N_GPU_LAYERS', 1 if is_mac else 40))
llama_n_batch = int(os.environ.get('LLAMA_N_BATCH', 512))


# auth
bypass_auth = os.environ.get('BYPASS_AUTHORIZATION', "False").lower() == 'true'
asap_pub_keys_url = os.getenv('ASAP_PUB_KEYS_REPO_URL', None)
asap_pub_keys_folder = os.getenv('ASAP_PUB_KEYS_FOLDER', None)
asap_pub_keys_auds = os.getenv('ASAP_PUB_KEYS_AUDS', '').strip().split(',')

if not bypass_auth and not asap_pub_keys_url:
    raise RuntimeError('The ASAP public keys repo url must be set')


# redis
redis_exp_seconds = int(os.environ.get('REDIS_EXP_SECONDS', 60 * 30))  # 30 minutes default
redis_host = os.environ.get('REDIS_HOST', 'localhost')
redis_port = int(os.environ.get('REDIS_PORT', 6379))
redis_use_tls = os.environ.get('REDIS_USE_TLS', 'false').lower().strip() == 'true'
redis_db_no = int(os.environ.get('REDIS_DB_NO', 0))
redis_usr = os.environ.get('REDIS_USR', None)
redis_pwd = os.environ.get('REDIS_PWD', None)
redis_aws_secret_id = os.environ.get('REDIS_AWS_SECRET_ID', '')
redis_use_secrets_manager = os.environ.get('REDIS_USE_SECRETS_MANAGER', 'false').lower().strip() == 'true'
redis_namespace = os.environ.get('REDIS_NAMESPACE', 'skynet')
redis_aws_region = os.environ.get('REDIS_AWS_REGION', 'us-west-2')


# monitoring
enable_metrics = os.environ.get('ENABLE_METRICS', 'true').lower() == 'true'
