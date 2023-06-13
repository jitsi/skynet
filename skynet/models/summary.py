from pydantic import BaseModel

class SummaryPayload(BaseModel):
    retrieveActionItems: bool = False
    text: str