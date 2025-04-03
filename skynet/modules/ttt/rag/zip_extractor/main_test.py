import os
import shutil
from pathlib import Path

import pytest

from skynet.modules.ttt.rag.zip_extractor.main import extract_files


class TestExtractFiles:
    @pytest.mark.asyncio
    async def test_extract_files(self):
        """
        Test extract_files function retrieves all files in all folders.
        """

        # create two folders, each containing 2 subfolders with 2 files each
        folders = [Path('temp/folder_1'), Path('temp/folder_2')]

        for folder in folders:
            os.makedirs(folder, exist_ok=True)

        for folder in folders:
            for i in range(2):
                subfolder = f'{folder}/subfolder_{i}'
                os.makedirs(subfolder, exist_ok=True)

                for j in range(2):
                    file = f'{subfolder}/file_{j}.txt'
                    with open(file, 'w') as f:
                        f.write(f'Hello, world! {i} {j}')

        # create two zip files, each containing the two folders
        zip_files = ['temp/test1', 'temp/test2']

        for folder, zip_file in zip(folders, zip_files):
            shutil.make_archive(zip_file, 'zip', folder)

        extracted_files = await extract_files([f'{file}.zip' for file in zip_files], 'temp')
        expected_files = [
            'temp/archives/test1/subfolder_0/file_0.txt',
            'temp/archives/test1/subfolder_0/file_1.txt',
            'temp/archives/test1/subfolder_1/file_0.txt',
            'temp/archives/test1/subfolder_1/file_1.txt',
            'temp/archives/test2/subfolder_0/file_0.txt',
            'temp/archives/test2/subfolder_0/file_1.txt',
            'temp/archives/test2/subfolder_1/file_0.txt',
            'temp/archives/test2/subfolder_1/file_1.txt',
        ]

        try:
            assert set(extracted_files) == set(expected_files)
        finally:
            # remove extracted files
            shutil.rmtree('temp')
