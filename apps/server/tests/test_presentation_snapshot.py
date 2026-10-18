"""Actual HTTP response filtering must retain an explicitly empty music slot."""

from __future__ import annotations

from pathlib import Path
import wave

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from tangl.journal.fragments import MediaFragment
from tangl.media.media_resource import MediaResourceInventoryTag as MediaRIT
from tangl.rest.routers.story_router import _serialize_runtime_envelope
from tangl.service.response import PresentationSnapshot, RuntimeEnvelope, RuntimeEnvelopePayload


@pytest.mark.parametrize(
    ("selected", "profile"), [(False, "raw"), (True, "raw"), (True, "no_audio")],
)
def test_http_snapshot_resolves_media_and_keeps_explicit_null(
    tmp_path: Path, selected: bool, profile: str,
) -> None:
    path = tmp_path / "music.wav"
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(8000)
        output.writeframes(b"\0\0" * 80)
    cue = MediaFragment(
        content=MediaRIT.from_source(path), content_format="rit", media_role="music",
    ) if selected else None
    envelope = RuntimeEnvelope(
        metadata={"world_id": "snapshot_http"}, presentation=PresentationSnapshot(music=cue),
    )
    app = FastAPI()

    @app.get("/", response_model=RuntimeEnvelopePayload, response_model_exclude_none=True)
    def response():
        return _serialize_runtime_envelope(envelope, render_profile=profile)

    with TestClient(app) as client:
        payload = client.get("/").json()
    assert payload["fragments"] == []
    if selected and profile == "raw":
        assert payload["presentation"]["music"]["url"] == "/media/world/snapshot_http/music.wav"
        assert payload["presentation"]["music"]["rit_id"] == str(cue.rit_id)
        assert str(path) not in str(payload)
    else:
        assert payload["presentation"] == {"music": None}
