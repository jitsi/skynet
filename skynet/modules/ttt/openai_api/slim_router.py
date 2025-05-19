from typing import List, Optional

from fastapi import Request
from fastapi.responses import JSONResponse, StreamingResponse
from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel

from skynet.logs import get_logger
from skynet.modules.ttt.processor import process_chat_completion, process_chat_completion_stream
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
    temperature: Optional[float] = None
    stream: Optional[bool] = False


@router.post('/v1/chat/completions')
async def create_chat_completion(chat_request: ChatCompletionRequest, request: Request):
    messages = chat_request.messages
    rest = {k: v for k, v in chat_request.model_dump().items() if k != 'messages' and v is not None}

    if chat_request.stream:
        return StreamingResponse(
            content=process_chat_completion_stream(messages, get_customer_id(request), **rest),
        )

    try:
        response = await process_chat_completion(messages, get_customer_id(request), **rest)
        return ChatCompletionResponse(choices=[ChatCompletionResponseChoice(message=ChatMessage(content=response))])
    except Exception as e:
        return JSONResponse(
            status_code=e.status_code if hasattr(e, 'status_code') else 500,
            content=e.body if hasattr(e, 'body') else {'error': str(e)},
        )
