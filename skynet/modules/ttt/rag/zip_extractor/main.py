import asyncio
from pathlib import Path
from shutil import unpack_archive
from typing import Optional


def _extract_files_sync(
    compressed_files: list[str], destination_folder: str, min_size_kb: Optional[int] = None
) -> list[str]:
    """Synchronous implementation of file extraction"""
    extracted_files = []

    for compressed_file in compressed_files:
        file_name = Path(compressed_file).name
        extracted_folder_name = file_name.replace('.zip', '')
        extracted_folder_path = f'{destination_folder}/archives/{extracted_folder_name}'
        unpack_archive(compressed_file, extracted_folder_path)

        all_entries = [f for f in Path(extracted_folder_path).rglob('*')]
        only_files = [str(f) for f in all_entries if Path(f).is_file()]
        extracted_files.extend(only_files)

    if min_size_kb:
        extracted_files = [f for f in extracted_files if Path(f).stat().st_size >= min_size_kb * 1024]

    return extracted_files


async def extract_files(
    compressed_files: list[str], destination_folder: str, min_size_kb: Optional[int] = None
) -> list[str]:
    """
    Extract all files from the given list of compressed files.
    Runs the entire extraction process in a separate thread.
    """
    return await asyncio.to_thread(_extract_files_sync, compressed_files, destination_folder, min_size_kb)
