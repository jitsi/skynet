from typing import Optional

from langchain_community.chat_models import ChatOCIGenAI
from langchain_core.language_models.chat_models import BaseChatModel

from langchain_openai import AzureChatOpenAI, ChatOpenAI

from skynet.auth.user_info import CredentialsType, get_credentials
from skynet.env import (
    app_uuid,
    azure_openai_api_version,
    llama_path,
    oci_auth_type,
    oci_available,
    oci_compartment_id,
    oci_config_profile,
    oci_max_tokens,
    oci_model_id,
    oci_service_endpoint,
    openai_api_base_url,
)
from skynet.logs import get_logger
from skynet.modules.ttt.summaries.v1.models import Processors

log = get_logger(__name__)

overriden_processors = {}


class LLMSelector:
    @staticmethod
    def override_job_processor(job_id: str, processor: Processors) -> None:
        overriden_processors[job_id] = processor

    @staticmethod
    def get_job_processor(customer_id: str, job_id: Optional[str] = None, oci_blackout: bool = False) -> Processors:
        if job_id and job_id in overriden_processors:
            return overriden_processors[job_id]

        options = get_credentials(customer_id)
        secret = options.get('secret')
        api_type = options.get('type')

        if secret:
            if api_type == CredentialsType.OPENAI.value:
                return Processors.OPENAI
            elif api_type == CredentialsType.AZURE_OPENAI.value:
                return Processors.AZURE

        if api_type == CredentialsType.LOCAL.value:
            return Processors.LOCAL

        if oci_available and not oci_blackout:
            return Processors.OCI

        return Processors.LOCAL

    @staticmethod
    def select(
        customer_id: str,
        job_id: Optional[str] = None,
        max_completion_tokens: Optional[int] = None,
        temperature: Optional[float] = 0,
        stream: Optional[bool] = False,
        oci_blackout: bool = False,
    ) -> BaseChatModel:
        processor = LLMSelector.get_job_processor(customer_id, job_id, oci_blackout)
        options = get_credentials(customer_id)

        if processor == Processors.OPENAI:
            log.info(f'Forwarding inference to OpenAI for customer {customer_id}')

            model_name = options.get('metadata').get('model')

            # gpt-5 family does not support temperature other than 1 anymore
            model_temp = 1 if model_name.startswith('gpt-5') else temperature

            return ChatOpenAI(
                api_key=options.get('secret'),
                max_completion_tokens=max_completion_tokens,
                model_name=model_name,
                streaming=stream,
                temperature=model_temp,
            )
        elif processor == Processors.AZURE:
            log.info(f'Forwarding inference to Azure-OpenAI for customer {customer_id}')

            metadata = options.get('metadata')

            return AzureChatOpenAI(
                api_key=options.get('secret'),
                api_version=azure_openai_api_version,
                azure_deployment=metadata.get('deploymentName'),
                azure_endpoint=metadata.get('endpoint'),
                max_completion_tokens=max_completion_tokens,
                streaming=stream,
                temperature=temperature,
            )
        elif processor == Processors.OCI:
            log.info(f'Forwarding inference to OCI for customer {customer_id}')

            model_kwargs = {
                'temperature': temperature,
                'frequency_penalty': 1,
                'max_tokens': max(max_completion_tokens or 0, oci_max_tokens),
            }

            return ChatOCIGenAI(
                auth_profile=oci_config_profile,
                auth_type=oci_auth_type,
                compartment_id=oci_compartment_id,
                is_stream=stream,
                model_id=oci_model_id,
                model_kwargs=model_kwargs,
                provider='meta',
                service_endpoint=oci_service_endpoint,
            )
        else:
            log.info(f'Forwarding inference to local LLM for customer {customer_id}')

            return ChatOpenAI(
                api_key='placeholder',  # use a placeholder value to bypass validation
                base_url=f'{openai_api_base_url}/v1',
                default_headers={'X-Skynet-UUID': app_uuid},
                frequency_penalty=1,
                max_completion_tokens=max_completion_tokens,
                max_retries=0,
                model=llama_path,
                streaming=stream,
                temperature=temperature,
            )


llm_selector = LLMSelector()
