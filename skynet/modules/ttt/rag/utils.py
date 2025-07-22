import os

import aiofiles

from fastapi import UploadFile

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from skynet.env import embeddings_chunk_size


def split_documents(initial_documents: list[Document]) -> list[Document]:
    """
    Split the documents into smaller chunks.
    """

    # todo: use a better splitter
    splitter = RecursiveCharacterTextSplitter(chunk_size=embeddings_chunk_size, chunk_overlap=100)

    splits = splitter.split_documents(initial_documents)

    return splits


async def save_files(folder: str, files: list[UploadFile]) -> list[str]:
    if not files:
        return []

    file_paths = []
    os.makedirs(folder, exist_ok=True)

    for file in files:
        if not file.filename:
            raise ValueError("File must have a filename")

        # Construct the file path and validate it stays within the intended folder
        file_path = os.path.join(folder, file.filename)
        resolved_path = os.path.abspath(os.path.realpath(file_path))
        resolved_folder = os.path.abspath(os.path.realpath(folder))

        if not resolved_path.startswith(resolved_folder + os.sep):
            raise ValueError(f"Invalid file path: {file.filename}")

        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(await file.read())
        file_paths.append(file_path)

    return file_paths
