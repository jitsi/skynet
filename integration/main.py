import asyncio

from .s3 import run as s3_run

async def main():
    success = True

    try:
        # this will test integration with aioboto3
        await s3_run()
    except Exception as e:
        print(f'Error: {e}')
        success = False

    if not success:
        raise Exception('Integration tests failed')


asyncio.run(main())
