from enum import Enum
from typing import Optional

from pydantic import BaseModel

from skynet.modules.ttt.summaries.v1.models import DocumentPayload

default_max_depth = 5


class RagStatus(Enum):
    ERROR = 'error'
    RUNNING = 'running'
    SUCCESS = 'success'


class RagPayload(BaseModel):
    max_depth: Optional[int] = default_max_depth
    urls: list[str]

    model_config = {
        'json_schema_extra': {
            'examples': [{'urls': ['https://jitsi.github.io/handbook'], 'max_depth': default_max_depth}]
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
                    'urls': ['https://jitsi.github.io/handbook'],
                }
            ]
        }
    }


class AssistantDocumentPayload(DocumentPayload):
    model_config = {
        'json_schema_extra': {
            'examples': [
                {
                    'text': 'User provided context here (will be appended to the RAG one)',
                    'prompt': 'User prompt here',
                    'max_completion_tokens': None,
                }
            ]
        }
    }


class AssistantResponse(BaseModel):
    text: str
