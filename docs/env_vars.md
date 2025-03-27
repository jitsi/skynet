# Skynet Environment Variables

Skynet is configurable via environment variables. Some are shared by all modules, while others are specific to each one of them. You can skip setting the env variables for the disabled modules.

## Shared Environment Variables

| **Name**                       | **Description**                                             | **Default**                               | **Available values**                                                            |
|--------------------------------|-------------------------------------------------------------|-------------------------------------------|---------------------------------------------------------------------------------|
| `ENABLE_METRICS`               | If the Prometheus metrics endpoint should be enabled or not | `true`                                    | `true`, `false`                                                                 |
| `ENABLED_MODULES`              | Which modules should be enabled, separated by commas        | `summaries:dispatcher,summaries:executor,assistant` | `summaries:dispatcher`, `summaries:executor`, `assistant`, `streaming_whisper` |
| `BYPASS_AUTHORIZATION`         | If signed JWT authorization should be enabled               | `false`                                   | `true`, `false`                                                                 |
| `ASAP_PUB_KEYS_REPO_URL`       | Public key repository URL                                   | `NULL`                                    | N/A                                                                             |
| `ASAP_PUB_KEYS_FOLDER`         | Public key repository root path                             | `NULL`                                    | N/A                                                                             |
| `ASAP_PUB_KEYS_AUDS`           | Allowed JWT audiences, separated by commas                  | `NULL`                                    | N/A                                                                             |
| `ASAP_PUB_KEYS_MAX_CACHE_SIZE` | Public key maximum cache size in bytes                      | `512`                                     | N/A                                                                             |
| `LOG_LEVEL`                    | Log level                                                   | `DEBUG`                                   | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`                                 |


## Assistant Module Environment Variables

| Name                             | **Description**                                                                                                                                    | **Default**                         | **Available values** |
|----------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------|----------------------|   
| `EMBEDDINGS_CHUNK_SIZE`          | Max size (in characters) of documents for which embeddings will be computed. Should be less than the max tokens of the embedding model             | 5000                                | N/A                  |
| `EMBEDDINGS_MODEL_PATH`          | The path where the embeddings model is located.                                                                                                    | `BAAI/bge-m3`    | N/A                  |
| `VECTOR_STORE_PATH`              | The default path where the vector store is saved locally                                                                                           | `_vector_store_`                    | N/A                  |


## Summaries Module Environment Variables

| Name                             | **Description**                                                                                                                                    | **Default**                         | **Available values** |
|----------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------|----------------------|
| `ENABLE_BATCHING`                | Enable submitting jobs for inference while others are running. The actual batching needs to be supported by the underlying inference processor     | `true`                              | `true`,`false`       |
| `LLAMA_PATH`                     | The path where the llama model is located.                                                                                                         | `llama3.1`                          | N/A                  |
| `LLAMA_N_CTX`                    | The context size of the llama model                                                                                                                | `128000`                            | N/A                  |
| `JOB_TIMEOUT`                    | Timeout in seconds after which an inference job will be considered stuck and the app killed.                                                       | `300`                               | N/A                  |
| `SUMMARY_MINIMUM_PAYLOAD_LENGTH` | The minimum payload length allowed for summarization.                                                                                              | `100`                               | N/A                  |
| `SKYNET_LISTEN_IP`               | Default ip address on which the webserver is started.                                                                                              | `0.0.0.0`                           | N/A                  |
| `SKYNET_PORT`                    | Default port on which the webserver is started.                                                                                                    | `8000`                              | N/A                  |

## Redis vars

| Name                             | **Description**                                                                                                                                    | **Default**                         | **Available values** |
|----------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------|----------------------|
| `REDIS_EXP_SECONDS`              | After how many seconds will a completed job expire/be deleted from Redis                                                                           | `1800`                              | N/A                  |
| `REDIS_HOST`                     | Redis host                                                                                                                                         | `localhost`                         | N/A                  |
| `REDIS_PORT`                     | Redis port                                                                                                                                         | `6379`                              | N/A                  |
| `REDIS_USE_TLS`                  | Use TLS when connecting to Redis                                                                                                                   | `false`                             | N/A                  |
| `REDIS_DB_NO`                    | Redis database number                                                                                                                              | `0`                                 | N/A                  |
| `REDIS_USR`                      | Redis user if using user/pass auth                                                                                                                 | `NULL`                              | N/A                  |
| `REDIS_PWD`                      | Redis pass if using user/pass auth                                                                                                                 | `NULL`                              | N/A                  |
| `REDIS_AWS_SECRET_ID`            | The ID of the secret to retrieve from AWS Secrets Manager                                                                                          | `NULL`                              | N/A                  |
| `REDIS_USE_SECRETS_MANAGER`      | Use AWS Secrets Manager to retrieve credentials                                                                                                    | `false`                             | N/A                  |
| `REDIS_NAMESPACE`                | Prefix for each Redis key                                                                                                                          | `skynet`                            | N/A                  |
| `REDIS_AWS_REGION`               | The AWS region. Needed when using AWS Secrets Manager to retrieve credentials.                                                                     | `us-west-2`                         | N/A                  |

## OCI vars
| Name                             | **Description**                                                                                                                                    | **Default**                         | **Available values** |
|----------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------|----------------------|
| `OCI_MAX_TOKENS`                 | OCI Maximum output tokens (check https://docs.oracle.com/en-us/iaas/Content/generative-ai/pretrained-models.htm)                                   | 4000                                | N/A                  |
| `OCI_MODEL_ID`                   | OCI Model id                                                                                                                                       | NULL                                | N/A                  |
| `OCI_SERVICE_ENDPOINT`           | OCI Service endpoint                                                                                                                               | `https://inference.generativeai.us-chicago-1.oci.oraclecloud.com`                                | N/A                  |
| `OCI_COMPARTMENT_ID`             | OCI Compartment ID                                                                                                                                 | NULL                                | N/A                  |
| `OCI_AUTH_TYPE`                  | OCI Authorization type                                                                                                                             | `API KEY`                           | N/A                  |
| `OCI_CONFIG_PROFILE`             | OCI Config profile                                                                                                                                 | `DEFAULT`                           | N/A                  |

## S3 vars (used for RAG vector store replication)
| Name                             | **Description**                                                                                                                                    | **Default**                         | **Available values** |
|----------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------|----------------------|
| `SKYNET_S3_ACCESS_KEY`           | S3 access key                                                                                                                                      | NULL                                | N/A                  |
| `SKYNET_S3_BUCKET`               | S3 bucket                                                                                                                                          | NULL                                | N/A                  |
| `SKYNET_S3_ENDPOINT`             | S3 endpoint                                                                                                                                        | NULL                                | N/A                  |
| `SKYNET_S3_REGION`               | S3 region                                                                                                                                          | NULL                                | N/A                  |
| `SKYNET_S3_SECRET_KEY`           | S3 secret key                                                                                                                                      | NULL                                | N/A                  |

## Streaming Whisper Module Environment Variables

| Name                               | **Description**                                                                                                                                              | **Default**                                 | **Available values**                                                                                                                                                           |
|------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `BEAM_SIZE`                        | Whisper beam size                                                                                                                                            | `1`                                         | N/A                                                                                                                                                                            |
| `WHISPER_MODEL_NAME`               | The Faster Whisper model name to use if you want to download it automatically at start-up. **Don't define it if you intend to mount the model as a volume.** | `NULL`                                      | `tiny`, `tiny.en`, `small`, `small.en`, `base`, `base.en`, `medium`, `medium.en`, `large-v2`, `large-v1`.<br>**NOTE**: check https://huggingface.co/SYSTRAN for model updates. |
| `WHISPER_COMPUTE_TYPE`             | Quantization https://opennmt.net/CTranslate2/quantization.html                                                                                               | `int8`                                      | `int8`, `int8_float32`, `int8_float16`, `int8_bfloat16`, `int16`, `float16`, `bfloat16`, `float32`                                                                             |
| `WHISPER_GPU_INDICES`              | Use multiple GPUs if available by specifying their indices separated by commas, e.g. `0,1` for two GPUs                                                      | `0`                                         | N/A                                                                                                                                                                            |
| `WHISPER_DEVICE`                   | Which device to use for inference. The default `auto` will automatically detect if a GPU is present and fall back to `cpu` if not.                           | `auto`                                      | `auto`, `cpu`, `gpu`                                                                                                                                                           |  
| `WHISPER_MODEL_PATH`               | The path to the model folder                                                                                                                                 | `f'{os.getcwd()}/models/streaming_whisper'` | N/A                                                                                                                                                                            |
| `WHISPER_RETURN_TRANSCRIBED_AUDIO` | If the transcribed audio should be returned in the response as a base64 string for each segment. Useful for debugging.                                       | `false`                                     | `true`, `false`                                                                                                                                                                |
