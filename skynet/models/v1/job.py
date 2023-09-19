from enum import Enum
from pydantic import BaseModel

class JobType(Enum):
    ACTION_ITEMS = 'action_items'
    SUMMARY = 'summary'

class JobStatus(Enum):
    PENDING = 'pending'
    SUCCESS = 'success'
    ERROR = 'error'

class Job(BaseModel):
    id: str
    result: str | None
    status: JobStatus
    type: JobType
    duration: float

class JobId(BaseModel):
    id: str
