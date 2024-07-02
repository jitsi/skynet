from fastapi_versionizer.versionizer import api_version

from skynet.modules.stt.assistant.fixie import test

from skynet.modules.stt.assistant.v1.models import TestPayload
from skynet.utils import get_router

router = get_router()


@api_version(1)
@router.post("/test")
async def test_stuff(payload: TestPayload) -> None:
    """
    Test
    """

    return await test(payload)
