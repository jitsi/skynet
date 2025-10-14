from enum import Enum

import aiofiles
import yaml

from skynet.env import default_customer_id, openai_credentials_file
from skynet.logs import get_logger
from skynet.modules.file_watcher import FileWatcher

log = get_logger(__name__)

credentials = dict()


class CredentialsType(Enum):
    AZURE_OPENAI = 'AZURE_OPENAI'
    LOCAL = 'LOCAL'
    OCI = 'OCI'
    OPENAI = 'OPENAI'


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
        customer_credentials = result[0] if result else {}

    # If no secret is configured and default_customer_id is set, try to use those credentials
    if not customer_credentials.get('secret') and default_customer_id and customer_id != default_customer_id:
        log.info(
            f'No secret configured for customer {customer_id}, falling back to default customer {default_customer_id}'
        )
        return get_credentials(default_customer_id)

    return customer_credentials
