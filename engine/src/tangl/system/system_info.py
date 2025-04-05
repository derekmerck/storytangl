from typing import Any, Optional

from pydantic import BaseModel, AnyUrl

from tangl.info import __url__

class SystemInfo(BaseModel):
    engine: str
    version: str
    uptime: str
    worlds: int
    users: int
    homepage_url: AnyUrl = __url__
    # media: Optional[list[MediaRecord | JournalMediaFragment]] = None

    # these are set by the server
    app_url: Optional[AnyUrl] = None
    api_url: Optional[AnyUrl] = None
    guide_url: Optional[AnyUrl] = None
