"""Native system metadata response model."""

from __future__ import annotations

from pydantic import AnyUrl, field_serializer

from tangl.info import __url__
from tangl.service.response.native_response import InfoModel


class SystemInfo(InfoModel):
    engine: str
    version: str
    uptime: str
    worlds: list[str] | int
    num_users: int
    homepage_url: AnyUrl = __url__

    @field_serializer("homepage_url")
    @classmethod
    def serialize_homepage(cls, v: AnyUrl, _info):
        return str(v)
