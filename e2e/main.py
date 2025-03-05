import asyncio

from .common import close_session, modules


async def main():
    success = True
    tasks = []

    if 'assistant' in modules:
        from .assistant import run as assistant_run

        tasks.append(assistant_run())

    try:
        all(await asyncio.gather(*tasks))
    except Exception as e:
        success = False
    finally:
        await close_session()

    if not success:
        raise Exception('E2E tests failed')


asyncio.run(main())
