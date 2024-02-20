import os
import sys

is_mac = sys.platform == 'darwin'

# general
log_level = os.environ.get('LOG_LEVEL', 'DEBUG').strip().upper()
supported_modules = {'summaries:dispatcher', 'summaries:executor', 'openai-api', 'streaming_whisper'}
enabled_modules = set(os.environ.get('ENABLED_MODULES', 'summaries:dispatcher,summaries:executor').split(','))
modules = supported_modules.intersection(enabled_modules)

# models
llama_path = os.environ.get('LLAMA_PATH')
llama_n_gpu_layers = int(os.environ.get('LLAMA_N_GPU_LAYERS', 1 if is_mac else 40))
llama_n_batch = int(os.environ.get('LLAMA_N_BATCH', 512))


# auth
bypass_auth = os.environ.get('BYPASS_AUTHORIZATION', "False").lower() == 'true'
asap_pub_keys_url = os.getenv('ASAP_PUB_KEYS_REPO_URL', None)
asap_pub_keys_folder = os.getenv('ASAP_PUB_KEYS_FOLDER', None)
asap_pub_keys_auds = os.getenv('ASAP_PUB_KEYS_AUDS', '').strip().split(',')
asap_pub_keys_max_cache_size = int(os.environ.get('ASAP_PUB_KEYS_MAX_CACHE_SIZE', 512))

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


# modules > stt > streaming_whisper
whisper_beam_size = int(os.getenv('BEAM_SIZE', 1))
whisper_model_name = os.getenv('WHISPER_MODEL_NAME', None)
# https://opennmt.net/CTranslate2/quantization.html
whisper_compute_type = os.getenv('WHISPER_COMPUTE_TYPE', 'int8')
whisper_gpu_indices = os.getenv('WHISPER_GPU_INDICES', None)
whisper_device = os.getenv('WHISPER_DEVICE', 'auto')
whisper_model_path = os.getenv('WHISPER_MODEL_PATH', f'{os.getcwd()}/models/streaming_whisper')
whisper_return_transcribed_audio = os.getenv('WHISPER_RETURN_TRANSCRIBED_AUDIO', 'false').lower().strip() == 'true'
# whisper_max_connections = int(os.getenv('WHISPER_MAX_CONNECTIONS', 10))


# jobs
job_timeout = int(os.environ.get('JOB_TIMEOUT', 60 * 10))  # 10 minutes default

# summaries
summary_minimum_payload_length = int(os.environ.get('SUMMARY_MINIMUM_PAYLOAD_LENGTH', 100))

# monitoring
enable_metrics = os.environ.get('ENABLE_METRICS', 'true').lower() == 'true'
