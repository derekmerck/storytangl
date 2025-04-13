from uuid import UUID

from pydantic import BaseModel

class UserSecret(BaseModel):
    user_secret: str
    user_id: UUID
    api_key: str
