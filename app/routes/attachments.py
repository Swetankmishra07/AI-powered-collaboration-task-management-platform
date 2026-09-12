from fastapi import APIRouter, Depends, File, Response, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models import User
from app.dependencies.authorization import require_member
from app.schemas.attachment import AttachmentResponse
from app.services.attachment_service import AttachmentService, storage_provider
from app.services.storage_service import StorageError


router = APIRouter(tags=["Attachments"])


@router.post("/tasks/{task_id}/attachments", response_model=AttachmentResponse, status_code=status.HTTP_201_CREATED)
def upload_attachment(
    task_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(require_member),
    db: Session = Depends(get_db),
):
    return AttachmentService.upload(task_id, file, current_user, db)


@router.get("/tasks/{task_id}/attachments", response_model=list[AttachmentResponse])
def list_attachments(task_id: int, current_user: User = Depends(require_member), db: Session = Depends(get_db)):
    return AttachmentService.list_for_task(task_id, current_user, db)


@router.get("/tasks/{task_id}/attachments/{attachment_id}")
def download_attachment(
    task_id: int,
    attachment_id: int,
    current_user: User = Depends(require_member),
    db: Session = Depends(get_db),
):
    attachment = AttachmentService.get_for_task(attachment_id, task_id, current_user, db)
    try:
        stream = storage_provider.open(attachment.storage_key)
    except StorageError as exc:
        from fastapi import HTTPException

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment content not found.") from exc
    return StreamingResponse(
        stream,
        media_type=attachment.content_type,
        headers={"Content-Disposition": f'attachment; filename="{attachment.original_filename}"'},
    )


@router.delete("/tasks/{task_id}/attachments/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_attachment(
    task_id: int,
    attachment_id: int,
    current_user: User = Depends(require_member),
    db: Session = Depends(get_db),
):
    AttachmentService.delete(attachment_id, task_id, current_user, db)
    return Response(status_code=status.HTTP_204_NO_CONTENT)