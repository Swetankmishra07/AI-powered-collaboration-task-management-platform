from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class NotificationResponse(BaseModel):
    id: int
    user_id: int
    type: str
    title: str
    message: str
    related_entity_type: Optional[str]
    related_entity_id: Optional[int]
    task_id: Optional[int]
    is_read: bool
    read_at: Optional[datetime]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
