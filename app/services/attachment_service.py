import logging
from pathlib import Path
from typing import BinaryIO, Optional
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.models import Attachment, User
from app.services.storage_service import StorageError, StorageProvider, create_storage_provider
from app.services.task_service import TaskService


logger = logging.getLogger(__name__)

ALLOWED_CONTENT_TYPES = {
    ".txt": "text/plain",
    ".csv": "text/csv",
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}

storage_provider: StorageProvider = create_storage_provider()


def _validate_filename(upload: UploadFile) -> str:
    filename = upload.filename or ""
    if (
        not filename
        or any(ord(character) < 32 or ord(character) == 127 for character in filename)
        or '"' in filename
        or "\x00" in filename
        or Path(filename).name != filename
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid attachment filename.")
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_CONTENT_TYPES or upload.content_type != ALLOWED_CONTENT_TYPES[extension]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported attachment type.")
    return extension


class AttachmentService:
    @staticmethod
    def list_for_task(task_id: int, user: User, db: Session) -> list[Attachment]:
        TaskService.get_task_by_id(task_id, user, db)
        return db.query(Attachment).filter(Attachment.task_id == task_id).order_by(Attachment.id).all()

    @staticmethod
    def upload(task_id: int, upload: UploadFile, user: User, db: Session) -> Attachment:
        TaskService.get_task_by_id(task_id, user, db)
        extension = _validate_filename(upload)
        stored_filename = f"{uuid4().hex}{extension}"
        stored_key = f"tasks/{task_id}/{stored_filename}"
        try:
            file_size = storage_provider.store(upload.file, stored_key)
        except StorageError as exc:
            try:
                storage_provider.delete(stored_key)
            except StorageError:
                logger.exception("Unable to clean up failed attachment storage")
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Attachment storage is unavailable.") from exc

        attachment = Attachment(
            original_filename=upload.filename,
            stored_filename=stored_filename,
            content_type=upload.content_type,
            file_size=file_size,
            storage_provider=storage_provider.name,
            storage_key=stored_key,
            uploader_id=user.id,
            task_id=task_id,
        )
        try:
            db.add(attachment)
            db.commit()
            db.refresh(attachment)
        except Exception:
            db.rollback()
            try:
                storage_provider.delete(stored_key)
            except StorageError:
                logger.exception("Unable to clean up attachment after database failure")
            raise
        return attachment

    @staticmethod
    def get_for_task(attachment_id: int, task_id: int, user: User, db: Session) -> Attachment:
        TaskService.get_task_by_id(task_id, user, db)
        attachment = db.query(Attachment).filter(
            Attachment.id == attachment_id,
            Attachment.task_id == task_id,
        ).first()
        if attachment is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found.")
        return attachment

    @staticmethod
    def delete(attachment_id: int, task_id: int, user: User, db: Session) -> None:
        attachment = AttachmentService.get_for_task(attachment_id, task_id, user, db)
        storage_key = attachment.storage_key
        try:
            db.delete(attachment)
            db.commit()
        except Exception:
            db.rollback()
            raise
        try:
            storage_provider.delete(storage_key)
        except StorageError:
            logger.exception("Attachment metadata deleted but content cleanup failed")
