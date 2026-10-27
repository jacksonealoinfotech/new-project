"""File upload and object storage abstraction."""

import os
import uuid
from pathlib import Path
from typing import Protocol

from app.core.exceptions import BadRequestError
from app.core.logging import get_logger

logger = get_logger("storage_adapter")


class StorageAdapter(Protocol):
    """Protocol for secure object storage providers."""

    async def save_file(self, filename: str, content: bytes, content_type: str) -> str: ...

    async def get_file(self, file_key: str) -> bytes | None: ...

    async def delete_file(self, file_key: str) -> bool: ...


class LocalStorageAdapter:
    """Local filesystem storage adapter enforcing path-traversal safeguards and randomized naming."""

    def __init__(self, base_directory: str = "uploads") -> None:
        self.base_dir = Path(base_directory).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_safe_path(self, file_key: str) -> Path:
        target = (self.base_dir / file_key).resolve()
        if not str(target).startswith(str(self.base_dir)):
            raise BadRequestError("Invalid file path: path traversal detected.")
        return target

    async def save_file(self, filename: str, content: bytes, content_type: str) -> str:
        # Sanitize extension and generate randomized unique identifier
        ext = os.path.splitext(filename)[1].lower()
        if len(ext) > 10 or "/" in ext or "\\" in ext:
            ext = ""
        secure_key = f"{uuid.uuid4().hex}{ext}"
        target_path = self._resolve_safe_path(secure_key)

        target_path.write_bytes(content)
        logger.info(
            "file_stored_successfully",
            file_key=secure_key,
            size_bytes=len(content),
            content_type=content_type,
        )
        return secure_key

    async def get_file(self, file_key: str) -> bytes | None:
        target_path = self._resolve_safe_path(file_key)
        if not target_path.exists() or not target_path.is_file():
            return None
        return target_path.read_bytes()

    async def delete_file(self, file_key: str) -> bool:
        target_path = self._resolve_safe_path(file_key)
        if target_path.exists() and target_path.is_file():
            target_path.unlink()
            return True
        return False


def get_storage_adapter() -> StorageAdapter:
    """Provide configured storage adapter instance."""
    return LocalStorageAdapter()
