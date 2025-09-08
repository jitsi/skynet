from typing import Optional
from pydantic import BaseModel


class CustomerConfigPayload(BaseModel):
    summary_prompt: str


class CustomerConfig(BaseModel):
    summary_prompt: Optional[str] = None


class CustomerConfigResponse(BaseModel):
    success: bool = True
    message: str = "Customer configuration updated successfully"