from typing import List, Optional

from fastapi import Request
from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel

from skynet.logs import get_logger
from skynet.modules.ttt.processor import process_chat_completion
from skynet.utils import get_customer_id, get_router

router = get_router()
log = get_logger(__name__)


class ChatMessage(BaseModel):
    content: Optional[str] = None


class ChatCompletionResponseChoice(BaseModel):
    message: ChatMessage


class ChatCompletionResponse(BaseModel):
    choices: List[ChatCompletionResponseChoice]


class ChatCompletionRequest(BaseModel):
    max_completion_tokens: Optional[int] = None
    messages: List[ChatCompletionMessageParam]


@router.post('/v1/chat/completions')
async def create_chat_completion(chat_request: ChatCompletionRequest, request: Request):
    response = await process_chat_completion(
        chat_request.messages, get_customer_id(request), max_completion_tokens=chat_request.max_completion_tokens
    )

    return ChatCompletionResponse(choices=[ChatCompletionResponseChoice(message=ChatMessage(content=response))])
