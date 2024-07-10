from collections.abc import Iterator

from starlette.websockets import WebSocket

from skynet.logs import get_logger
from skynet.modules.stt.assistant.chunk import Chunk
from skynet.modules.stt.assistant.models import AssistantResponse
from skynet.modules.stt.assistant.state import State

log = get_logger(__name__)


class SessionConnection:
    def __init__(self, ws: WebSocket):
        self.ws = ws
        self.state = None

    def process(self, chunk: bytes) -> Iterator[AssistantResponse] | None:
        a_chunk = Chunk(chunk)

        if self.state is None:
            self.state = State()

        return self.state.process(a_chunk)
