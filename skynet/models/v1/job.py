from enum import Enum
import timeit
from pydantic import BaseModel, Field, computed_field

class JobType(Enum):
    ACTION_ITEMS = 'action_items'
    SUMMARY = 'summary'

class JobStatus(Enum):
    PENDING = 'pending'
    SUCCESS = 'success'
    ERROR = 'error'

class Job(BaseModel):
    end: float = 0
    start: float = 0

    id: str
    result: str | None = None
    status: JobStatus = JobStatus.PENDING
    type: JobType

    @computed_field
    @property
    def duration(self) -> float:
        return round(self.end - self.start, 3)

class JobId(BaseModel):
    id: str
