from __future__ import annotations

from tangl.service.response import InfoModel, StoryInfo, SystemInfo, UserInfo, WorldInfo


def test_all_info_models_inherit_infomodel() -> None:
    assert issubclass(SystemInfo, InfoModel)
    assert issubclass(UserInfo, InfoModel)
    assert issubclass(WorldInfo, InfoModel)
    assert issubclass(StoryInfo, InfoModel)


def test_system_info_has_no_http_fields() -> None:
    info = SystemInfo(
        engine="StoryTangl",
        version="3.7.0",
        uptime="0:05:23",
        worlds=["intro", "demo"],
        num_users=5,
    )

    assert not hasattr(info, "app_url")
    assert not hasattr(info, "response_id")
    assert not hasattr(info, "timestamp")
