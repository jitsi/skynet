from enum import Enum
from typing import Optional

from pydantic import BaseModel

from skynet.modules.ttt.assistant.constants import assistant_default_system_message

from skynet.modules.ttt.summaries.v1.models import DocumentPayload, HintType

default_max_depth = 5


class RagStatus(Enum):
    ERROR = 'error'
    RUNNING = 'running'
    SUCCESS = 'success'


class RagPayload(BaseModel):
    system_message: Optional[str] = None
    max_depth: Optional[int] = default_max_depth
    urls: list[str]

    model_config = {
        'json_schema_extra': {
            'examples': [
                {
                    'urls': ['https://jitsi.github.io/handbook'],
                    'max_depth': default_max_depth,
                    'system_message': assistant_default_system_message,
                }
            ]
        }
    }


class RagConfig(RagPayload):
    error: Optional[str] = None
    status: RagStatus = RagStatus.RUNNING

    model_config = {
        'json_schema_extra': {
            'examples': [
                {
                    'error': None,
                    'max_depth': default_max_depth,
                    'status': 'running',
                    'system_message': assistant_default_system_message,
                    'urls': ['https://jitsi.github.io/handbook'],
                }
            ]
        }
    }


class AssistantDocumentPayload(DocumentPayload):
    use_only_rag_data: bool = False

    model_config = {
        'json_schema_extra': {
            'examples': [
                {
                    'text': 'User provided context here (will be appended to the RAG one)',
                    'prompt': 'User prompt here',
                    'max_completion_tokens': None,
                    'use_only_rag_data': False,  # If True and a vector store is available, only the RAG data will be used for assistance
                }
            ]
        }
    }


class AssistantResponse(BaseModel):
    text: str
