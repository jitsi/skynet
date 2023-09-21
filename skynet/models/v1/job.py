from enum import Enum
import timeit
from pydantic import BaseModel, PrivateAttr, computed_field

class JobType(Enum):
    ACTION_ITEMS = 'action_items'
    SUMMARY = 'summary'

class JobStatus(Enum):
    PENDING = 'pending'
    SUCCESS = 'success'
    ERROR = 'error'

class Job(BaseModel):
    _end: float = PrivateAttr(default_factory=timeit.default_timer)
    _start: float = PrivateAttr(default_factory=timeit.default_timer)

    id: str
    result: str | None = None
    status: JobStatus = JobStatus.PENDING
    type: JobType

    @computed_field
    @property
    def duration(self) -> float:
        return round(self._end - self._start, 3)

class JobId(BaseModel):
    id: str
