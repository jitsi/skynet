import asyncio

from .common import close_session, modules


async def main():
    success = True

    try:
        if 'assistant' in modules:
            from .assistant import run as assistant_run

            await assistant_run()

        if 'summaries' in modules:
            from .summaries import run as summaries_run

            await summaries_run()
    except Exception as e:
        success = False
    finally:
        await close_session()

    if not success:
        raise Exception('E2E tests failed')


asyncio.run(main())
