from typing import Literal, Any, Optional
from uuid import UUID

from .base_response import BaseResponse

RuntimeJob = Literal['create', 'read', 'update', 'drop']

class RuntimeInfo(BaseResponse):
    job: RuntimeJob

    user_id: Optional[UUID] = None
    world_id: Optional[UUID] = None
    story_id: Optional[UUID] = None
    node_id: Optional[UUID] = None

    expr: Optional[str] = None
    result: Any = None
    errors: Optional[str] = None

    # For user create/update responses, could stick it in "result" as a dict key
    user_secret: Optional[str] = None

