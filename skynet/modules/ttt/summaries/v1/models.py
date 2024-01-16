import time

from enum import Enum

from pydantic import BaseModel, computed_field, Field


class DocumentPayload(BaseModel):
    text: str


class JobType(Enum):
    ACTION_ITEMS = 'action_items'
    SUMMARY = 'summary'


class JobStatus(Enum):
    PENDING = 'pending'
    RUNNING = 'running'
    SUCCESS = 'success'
    ERROR = 'error'


# job model to expose to the API
class BaseJob(BaseModel):
    id: str
    result: str | None = None
    status: JobStatus = JobStatus.PENDING
    type: JobType
    duration: float = 0.0


# since private fields are not serialized, use a different model with required internals
class Job(BaseJob):
    end: float | None = None
    created: float = Field(default_factory=time.time)
    start: float | None = None
    payload: DocumentPayload
    worker_id: int | None = None

    @computed_field
    @property
    def computed_duration(self) -> float:
        if self.start and self.end:
            return round(self.end - self.start, 3)

        return 0.0


class JobId(BaseModel):
    id: str
