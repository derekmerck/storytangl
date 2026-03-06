from __future__ import annotations
import logging
import base64
from uuid import UUID, uuid4

from tangl.service.controllers import ApiKeyInfo, UserController
from tangl.service.response import RuntimeInfo
from tangl.utils.hash_secret import key_for_secret, uuid_for_secret


class _StubMedia:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def get_content(self, **kwargs: object) -> str:
        self.calls.append(kwargs)
        return "content"


class _StubUser:
    def __init__(self) -> None:
        self.uid = uuid4()
        self.secret = "secret"
        self.updated_kwargs: dict[str, object] | None = None
        self._story_ids: list[UUID] = [uuid4(), uuid4()]
        self.media: dict[str, _StubMedia] = {"avatar": _StubMedia()}

    def update(self, **kwargs: object) -> None:
        self.updated_kwargs = kwargs

    def get_story_ids(self) -> list[UUID]:
        return list(self._story_ids)

    def unlink_story(self, story_id: UUID) -> None:
        self._story_ids.remove(story_id)

    def find_one(self, *, alias: str) -> _StubMedia:
        return self.media[alias]


def test_user_controller_endpoints_use_user_only() -> None:
    endpoints = UserController.get_api_endpoints()
    assert "drop_story" not in endpoints
    for endpoint in endpoints.values():
        for name, hint in endpoint.type_hints().items():
            if name == "return":
                continue
            qualname = getattr(hint, "__name__", str(hint))
            assert "Story" not in qualname
            assert "Ledger" not in qualname


def test_update_user_returns_api_key_info() -> None:
    controller = UserController()
    user = _StubUser()
    result = controller.update_user(user, display_name="Player")
    assert isinstance(result, RuntimeInfo)
    assert result.status == "ok"
    assert user.updated_kwargs == {"display_name": "Player"}
    expected = key_for_secret(user.secret)
    assert result.details is not None
    assert result.details.get("api_key") == expected


def test_get_user_media_resolves_identifier() -> None:
    controller = UserController()
    user = _StubUser()
    media = controller.get_user_media(user, "avatar", size="thumb")
    assert media == "content"
    assert user.media["avatar"].calls == [{"size": "thumb"}]


def test_drop_user_unlinks_all_stories() -> None:
    controller = UserController()
    user = _StubUser()
    expected_story_ids = set(user._story_ids)
    result = controller.drop_user(user)
    assert isinstance(result, RuntimeInfo)
    assert result.status == "ok"
    assert set(result.details.get("story_ids", [])) == {str(item) for item in expected_story_ids}
    assert user._story_ids == []


def test_create_user_returns_runtime_details() -> None:
    controller = UserController()

    result = controller.create_user(secret="dev-secret")

    assert isinstance(result, RuntimeInfo)
    assert result.status == "ok"
    details = result.details or {}
    user = details.get("user")
    assert user is not None and hasattr(user, "uid")
    assert details.get("user_id") == str(user.uid)
