# autoflake: skip_file

import os
import sys
import uuid

import torch

app_uuid = str(uuid.uuid4())

is_mac = sys.platform == 'darwin'

device = 'cuda' if torch.cuda.is_available() else 'cpu'
try:
    import vllm
except ImportError:
    use_vllm = False
else:
    use_vllm = device == 'cuda'


# utilities
def tobool(val: str | None):
    if val is None:
        return False
    val = val.lower().strip()
    if val in ['y', 'yes', 'true', '1']:
        return True
    return False


# general
app_port = int(os.environ.get('SKYNET_PORT', 8000))
listen_ip = os.environ.get('SKYNET_LISTEN_IP', '0.0.0.0')
log_level = os.environ.get('LOG_LEVEL', 'DEBUG').strip().upper()
supported_modules = {'summaries:dispatcher', 'summaries:executor', 'streaming_whisper', 'assistant'}
enabled_modules = set(os.environ.get('ENABLED_MODULES', 'summaries:dispatcher,summaries:executor,assistant').split(','))
modules = supported_modules.intersection(enabled_modules)
file_refresh_interval = int(os.environ.get('FILE_REFRESH_INTERVAL', 30))

# models
llama_path = os.environ.get('LLAMA_PATH', 'llama3.1')
llama_n_ctx = int(os.environ.get('LLAMA_N_CTX', 128000))

embeddings_chunk_size = int(os.environ.get('EMBEDDINGS_CHUNK_SIZE', 5000))
embeddings_model_path = os.environ.get('EMBEDDINGS_MODEL_PATH', 'BAAI/bge-m3')

# azure openai api
# latest ga version https://learn.microsoft.com/en-us/azure/ai-services/openai/api-version-deprecation#latest-ga-api-release
azure_openai_api_version = os.environ.get('AZURE_OPENAI_API_VERSION', '2024-10-21')

# openai api
openai_api_port = 8003
openai_api_base_url = os.environ.get(
    'OPENAI_API_BASE_URL', f'http://localhost:{openai_api_port}' if use_vllm else "http://localhost:11434"
)

# openai
openai_credentials_file = os.environ.get('SKYNET_CREDENTIALS_PATH')

# health checking
disable_llm_health_check = tobool(os.environ.get('DISABLE_LLM_HEALTH_CHECK', 'false'))

# auth
bypass_auth = tobool(os.environ.get('BYPASS_AUTHORIZATION'))
asap_pub_keys_url = os.environ.get('ASAP_PUB_KEYS_REPO_URL')
asap_pub_keys_folder = os.environ.get('ASAP_PUB_KEYS_FOLDER')
asap_pub_keys_fallback_folder = os.environ.get('ASAP_PUB_KEYS_FALLBACK_FOLDER')
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
whisper_beam_size = int(os.environ.get('BEAM_SIZE', 5))
whisper_model_name = os.environ.get('WHISPER_MODEL_NAME')
# https://opennmt.net/CTranslate2/quantization.html
whisper_compute_type = os.environ.get('WHISPER_COMPUTE_TYPE', 'int8')
whisper_gpu_indices = os.environ.get('WHISPER_GPU_INDICES')
whisper_device = os.environ.get('WHISPER_DEVICE', 'auto')
whisper_model_path = os.environ.get('WHISPER_MODEL_PATH', f'{os.getcwd()}/models/streaming_whisper')
whisper_return_transcribed_audio = tobool(os.environ.get('WHISPER_RETURN_TRANSCRIBED_AUDIO'))
whisper_max_connections = int(os.environ.get('WHISPER_MAX_CONNECTIONS', 10))
whisper_min_probability = float(os.environ.get('WHISPER_MIN_PROBABILITY', 0.7))
ws_max_size_bytes = int(os.environ.get('WS_MAX_SIZE_BYTES', 1000000))
ws_max_queue_size = int(os.environ.get('WS_MAX_QUEUE_SIZE', 3000))
ws_max_ping_interval = int(os.environ.get('WS_MAX_PING_INTERVAL', 30))
ws_max_ping_timeout = int(os.environ.get('WS_MAX_PING_TIMEOUT', 30))
# The maximum number of final transcriptions to include in the initial prompt.
# This is used to provide some context to the model
# The larger the initial prompt (max 224 tokens), the slower the inference.
whisper_max_finals_in_initial_prompt = int(os.environ.get('WHISPER_MAX_FINALS_IN_INITIAL_PROMPT', 2))
# The period in milliseconds to flush the buffer after no new spoken audio is detected
whisper_flush_interval = int(os.environ.get('WHISPER_FLUSH_BUFFER_INTERVAL', 2000))

# jobs
job_timeout = int(os.environ.get('JOB_TIMEOUT', 60 * 5))  # 5 minutes default
max_concurrency = int(os.environ.get('MAX_CONCURRENCY', 30))

# summaries
summary_minimum_payload_length = int(os.environ.get('SUMMARY_MINIMUM_PAYLOAD_LENGTH', 100))
enable_batching = tobool(os.environ.get('ENABLE_BATCHING', 'true'))

# monitoring
enable_metrics = tobool(os.environ.get('ENABLE_METRICS', 'true'))

# load balancing
enable_haproxy_agent = tobool(os.environ.get('ENABLE_HAPROXY_AGENT'))

# testing
echo_requests_base_url = os.environ.get('ECHO_REQUESTS_BASE_URL')
echo_requests_percent = int(os.environ.get('ECHO_REQUESTS_PERCENT', 100))
echo_requests_token = os.environ.get('ECHO_REQUESTS_TOKEN')

# oci
oci_max_tokens = int(os.environ.get('OCI_MAX_TOKENS', 4000))
oci_model_id = os.environ.get('OCI_MODEL_ID')
oci_service_endpoint = os.environ.get(
    'OCI_SERVICE_ENDPOINT', 'https://inference.generativeai.eu-frankfurt-1.oci.oraclecloud.com'
)
oci_compartment_id = os.environ.get('OCI_COMPARTMENT_ID')
oci_auth_type = os.environ.get('OCI_AUTH_TYPE', 'API_KEY')
oci_config_profile = os.environ.get('OCI_CONFIG_PROFILE', 'DEFAULT')
oci_available = oci_model_id and oci_service_endpoint and oci_compartment_id and oci_auth_type and oci_config_profile
use_oci = oci_available and llama_path.startswith('oci://')

# rag
vector_store_path = os.environ.get('VECTOR_STORE_PATH', '_vector_store_')
supported_vector_store_types = {'faiss'}
vector_store_type = supported_vector_store_types.intersection({os.environ.get('VECTOR_STORE_TYPE', 'faiss').lower()})
vector_store_type = vector_store_type.pop() if vector_store_type else None

# s3
skynet_s3_access_key = os.environ.get('SKYNET_S3_ACCESS_KEY')
skynet_s3_bucket = os.environ.get('SKYNET_S3_BUCKET')
skynet_s3_endpoint = os.environ.get('SKYNET_S3_ENDPOINT')
skynet_s3_region = os.environ.get('SKYNET_S3_REGION')
skynet_s3_secret_key = os.environ.get('SKYNET_S3_SECRET_KEY')
use_s3 = all([skynet_s3_access_key, skynet_s3_secret_key, skynet_s3_bucket, skynet_s3_endpoint, skynet_s3_region])
