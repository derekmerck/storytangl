"""Audio DTO transport and ordinary static HTTP serving, not client playback."""

from __future__ import annotations

from base64 import b64decode
from io import BytesIO
import json
from pathlib import Path
from uuid import uuid4
import wave

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from tangl.journal.fragments import ChoiceFragment, ContentFragment, MediaFragment
from tangl.media import MediaDataType
from tangl.media.media_resource import MediaResourceInventoryTag as MediaRIT
from tangl.rest.media_server import mount_world_media
from tangl.rest.routers.story_router import _serialize_runtime_envelope
from tangl.service.response import RuntimeEnvelope


@pytest.mark.parametrize(
    ("profile", "expected_format"),
    [("raw", "url"), ("passthrough", "path"), ("inline_data", "data")],
)
def test_audio_envelope_keeps_metadata_and_serves_the_actual_wav(
    tmp_path: Path, profile: str, expected_format: str,
) -> None:
    path = tmp_path / "tone.wav"
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(8000)
        output.writeframes(b"\x00\x00" * 80)
    rit = MediaRIT.from_source(path)
    fragment = MediaFragment(
        content=rit, content_format="rit", content_type=MediaDataType.AUDIO, media_role="music",
    )
    envelope = RuntimeEnvelope(
        fragments=[fragment], metadata={"world_id": "audio_http"},
    )
    before = fragment.unstructure()
    wire = json.loads(json.dumps(_serialize_runtime_envelope(envelope, render_profile=profile)))
    payload = wire["fragments"][0]
    assert payload["content_format"] == expected_format
    assert payload["rit_id"] == str(rit.uid)
    assert payload["media_type"] == "audio"
    assert payload["media_role"] == "music"
    assert payload["media_format"] == "wav"
    assert payload["mime_type"] == "audio/wav"
    if expected_format == "url":
        media_app = FastAPI()
        mount_world_media(media_app, "audio_http", tmp_path)
        app = FastAPI()
        app.mount("/media", media_app)
        with TestClient(app) as client:
            response = client.get(payload["url"])
        assert response.status_code == 200
        assert response.headers["content-type"] in {"audio/wav", "audio/x-wav", "audio/vnd.wave"}
        actual = response.content
    elif expected_format == "path":
        actual = Path(payload["path"]).read_bytes()
    else:
        actual = b64decode(payload["data"])
    assert actual == path.read_bytes()
    with wave.open(BytesIO(actual), "rb") as audio:
        assert (audio.getnchannels(), audio.getsampwidth(), audio.getframerate()) == (1, 2, 8000)
        assert audio.getnframes() == 80
    assert fragment.unstructure() == before


def test_no_audio_rest_profile_omits_audio_but_keeps_choices() -> None:
    media = MediaFragment(
        content="https://example.invalid/tone.wav", content_format="url",
        content_type=MediaDataType.AUDIO, media_role="music",
    )
    choice = ChoiceFragment(edge_id=uuid4(), text="Continue")
    envelope = RuntimeEnvelope(fragments=[ContentFragment(content="Hello"), media, choice])
    before = media.unstructure()
    payload = _serialize_runtime_envelope(envelope, render_profile="raw,no_audio")
    assert [f["fragment_type"] for f in payload["fragments"]] == ["content", "choice"]
    assert payload["fragments"][-1]["edge_id"] == str(choice.edge_id)
    assert media.unstructure() == before
