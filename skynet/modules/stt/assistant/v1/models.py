from pydantic import BaseModel


class TestPayload(BaseModel):
    audio: str
    prompt: str
