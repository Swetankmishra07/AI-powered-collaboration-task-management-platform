import os
from io import BytesIO
from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO
from uuid import uuid4

from app.core.config import settings


class StorageError(RuntimeError):
    """Raised when storage cannot read or write an object."""


class StorageProvider(ABC):
    name = "unknown"

    @abstractmethod
    def store(self, stream: BinaryIO, key: str) -> int:
        raise NotImplementedError

    @abstractmethod
    def open(self, key: str) -> BinaryIO:
        raise NotImplementedError

    @abstractmethod
    def delete(self, key: str) -> None:
        raise NotImplementedError


class LocalFilesystemStorage(StorageProvider):
    name = "local"

    def __init__(self, root: str, max_size: int) -> None:
        self.root = Path(root).expanduser().resolve()
        self.max_size = max_size

    def _path(self, key: str) -> Path:
        candidate = (self.root / key).resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError as exc:
            raise StorageError("Invalid storage key") from exc
        return candidate

    def _remove_empty_parents(self, directory: Path) -> None:
        while directory != self.root:
            try:
                directory.rmdir()
            except OSError:
                break
            directory = directory.parent

    def store(self, stream: BinaryIO, key: str) -> int:
        target = self._path(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(f".{target.name}.{uuid4().hex}.tmp")
        size = 0
        try:
            with temporary.open("wb") as output:
                while True:
                    chunk = stream.read(1024 * 1024)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > self.max_size:
                        raise StorageError("Attachment exceeds the configured size limit")
                    output.write(chunk)
                output.flush()
                os.fsync(output.fileno())
            temporary.replace(target)
            return size
        except Exception as exc:
            temporary.unlink(missing_ok=True)
            self._remove_empty_parents(target.parent)
            if isinstance(exc, StorageError):
                raise
            raise StorageError("Unable to store attachment") from exc

    def open(self, key: str) -> BinaryIO:
        path = self._path(key)
        if not path.is_file():
            raise StorageError("Attachment content not found")
        try:
            with path.open("rb") as stream:
                return BytesIO(stream.read())
        except OSError as exc:
            raise StorageError("Unable to read attachment") from exc

    def delete(self, key: str) -> None:
        path = self._path(key)
        try:
            path.unlink(missing_ok=True)
            self._remove_empty_parents(path.parent)
        except OSError as exc:
            raise StorageError("Unable to delete attachment content") from exc


def create_storage_provider() -> StorageProvider:
    if settings.ATTACHMENT_STORAGE_PROVIDER != "local":
        raise StorageError("Configured attachment storage provider is not supported")
    return LocalFilesystemStorage(settings.ATTACHMENT_STORAGE_ROOT, settings.ATTACHMENT_MAX_FILE_SIZE_BYTES)