from __future__ import annotations

from uuid import uuid4

from tangl.core import BaseFragment
from tangl.service.response.native_response import FragmentStream, InfoModel, MediaNative, RuntimeInfo


def test_runtime_info_ok() -> None:
    info = RuntimeInfo.ok(cursor_id=uuid4(), step=5, message="Choice resolved", choice_label="open_door")

    assert info.status == "ok"
    assert info.step == 5
    assert info.details is not None
    assert info.details["choice_label"] == "open_door"


def test_runtime_info_error() -> None:
    info = RuntimeInfo.error(code="NOT_FOUND", message="Choice not available", cursor_id=uuid4(), step=5)

    assert info.status == "error"
    assert info.code == "NOT_FOUND"
    assert info.cursor_id is not None


def test_info_model_base() -> None:
    class TestInfo(InfoModel):
        value: str

    info = TestInfo(value="test")
    assert isinstance(info, InfoModel)


def test_fragment_stream_alias() -> None:
    fragments: FragmentStream = [
        BaseFragment(fragment_type="text"),
        BaseFragment(fragment_type="choice"),
    ]

    assert isinstance(fragments, list)
    assert all(isinstance(fragment, BaseFragment) for fragment in fragments)


def test_media_native_alias() -> None:
    assert MediaNative is not None
