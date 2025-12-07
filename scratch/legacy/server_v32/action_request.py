from pydantic import BaseModel, Field

from tangl.type_hints import Identifier


class ActionRequest(BaseModel):
    uid: Identifier = Field(..., alias="action_id")
    payload: dict = None
