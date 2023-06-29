from pydantic import BaseModel

class SummaryPayload(BaseModel):
    text: str