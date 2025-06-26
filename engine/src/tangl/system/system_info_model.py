from typing import Any, Optional

from pydantic import AnyUrl

from tangl.info import __url__
from tangl.service.response import BaseResponse

class SystemInfo(BaseResponse):
    engine: str
    version: str
    uptime: str
    worlds: list[str]
    num_users: int
    homepage_url: AnyUrl = __url__
    # media: Optional[list[MediaRecord | JournalMediaFragment]] = None

    # these are set by the server
    app_url: Optional[AnyUrl] = None
    api_url: Optional[AnyUrl] = None
    guide_url: Optional[AnyUrl] = None
