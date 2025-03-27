from enum import Enum
from typing import Optional

from fastapi import UploadFile
from pydantic import BaseModel, computed_field, field_validator

from skynet.modules.ttt.assistant.constants import assistant_default_system_message

from skynet.modules.ttt.summaries.v1.models import DocumentPayload

default_max_depth = 5


class RagStatus(Enum):
    ERROR = 'error'
    RUNNING = 'running'
    SUCCESS = 'success'


class AssistantType(Enum):
    SEARCH = 'search'
    STATISTICS = 'statistics'


class RagPayload(BaseModel):
    files: Optional[list[UploadFile]] = []
    max_depth: Optional[int] = default_max_depth
    system_message: Optional[str] = None
    urls: Optional[list[str]] = []

    @field_validator('files', mode='before')
    def validate_files(value):
        return [f for f in value if f.filename]

    model_config = {
        'json_schema_extra': {
            'examples': [
                {
                    'files': [],
                    'urls': ['https://jitsi.github.io/handbook'],
                    'max_depth': default_max_depth,
                    'system_message': assistant_default_system_message,
                }
            ]
        }
    }


class RagConfig(RagPayload):
    error: Optional[str] = None
    files: Optional[list[str]] = []
    refresh_interval: int = 30
    status: RagStatus = RagStatus.RUNNING

    @field_validator('files', mode='before')
    def validate_files(value):
        return [f if isinstance(f, str) else f.filename for f in value]

    model_config = {
        'json_schema_extra': {
            'examples': [
                {
                    'error': None,
                    'files': [],
                    'max_depth': default_max_depth,
                    'status': 'running',
                    'system_message': assistant_default_system_message,
                    'urls': ['https://jitsi.github.io/handbook'],
                }
            ]
        }
    }


class AssistantDocumentPayload(DocumentPayload):
    assistant_search_top_k: int = 3
    assistant_stats_top_k: int = 90
    assistant_type: AssistantType = AssistantType.SEARCH
    use_only_rag_data: bool = False

    @computed_field
    @property
    def top_k(self) -> int:
        if self.assistant_type == AssistantType.SEARCH:
            return self.assistant_search_top_k

        return self.assistant_stats_top_k

    model_config = {
        'json_schema_extra': {
            'examples': [
                {
                    'assistant_search_top_k': 3,
                    'assistant_stats_top_k': 90,
                    'assistant_type': 'search',
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
