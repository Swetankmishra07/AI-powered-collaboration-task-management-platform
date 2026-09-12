from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class ActivityResponse(BaseModel):
    id: int
    actor_id: Optional[int]
    task_id: Optional[int]
    action: str
    entity_type: str
    entity_id: int
    metadata_json: dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
