from langchain_community.chat_models import ChatOCIGenAI
from langchain_core.messages import HumanMessage, SystemMessage

from skynet.env import (
    oci_auth_type,
    oci_available,
    oci_compartment_id,
    oci_config_profile,
    oci_model_id,
    oci_service_endpoint,
)


async def initialize():
    if not oci_available:
        return

    # Prime it so all transformers config is downloaded.
    model_kwargs = {
        "temperature": 0,
        "frequency_penalty": 1,
        "max_tokens": None,
    }

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
