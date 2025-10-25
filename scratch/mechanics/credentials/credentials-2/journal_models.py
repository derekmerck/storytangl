from typing import Optional
from enum import Enum

from tangl.entity import BaseJournalItem
from tangl.media import JournalMediaItem
from .enums import Region

class CredentialMediaRole(Enum):
    BASE_IMAGE = "base_image"
    SEAL = "seal"
    HOLDER_IMAGE = "holder_image"

class JournalCredentialMedia(JournalMediaItem):
    media_role: CredentialMediaRole

class JournalCredential(BaseJournalItem):

    credential_id: str
    credential_type: str
    issuer: Region
    issued: str | int
    media: list[JournalCredentialMedia]
    expiry: Optional[str | int]
    holder_id: Optional[str]
