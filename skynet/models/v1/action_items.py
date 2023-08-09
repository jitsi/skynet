from pydantic import BaseModel

class ActionItemsResult(BaseModel):
    action_items: str
