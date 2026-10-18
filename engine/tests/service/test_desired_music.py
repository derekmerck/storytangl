"""Desired music survives journal windows, JSON reopen and normal transport policy."""

from __future__ import annotations

import json
from pathlib import Path
import wave

import pytest

from tangl.journal.fragments import ChoiceFragment, ControlFragment, MediaFragment
from tangl.media.media_resource.resource_manager import ResourceManager
from tangl.media.media_resource import MediaInventory, MediaRITStatus
from tangl.persistence import PersistenceManagerFactory
from tangl.persistence.serializers import JsonSerializationHandler as Json
from tangl.rest.routers.story_router import _serialize_runtime_envelope
from tangl.service import ServiceManager
from tangl.service.media import MediaRenderProfile
from tangl.service.response import DirectEdgeRequest, RuntimeEnvelopePayload
from tangl.service.remote_service_manager import RemoteServiceManager
from tangl.service.user import User
from tangl.story import World


@pytest.fixture
def music_session(tmp_path: Path):
    path = tmp_path / "music.wav"
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(8000)
        output.writeframes(b"\0\0" * 80)
    resources = ResourceManager(tmp_path)
    resources.register_file(path)
    blocks = {f"b{i}": {
        "content": f"Block {i}",
        "actions": [{"text": "Continue", "successor": f"b{i+1}"}] if i < 4 else [],
    } for i in range(5)}
    blocks["b0"]["media"] = [{
        "name": "music.wav", "media_role": "music", "presentation_handle": "island:theme",
        "staging_hints": {"media_timing": "loop"},
    }]
    world = World.from_script_data(
        script_data={"label": "bgm_snapshot", "scenes": {"intro": {"blocks": blocks}}},
        resources=resources,
    )
    persistence = PersistenceManagerFactory.create_persistence_manager(
        manager_name="json_sqlite_in_mem",
    )
    user = User(label="music_reader")
    persistence.save(user)
    manager = ServiceManager(persistence)
    first = manager.create_story(user_id=user.uid, world_id=world.label, world=world)
    return persistence, user, first, path


def test_fresh_service_fold_uses_history_before_limited_window_without_mutation(
    music_session,
) -> None:
    persistence, user, first, _path = music_session
    selected = first.presentation.music
    assert isinstance(selected, MediaFragment)
    assert selected.presentation_handle == "island:theme"
    manager = ServiceManager(persistence)
    envelope = first
    for _ in range(4):
        choice = next(f for f in envelope.fragments if isinstance(f, ChoiceFragment))
        envelope = manager.resolve_choice(
            user_id=user.uid, request=DirectEdgeRequest(edge_id=choice.edge_id),
        )
    manager = ServiceManager(persistence)
    with manager.open_session(user_id=user.uid) as session:
        ledger_id = session.ledger.uid
        before = Json.serialize(session.ledger.unstructure())
        stored = persistence.storage[ledger_id]
        assert isinstance(stored, str)
        assert "presentation" not in json.loads(stored)
    for _ in range(2):
        update = manager.get_story_update(user_id=user.uid, since_step=3, limit=1)
        assert len(update.fragments) == 1
        assert not any(isinstance(f, MediaFragment) for f in update.fragments)
        assert update.presentation.music.rit_id == selected.rit_id
        assert update.presentation.music.uid == selected.uid
        assert update.presentation.music.staging_hints.media_timing == "loop"
    with manager.open_session(user_id=user.uid) as session:
        assert Json.serialize(session.ledger.unstructure()) == before
    assert persistence.storage[ledger_id] == stored
    with manager.open_session(user_id=user.uid, write_back=True) as session:
        session.ledger.output_stream.append(ControlFragment(
            fragment_type="delete", target={"kind": "role", "media_role": "music"},
        ))
    stopped = ServiceManager(persistence).get_story_update(user_id=user.uid, limit=1)
    assert stopped.presentation.music is None
    assert stopped.to_dto()["presentation"] == {"music": None}
    wire = RuntimeEnvelopePayload.model_validate(_serialize_runtime_envelope(stopped)).model_dump(
        mode="json", exclude_none=True,
    )
    assert wire["presentation"] == {"music": None}


@pytest.mark.parametrize(
    ("profile", "format"), [("raw", "url"), ("passthrough", "path"), ("inline_data", "data")],
)
def test_snapshot_and_restart_use_ordinary_resolved_descriptor_and_typed_dto(
    music_session, profile: str, format: str,
) -> None:
    _persistence, _user, envelope, path = music_session
    cue = envelope.presentation.music
    control = ControlFragment(
        target={"kind": "role", "media_role": "music"}, media_action="restart", media=cue,
    )
    envelope.fragments = [control]
    wire = json.loads(json.dumps(_serialize_runtime_envelope(envelope, render_profile=profile)))
    RuntimeEnvelopePayload.model_validate(wire)
    media = wire["presentation"]["music"]
    assert media["content_format"] == format
    assert media["rit_id"] == str(cue.rit_id)
    assert media["mime_type"] == "audio/wav"
    assert media["presentation_handle"] == "island:theme"
    assert "media_action" not in media
    assert "content" not in media
    assert wire["fragments"][0]["uid"] == str(control.uid)
    assert wire["fragments"][0]["media"] == media
    if format == "url":
        assert media["url"].endswith("/music.wav")
        assert str(path) not in json.dumps(wire)
    elif format == "path":
        assert media["path"] == str(path)
    hydrated = RemoteServiceManager(api_url="http://example.invalid")._decode_runtime_envelope(wire)
    assert isinstance(hydrated.presentation.music, MediaFragment)
    assert hydrated.presentation.music.rit_id == cue.rit_id
    assert hydrated.presentation.music.mime_type == "audio/wav"
    assert hydrated.fragments[0].media.rit_id == cue.rit_id
    repeated = _serialize_runtime_envelope(hydrated, render_profile=profile)
    assert repeated["presentation"]["music"]["mime_type"] == "audio/wav"


@pytest.mark.parametrize("profile", ["no_audio", "passthrough,no_audio", "inline_data,no_audio"])
def test_audio_opt_out_cannot_leak_snapshot_or_nested_control_media(
    music_session, profile: str,
) -> None:
    _persistence, _user, envelope, _path = music_session
    cue = envelope.presentation.music
    envelope.fragments = [ControlFragment(
        target={"kind": "role", "media_role": "music"}, media_action="restart", media=cue,
    )]
    wire = _serialize_runtime_envelope(envelope, render_profile=profile)
    assert wire["presentation"] == {"music": None}
    assert wire["fragments"] == []
    assert envelope.presentation.music is cue


@pytest.mark.parametrize("source", ["missing", "lfs"])
@pytest.mark.parametrize("profile", ["raw", "passthrough", "inline_data"])
def test_unavailable_selected_resource_degrades_after_canonical_fold(
    music_session, source: str, profile: str,
) -> None:
    persistence, user, first, path = music_session
    if source == "missing":
        path.unlink()
    else:
        path.write_text("version https://git-lfs.github.com/spec/v1\n"
                        f"oid sha256:{'a' * 64}\nsize 1000000\n", encoding="ascii")
    manager = ServiceManager(persistence)
    with manager.open_session(user_id=user.uid) as session:
        before = Json.serialize(session.ledger.unstructure())
    envelope = manager.get_story_update(user_id=user.uid, limit=1)
    assert envelope.presentation.music.rit_id == first.presentation.music.rit_id
    wire = _serialize_runtime_envelope(envelope, render_profile=profile)
    assert wire["presentation"] == {"music": None}
    with manager.open_session(user_id=user.uid) as session:
        assert Json.serialize(session.ledger.unstructure()) == before


def test_snapshot_text_fallback_is_ordinary_nonplayable_content(music_session) -> None:
    _persistence, _user, envelope, _path = music_session
    envelope.presentation.music = envelope.presentation.music.evolve(
        fallback_text="Music unavailable.",
    )
    envelope.fragments = [ControlFragment(
        target={"kind": "role", "media_role": "music"}, media_action="restart",
        media=envelope.presentation.music,
    )]
    wire = _serialize_runtime_envelope(envelope, render_profile="no_audio")
    assert wire["presentation"]["music"]["fragment_type"] == "content"
    assert wire["presentation"]["music"]["text"] == "Music unavailable."
    assert not {"url", "path", "data"} & wire["presentation"]["music"].keys()
    assert wire["fragments"] == [wire["presentation"]["music"]]
    assert "media_action" not in wire["fragments"][0]


def test_path_only_descriptor_cannot_bypass_a_remote_media_profile(music_session) -> None:
    _persistence, _user, envelope, path = music_session
    cue = envelope.presentation.music.evolve(
        content=str(path), content_format="path", rit_id=envelope.presentation.music.rit_id,
    )
    envelope.presentation.music = cue
    envelope.fragments = [ControlFragment(
        target={"kind": "role", "media_role": "music"}, media_action="restart", media=cue,
    )]
    wire = _serialize_runtime_envelope(envelope)
    assert wire["presentation"] == {"music": None}
    assert wire["fragments"] == []
    assert str(path) not in json.dumps(wire)


def test_snapshot_static_fallback_names_the_actual_represented_resource(
    music_session, monkeypatch: pytest.MonkeyPatch,
) -> None:
    import importlib

    _persistence, _user, envelope, path = music_session
    original = envelope.presentation.music.content
    original.status = MediaRITStatus.PENDING
    original.derivation_spec = {"fallback_ref": "placeholder.svg"}
    placeholder = path.parent / "placeholder.svg"
    placeholder.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>', encoding="utf-8")
    resources = ResourceManager(path.parent)
    fallback = resources.register_file(placeholder)
    profile = MediaRenderProfile(static_inventories=(MediaInventory(resources.registry),))
    router = importlib.import_module("tangl.rest.routers.story_router")
    monkeypatch.setattr(router, "_media_render_profile", lambda _: profile)
    wire = _serialize_runtime_envelope(envelope)
    assert wire["presentation"]["music"]["rit_id"] == str(fallback.uid) != str(original.uid)
    assert wire["presentation"]["music"]["media_type"] == "vector"
    assert wire["presentation"]["music"]["url"].endswith("/placeholder.svg")
    assert envelope.presentation.music.rit_id == original.uid
