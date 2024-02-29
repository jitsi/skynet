import yaml

from skynet.env import openai_credentials_file
from skynet.modules.file_watcher import FileWatcher

credentials = dict()


def open_yaml(file_path):
    try:
        with open(file_path, 'r') as stream:
            global credentials
            credentials = yaml.safe_load(stream)['customer_credentials']
    except Exception as e:
        raise RuntimeError(f'Error loading credentials file: {e}')


def setup_credentials():
    if openai_credentials_file:
        open_yaml(openai_credentials_file)
        file_watcher = FileWatcher(openai_credentials_file, lambda: open_yaml(openai_credentials_file))

        file_watcher.start()
    else:
        raise RuntimeError('The OpenAI credentials file must be set')


def get_credentials(customer_id):
    return credentials.get(customer_id)
