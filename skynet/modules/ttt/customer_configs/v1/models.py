from typing import Optional

from pydantic import BaseModel


class CustomerConfigPayload(BaseModel):
    live_summary_prompt: str


class CustomerConfig(BaseModel):
    live_summary_prompt: Optional[str] = None


class CustomerConfigResponse(BaseModel):
    success: bool = True
    message: str = "Customer configuration updated successfully"
