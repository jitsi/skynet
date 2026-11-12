from typing import Optional

from langchain_community.chat_models import ChatOCIGenAI
from langchain_core.messages import HumanMessage, SystemMessage
from oci.exceptions import TransientServiceError

from skynet.env import (
    oci_auth_type,
    oci_available,
    oci_compartment_id,
    oci_config_profile,
    oci_model_id,
    oci_service_endpoint,
)
from skynet.logs import get_logger

log = get_logger(__name__)

# Set when the startup warm-up fails with a non-transient error (e.g. a model id
# that does not exist on the configured endpoint). OCI stays off until restart.
_disabled_reason: Optional[str] = None


def is_oci_disabled() -> bool:
    return _disabled_reason is not None


async def initialize():
    global _disabled_reason

    if not oci_available:
        return

    # Prime it so all transformers config is downloaded.
    model_kwargs = {
        "temperature": 0,
        "frequency_penalty": 1,
        "max_tokens": None,
    }

    try:
        llm = ChatOCIGenAI(
            model_id=oci_model_id,
            service_endpoint=oci_service_endpoint,
            compartment_id=oci_compartment_id,
            provider="meta",
            model_kwargs=model_kwargs,
            auth_type=oci_auth_type,
            auth_profile=oci_config_profile,
        )

        messages = [
            SystemMessage(content="Your are an AI assistant."),
            HumanMessage(content="Hello."),
        ]

        await llm.ainvoke(messages)
    except TransientServiceError as e:
        log.warning(f"Warming up OCI hit TransientServiceError: {e}")
    except Exception as e:
        # A broken OCI config must not take the whole service down: customers with
        # their own OpenAI / Azure credentials don't need OCI at all.
        _disabled_reason = str(e)
        log.error(f"Warming up OCI failed, disabling OCI until restart: {e}")
