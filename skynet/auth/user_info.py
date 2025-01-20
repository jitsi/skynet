from enum import Enum

import aiofiles
import yaml

from skynet.env import openai_credentials_file
from skynet.logs import get_logger
from skynet.modules.file_watcher import FileWatcher

log = get_logger(__name__)

credentials = dict()


class CredentialsType(Enum):
    OPENAI = 'OPENAI'
    AZURE_OPENAI = 'AZURE_OPENAI'


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
    customer_credentials = credentials.get(customer_id, {}) or {}
    multiple_credentials = customer_credentials.get('credentialsMap')

    if multiple_credentials:
        result = [val for val in multiple_credentials.values() if val['enabled']]
        return result[0] if result else {}

    # backwards compatibility
    customer_credentials.setdefault('type', CredentialsType.OPENAI.value)
    return customer_credentials
