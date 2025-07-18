import os
import tempfile
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import UploadFile

from skynet.modules.ttt.rag.utils import save_files


class TestSaveFiles:
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def mock_upload_file(self):
        """Create a mock UploadFile"""
        file = MagicMock(spec=UploadFile)
        file.filename = "test.txt"
        file.read = AsyncMock(return_value=b"test content")
        return file

    @pytest.mark.asyncio
    async def test_save_files_empty_list(self, temp_dir):
        """Test saving empty file list"""
        result = await save_files(temp_dir, [])
        assert result == []

    @pytest.mark.asyncio
    async def test_save_files_valid_file(self, temp_dir, mock_upload_file):
        """Test saving a valid file"""
        result = await save_files(temp_dir, [mock_upload_file])

        assert len(result) == 1
        assert result[0] == os.path.join(temp_dir, "test.txt")
        assert os.path.exists(result[0])

        with open(result[0], 'rb') as f:
            assert f.read() == b"test content"

    @pytest.mark.asyncio
    async def test_save_files_path_traversal_attack(self, temp_dir):
        """Test prevention of path traversal attacks"""
        malicious_file = MagicMock(spec=UploadFile)
        malicious_file.filename = "../../../etc/passwd"
        malicious_file.read = AsyncMock(return_value=b"malicious content")

        # Path traversal should be rejected
        with pytest.raises(ValueError, match="Invalid file path"):
            await save_files(temp_dir, [malicious_file])

    @pytest.mark.asyncio
    async def test_save_files_no_filename(self, temp_dir):
        """Test handling of file without filename"""
        file_without_name = MagicMock(spec=UploadFile)
        file_without_name.filename = None
        file_without_name.read = AsyncMock(return_value=b"content")

        with pytest.raises(ValueError, match="File must have a filename"):
            await save_files(temp_dir, [file_without_name])

    @pytest.mark.asyncio
    async def test_save_files_multiple_files(self, temp_dir):
        """Test saving multiple files"""
        files = []
        for i in range(3):
            file = MagicMock(spec=UploadFile)
            file.filename = f"file_{i}.txt"
            file.read = AsyncMock(return_value=f"content {i}".encode())
            files.append(file)

        result = await save_files(temp_dir, files)

        assert len(result) == 3
        for i, file_path in enumerate(result):
            assert file_path == os.path.join(temp_dir, f"file_{i}.txt")
            assert os.path.exists(file_path)

            with open(file_path, 'rb') as f:
                assert f.read() == f"content {i}".encode()

    @pytest.mark.asyncio
    async def test_save_files_creates_directory(self):
        """Test that save_files creates the directory if it doesn't exist"""
        with tempfile.TemporaryDirectory() as temp_dir:
            new_dir = os.path.join(temp_dir, "new_folder")
            assert not os.path.exists(new_dir)

            mock_file = MagicMock(spec=UploadFile)
            mock_file.filename = "test.txt"
            mock_file.read = AsyncMock(return_value=b"test content")

            result = await save_files(new_dir, [mock_file])

            assert os.path.exists(new_dir)
            assert len(result) == 1
            assert os.path.exists(result[0])
