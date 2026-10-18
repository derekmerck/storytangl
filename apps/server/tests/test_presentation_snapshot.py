"""Actual HTTP response filtering must retain an explicitly empty music slot."""

from __future__ import annotations

from pathlib import Path
import wave

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from tangl.core import Graph
from tangl.journal.fragments import ControlFragment, MediaFragment
from tangl.journal.presentation import desired_music
from tangl.media import MediaDataType
from tangl.media.media_resource import MediaResourceInventoryTag as MediaRIT, MediaRITStatus
from tangl.persistence.serializers import JsonSerializationHandler as Json
from tangl.rest.routers.story_router import _serialize_runtime_envelope
from tangl.service.remote_service_manager import RemoteServiceManager
from tangl.service.response import PresentationSnapshot, RuntimeEnvelope, RuntimeEnvelopePayload
from tangl.vm import Ledger


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


def test_pending_poll_remains_incremental_but_not_in_music_snapshot() -> None:
    graph = Graph()
    start = graph.add_node(label="start")
    rit = MediaRIT(
        data=b"pending audio", data_type=MediaDataType.AUDIO,
        status=MediaRITStatus.PENDING, job_id="music-job",
    )
    graph.add(rit)
    cue = MediaFragment(content=rit, content_format="rit", media_role="music")
    ledger = Ledger.from_graph(graph, entry_id=start.uid)
    ledger.output_stream.append(cue)
    before = Json.serialize(ledger.unstructure())
    app = FastAPI()

    @app.get("/", response_model=RuntimeEnvelopePayload, response_model_exclude_none=True)
    def response():
        return _serialize_runtime_envelope(RuntimeEnvelope(
            fragments=[cue],
            presentation=PresentationSnapshot(music=desired_music(ledger.get_journal())),
        ), render_profile="poll")

    with TestClient(app) as client:
        for _ in range(2):
            payload = client.get("/").json()
            assert payload["presentation"] == {"music": None}
            assert payload["fragments"][0]["directive"] == "poll_media"
            assert payload["fragments"][0]["job_id"] == "music-job"
            remote = RemoteServiceManager(api_url="http://example.invalid")
            assert remote._decode_runtime_envelope(payload).presentation.music is None
    assert Json.serialize(ledger.unstructure()) == before


@pytest.mark.parametrize("hints", [{"media_x": 0.25}, {"media_timing": None}, None])
def test_http_presentation_patch_preserves_supplied_nulls(hints: dict | None) -> None:
    control = ControlFragment(
        target={"kind": "handle", "handle": "character:alice"}, patch_kind="presentation",
        payload={"staging_hints": hints},
    )
    app = FastAPI()

    @app.get("/", response_model=RuntimeEnvelopePayload, response_model_exclude_none=True)
    def response():
        return _serialize_runtime_envelope(RuntimeEnvelope(fragments=[control]))

    with TestClient(app) as client:
        payload = client.get("/").json()
    assert payload["fragments"][0]["payload"] == {"staging_hints": hints}
