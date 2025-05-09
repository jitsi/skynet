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
    def get_job_processor(customer_id: str, job_id: Optional[str] = None) -> Processors:
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

        if oci_available:
            return Processors.OCI

        log.warning(f'OCI is not available, falling back to local processing for customer {customer_id}')

        return Processors.LOCAL

    @staticmethod
    def select(
        customer_id: str,
        job_id: Optional[str] = None,
        max_completion_tokens: Optional[int] = None,
        temperature: Optional[float] = 0,
    ) -> BaseChatModel:
        processor = LLMSelector.get_job_processor(customer_id, job_id)
        options = get_credentials(customer_id)

        if processor == Processors.OPENAI:
            log.info(f'Forwarding inference to OpenAI for customer {customer_id}')

            return ChatOpenAI(
                api_key=options.get('secret'),
                max_completion_tokens=max_completion_tokens,
                model_name=options.get('metadata').get('model'),
                temperature=temperature,
            )
        elif processor == Processors.AZURE:
            log.info(f'Forwarding inference to Azure-OpenAI for customer {customer_id}')

            metadata = options.get('metadata')

            return AzureChatOpenAI(
                api_key=options.get('secret'),
                api_version=azure_openai_api_version,
                azure_endpoint=metadata.get('endpoint'),
                azure_deployment=metadata.get('deploymentName'),
                max_completion_tokens=max_completion_tokens,
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
                model_id=oci_model_id,
                service_endpoint=oci_service_endpoint,
                compartment_id=oci_compartment_id,
                provider='meta',
                model_kwargs=model_kwargs,
                auth_type=oci_auth_type,
                auth_profile=oci_config_profile,
            )
        else:
            if customer_id:
                log.info(f'Customer {customer_id} has no API key configured, falling back to local processing')

            return ChatOpenAI(
                model=llama_path,
                api_key='placeholder',  # use a placeholder value to bypass validation
                base_url=f'{openai_api_base_url}/v1',
                default_headers={'X-Skynet-UUID': app_uuid},
                frequency_penalty=1,
                max_retries=0,
                temperature=temperature,
                max_completion_tokens=max_completion_tokens,
            )


llm_selector = LLMSelector()
