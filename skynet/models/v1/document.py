from pydantic import BaseModel

class DocumentPayload(BaseModel):
    text: str