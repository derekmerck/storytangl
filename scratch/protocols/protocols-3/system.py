from __future__ import annotations
from typing import Protocol, TYPE_CHECKING, Any
from datetime import timedelta

from pydantic import BaseModel

from tangl.type_hints import UniqueLabel, Identifier

if TYPE_CHECKING:
    from .world import WorldId
    from .user import UserFeature, UserSecret
    from .content import MediaData, MediaFragment
    from .service import ClientFeature

# ----------------
# System Type Hints
# ----------------
SystemFeature = UniqueLabel   # world list, federated services, media server

# ----------------
# System Info
# ----------------
class SystemHandler(Protocol):
    """System management, no world, story instance, or user"""

    @classmethod
    async def get_system_info(cls, feature_config: dict[SystemFeature, Any] = None) -> SystemInfo:
        """Get detailed system information including health and installed worlds"""

    @classmethod
    async def get_key_for_secret(cls, secret: str) -> UserSecret:
        """Recover api_key from secret"""

    @classmethod
    async def get_system_media(cls, media_id: Identifier) -> MediaData: ...  # or offload to media server

# ----------------
# System Info
# ----------------
class SystemInfo(BaseModel, allow_extra=True):

    uptime: timedelta
    worlds: set[WorldId]
    active_users: int
    active_stories: int
    system_features: set[SystemFeature]     # media endpoints, federated service advertisements, etc.
    client_features: set[ClientFeature]     # features supported by response handler, text formats, media, styled dialog, etc.
    user_features: set[UserFeature]         # features and prefs supported by the user manager
    media: list[MediaFragment] = None


