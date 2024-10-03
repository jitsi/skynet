import time
from enum import Enum

from pydantic import BaseModel, computed_field, Field


class HintType(Enum):
    CONVERSATION = 'conversation'
    EMAILS = 'emails'
    TEXT = 'text'


class DocumentPayload(BaseModel):
    text: str
    hint: HintType = HintType.TEXT
    prompt: str | None = None

    model_config = {
        'json_schema_extra': {
            'examples': [{'text': 'Your text here', 'hint': 'text', 'prompt': 'Summarize the following text {text}'}]
        }
    }


class DocumentMetadata(BaseModel):
    customer_id: str | None = None


class JobType(Enum):
    ACTION_ITEMS = 'action_items'
    SUMMARY = 'summary'


class Processors(Enum):
    OPENAI = 'OPENAI'
    AZURE = 'AZURE'
    LOCAL = 'LOCAL'


class JobStatus(Enum):
    PENDING = 'pending'
    RUNNING = 'running'
    SUCCESS = 'success'
    ERROR = 'error'


# job model to expose to the API
class BaseJob(BaseModel):
    duration: float = 0.0
    id: str
    processor: Processors = Processors.LOCAL
    result: str | None = None
    status: JobStatus = JobStatus.PENDING
    type: JobType


# since private fields are not serialized, use a different model with required internals
class Job(BaseJob):
    created: float = Field(default_factory=time.time)
    end: float | None = None
    metadata: DocumentMetadata = DocumentMetadata()
    payload: DocumentPayload
    start: float | None = None
    worker_id: int | None = None

    @computed_field
    @property
    def computed_duration(self) -> float:
        if self.start and self.end:
            return round(self.end - self.start, 3)

        return 0.0


class JobId(BaseModel):
    id: str
