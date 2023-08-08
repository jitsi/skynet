from pydantic import BaseModel

class SummaryResult(BaseModel):
    summary: str
