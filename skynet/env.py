import os
import sys
import uuid

app_uuid = str(uuid.uuid4())

is_mac = sys.platform == 'darwin'


# utilities
def tobool(val: str | None):
    if val is None:
        return False
    val = val.lower().strip()
    if val in ['y', 'yes', 'true', '1']:
        return True
    return False


# general
log_level = os.environ.get('LOG_LEVEL', 'DEBUG').strip().upper()
supported_modules = {'summaries:dispatcher', 'summaries:executor', 'openai-api', 'streaming_whisper'}
enabled_modules = set(os.environ.get('ENABLED_MODULES', 'summaries:dispatcher,summaries:executor').split(','))
modules = supported_modules.intersection(enabled_modules)
file_refresh_interval = int(os.environ.get('FILE_REFRESH_INTERVAL', 30))

# models

# Some formats are auto-detected: https://github.com/abetlen/llama-cpp-python/blob/c50d3300d2a09c98765be7f2c05b7e4fd0b4232e/llama_cpp/llama_chat_format.py#L724
model_chat_format = os.environ.get('MODEL_CHAT_FORMAT')
llama_path = os.environ.get('LLAMA_PATH')
llama_n_ctx = int(os.environ.get('LLAMA_N_CTX', 8192))
llama_n_gpu_layers = int(os.environ.get('LLAMA_N_GPU_LAYERS', -1 if is_mac else 40))
llama_n_batch = int(os.environ.get('LLAMA_N_BATCH', 512))

# openai api
openai_api_base_url = os.environ.get('OPENAI_API_BASE_URL', 'http://localhost:8000/openai-api/v1')

# openai
openai_credentials_file = os.environ.get('SKYNET_CREDENTIALS_PATH')

# auth
bypass_auth = tobool(os.environ.get('BYPASS_AUTHORIZATION'))
asap_pub_keys_url = os.environ.get('ASAP_PUB_KEYS_REPO_URL')
asap_pub_keys_folder = os.environ.get('ASAP_PUB_KEYS_FOLDER')
asap_pub_keys_auds = os.environ.get('ASAP_PUB_KEYS_AUDS', '').strip().split(',')
asap_pub_keys_max_cache_size = int(os.environ.get('ASAP_PUB_KEYS_MAX_CACHE_SIZE', 512))

if not bypass_auth and not asap_pub_keys_url:
    raise RuntimeError('The ASAP public keys repo url must be set')


# redis
redis_exp_seconds = int(os.environ.get('REDIS_EXP_SECONDS', 60 * 30))  # 30 minutes default
redis_host = os.environ.get('REDIS_HOST', 'localhost')
redis_port = int(os.environ.get('REDIS_PORT', 6379))
redis_use_tls = tobool(os.environ.get('REDIS_USE_TLS'))
redis_db_no = int(os.environ.get('REDIS_DB_NO', 0))
redis_usr = os.environ.get('REDIS_USR')
redis_pwd = os.environ.get('REDIS_PWD')
redis_aws_secret_id = os.environ.get('REDIS_AWS_SECRET_ID', '')
redis_use_secrets_manager = tobool(os.environ.get('REDIS_USE_SECRETS_MANAGER'))
redis_namespace = os.environ.get('REDIS_NAMESPACE', 'skynet')
redis_aws_region = os.environ.get('REDIS_AWS_REGION', 'us-west-2')


# modules > stt > streaming_whisper
whisper_beam_size = int(os.environ.get('BEAM_SIZE', 1))
whisper_model_name = os.environ.get('WHISPER_MODEL_NAME')
# https://opennmt.net/CTranslate2/quantization.html
whisper_compute_type = os.environ.get('WHISPER_COMPUTE_TYPE', 'int8')
whisper_gpu_indices = os.environ.get('WHISPER_GPU_INDICES')
whisper_device = os.environ.get('WHISPER_DEVICE', 'auto')
whisper_model_path = os.environ.get('WHISPER_MODEL_PATH', f'{os.getcwd()}/models/streaming_whisper')
whisper_return_transcribed_audio = tobool(os.environ.get('WHISPER_RETURN_TRANSCRIBED_AUDIO'))
whisper_max_connections = int(os.environ.get('WHISPER_MAX_CONNECTIONS', 10))
ws_max_size_bytes = int(os.environ.get('WS_MAX_SIZE_BYTES', 1000000))
ws_max_queue_size = int(os.environ.get('WS_MAX_QUEUE_SIZE', 3000))
ws_max_ping_interval = int(os.environ.get('WS_MAX_PING_INTERVAL', 30))
ws_max_ping_timeout = int(os.environ.get('WS_MAX_PING_TIMEOUT', 30))


# jobs
job_timeout = int(os.environ.get('JOB_TIMEOUT', 60 * 10))  # 10 minutes default

# summaries
summary_default_hint_type = os.environ.get('SUMMARY_DEFAULT_HINT_TYPE', 'text')
summary_minimum_payload_length = int(os.environ.get('SUMMARY_MINIMUM_PAYLOAD_LENGTH', 100))

# monitoring
enable_metrics = tobool(os.environ.get('ENABLE_METRICS', 'true'))

# load balancing
enable_haproxy_agent = tobool(os.environ.get('ENABLE_HAPROXY_AGENT'))
