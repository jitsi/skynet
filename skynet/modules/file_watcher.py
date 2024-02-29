import asyncio
import os

from skynet.env import file_refresh_interval

from skynet.logs import get_logger

log = get_logger(__name__)


class FileWatcher:
    def __init__(self, file_path, callback=None, refresh_delay_secs=file_refresh_interval):
        self.background_task = None
        self.file_path = file_path
        self.callback = callback
        self.refresh_delay_secs = refresh_delay_secs
        self._previous_modified_time = os.stat(file_path).st_mtime

    def watch(self):
        modified_time = os.stat(self.file_path).st_mtime

        if modified_time != self._previous_modified_time:
            self._previous_modified_time = modified_time

            log.info(f'File {self.file_path} has changed')

            if self.callback:
                self.callback()

    async def poll_for_changes(self):
        while True:
            try:
                await asyncio.sleep(self.refresh_delay_secs)
                self.watch()
            except Exception as e:
                log.error(f'Error while polling for file changes: {e}')
                break

    def start(self):
        self.background_task = asyncio.create_task(self.poll_for_changes())
