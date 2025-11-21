"""Native system metadata response model."""

from __future__ import annotations

from pydantic import AnyUrl

from tangl.info import __url__
from tangl.service.response.native_response import InfoModel


class SystemInfo(InfoModel):
    engine: str
    version: str
    uptime: str
    worlds: list[str] | int
    num_users: int
    homepage_url: AnyUrl = __url__
