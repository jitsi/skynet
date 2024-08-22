from pydantic import BaseModel


class AssistantResponse(BaseModel):
    text: str
    ts: int
