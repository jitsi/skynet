# Skynet Environment Variables

Skynet is configurable via environment variables. Some are shared by all modules, while others are specific to each one of them. You can skip setting the env variables for the disabled modules.

## Shared Environment Variables

| **Name**               | **Description**                                             | **Default**                               | **Available values**                                                            |
|------------------------|-------------------------------------------------------------|-------------------------------------------|---------------------------------------------------------------------------------|
| `ENABLED_MODULES`      | Which modules should be enabled, separated by commas        | `summaries:dispatcher,summaries:executor` | `summaries:dispatcher`, `summaries:executor`, `openai-api`, `streaming_whisper` |
| `BYPASS_AUTHORIZATION` | If signed JWT authorization should be enabled               | `false`                                   | `true`, `false`                                                                 |
| `ENABLE_MONITORING`      | If the Prometheus metrics endpoint should be enabled or not | `true`                                    | `true`, `false`                                                                 |
| `ASAP_PUB_KEYS_REPO_URL` | Public key repository URL | `NULL` | N/A |
| `ASAP_PUB_KEYS_FOLDER` | Public key repository root path | `NULL` | N/A |
| `ASAP_PUB_KEYS_AUDS`   | Allowed JWT audiences, separated by commas | `NULL` | N/A |
| `ASAP_PUB_KEYS_MAX_CACHE_SIZE` | Public key maximum cache size in bytes | `512` | N/A |


## Summaries Module Environment Variables

| Name                 | **Description**                                                                                                                                        | **Default**                             | **Available values** |
|----------------------|----------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------|------------------|
| `LLAMA_CPP_LIB` | The path where libllama resides | `NULL` | Use `$(pwd)/libllama-bin/libllama-m1.so` to enable GPU acceleration on an M1 Mac
| `LLAMA_PATH`         | The path where the llama GGUF model is located.                                                                                                    | `NULL`                              | N/A              |
| `LLAMA_N_GPU_LAYERS` | The number of layers to offload to the GPU. Depends on the hardware. The more layers are offloaded to the GPU, the faster it churns out responses. | `1` if running on Mac, `40` if not. | N/A              |
| `LLAMA_N_BATCH`      | The batch size used when parsing long texts.                                                                                                       | `512`                               | N/A              |
| `JOB_TIMEOUT` | Timeout in seconds after which an inference job will be considered stuck and the app killed. | `600` | N/A |
| `REDIS_EXP_SECONDS` | After how many seconds will a completed job expire/be deleted from Redis | `1800` | N/A |
| `REDIS_HOST` | Redis host | `localhost` | N/A |
| `REDIS_PORT` | Redis port | `6379` | N/A |
| `REDIS_USE_TLS` | Use TLS when connecting to Redis | `false` | N/A |
| `REDIS_DB_NO` | Redis database number | `0` | N/A |
| `REDIS_USR` | Redis user if using user/pass auth | `NULL` | N/A |
| `REDIS_PWD` | Redis pass if using user/pass auth | `NULL` | N/A |
| `REDIS_AWS_SECRET_ID` | The ID of the secret to retrieve from AWS Secrets Manager | `NULL` | N/A |
| `REDIS_USE_SECRETS_MANAGER` | Use AWS Secrets Manager to retrieve credentials | `false` | N/A |
| `REDIS_NAMESPACE` | Prefix for each Redis key | `skynet` | N/A |
| `REDIS_AWS_REGION` | The AWS region. Needed when using AWS Secrets Manager to retrieve credentials. | `us-west-2` | N/A |

## Streaming Whisper Module Environment Variables

| Name                 | **Description**                                                                                                                                        | **Default**                             | **Available values** |
|----------------------|----------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------|------------------|
| `BEAM_SIZE` | Whisper beam size  | `5` | N/A |
| `WHISPER_COMPUTE_TYPE` | Quantization https://opennmt.net/CTranslate2/quantization.html | `int8` | `int8`, `int8_float32`, `int8_float16`, `int8_bfloat16`, `int16`, `float16`, `bfloat16`, `float32` |
| `WHISPER_GPU_INDICES` | Use multiple GPUs if available by specifying the indices separated by commas, e.g. `0,1` for two GPUs | `0` | N/A |
| `WHISPER_DEVICE`| Which device to use for inference. The default `auto` will automatically detect if a GPU is present and fall back to `cpu` if not. | `auto` | `auto`, `cpu`, `gpu` |  
| `WHISPER_MODEL_PATH` | The path to the model folder | `f'{os.getcwd()}/models/streaming_whisper'` | N/A |
