import aiofiles
import yaml

from skynet.env import openai_credentials_file
from skynet.logs import get_logger
from skynet.modules.file_watcher import FileWatcher

log = get_logger(__name__)

credentials = dict()


async def open_yaml(file_path):
    try:
        async with aiofiles.open(file_path, mode='r') as file:
            global credentials

            contents = await file.read()
            credentials = yaml.safe_load(contents)['customer_credentials'] or {}
    except Exception as e:
        raise RuntimeError(f'Error loading credentials file: {e}')


async def open_credentials_yaml():
    await open_yaml(openai_credentials_file)


async def setup_credentials():
    if not openai_credentials_file:
        return

    log.info('Setting up credentials.')

    await open_credentials_yaml()
    file_watcher = FileWatcher(openai_credentials_file, open_credentials_yaml)

    file_watcher.start()

    log.info('Credentials set. Watching for changes...')


def get_credentials(customer_id):
    return credentials.get(customer_id, {}) or {}
