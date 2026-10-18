"""File-backed audio through ordinary authoring, JSON persistence and Service DTOs.

The generated PCM WAV proves transport, not device/browser playback. No binary
fixture, audio hardware, codec probe or generation service is required.
"""

from __future__ import annotations

from base64 import b64decode
import json
from pathlib import Path
import wave

import pytest

from tangl.core import Selector
from tangl.journal.fragments import ChoiceFragment, ContentFragment, MediaFragment
from tangl.media import MediaDataType
from tangl.media.media_resource import MediaDep, MediaInventory, MediaRITStatus
from tangl.media.media_resource import MediaResourceInventoryTag as MediaRIT
from tangl.media.media_resource.resource_manager import ResourceManager
from tangl.persistence import PersistenceManager, PersistenceManagerFactory
from tangl.persistence.serializers import JsonSerializationHandler as Json
from tangl.service import ServiceManager
from tangl.service.media import MediaContentProfile, MediaRenderProfile, media_fragment_to_payload
from tangl.service.response import DirectEdgeRequest, RuntimeEnvelope
from tangl.service.user import User
from tangl.story import World


AudioSession = tuple[PersistenceManager, ServiceManager, User, World, RuntimeEnvelope, Path, Path]


@pytest.fixture(params=["music", "sound_fx", "character_vox", "narrative_vox"])
def audio_session(tmp_path: Path, request: pytest.FixtureRequest) -> AudioSession:
    media_root = tmp_path / "media"
    (media_root / "soundtrack").mkdir(parents=True)
    path = media_root / "soundtrack" / "tone.wav"
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(8000)
        output.writeframes(b"\x00\x00" * 80)
    resources = ResourceManager(media_root)
    resources.index_directory(".")
    world = World.from_script_data(
        script_data={
            "label": "audio_transport",
            "metadata": {"title": "Audio transport", "author": "Tests"},
            "scenes": {"intro": {"blocks": {
                "start": {
                    "content": "The story is playable without sound.",
                    "media": [{
                        "name": "tone.wav",
                        "media_role": request.param,
                        "staging_hints": {"media_timing": "loop"},
                    }],
                    "actions": [{"text": "Continue", "successor": "after"}],
                },
                "after": {"content": "You continued."},
            }}},
        },
        resources=resources,
    )
    persistence = PersistenceManagerFactory.create_persistence_manager(
        manager_name="json_sqlite_in_mem",
    )
    manager = ServiceManager(persistence)
    user = User(label="audio_reader")
    persistence.save(user)
    envelope = manager.create_story(user_id=user.uid, world_id=world.label, world=world)
    return persistence, manager, user, world, envelope, path, media_root


def test_authored_audio_provisions_and_restores_through_real_json(audio_session: AudioSession) -> None:
    persistence, _manager, user, world, envelope, path, root = audio_session
    emitted = next(f for f in envelope.fragments if isinstance(f, MediaFragment))
    assert emitted.content_format == "rit"
    assert emitted.content_type is MediaDataType.AUDIO
    assert emitted.media_role in {"music", "sound_fx", "character_vox", "narrative_vox"}
    assert emitted.staging_hints.media_timing == "loop"
    with ServiceManager(persistence).open_session(user_id=user.uid) as session:
        ledger = session.ledger
        dep = next(ledger.cursor.edges_out(Selector(has_kind=MediaDep)))
        restored = next(f for f in ledger.output_stream.values() if isinstance(f, MediaFragment))
        assert isinstance(persistence.storage[ledger.uid], str)
        assert json.loads(persistence.storage[ledger.uid])["kind"] == "Ledger"
        assert restored.content is dep.provider is ledger.graph.get(emitted.rit_id)
        assert restored.uid == emitted.uid
        assert restored.content.path == path
        assert restored.content.media_format == "wav"
        assert restored.content.mime_type == "audio/wav"
        assert restored.content.data_type is MediaDataType.AUDIO
        assert restored.media_role == emitted.media_role
        assert restored.staging_hints.media_timing == "loop"
        before = Json.serialize(ledger.unstructure())
        for profile, transport in [
            (MediaContentProfile.PASSTHROUGH, "path"),
            (MediaContentProfile.MEDIA_SERVER, "url"),
            (MediaContentProfile.INLINE_DATA, "data"),
        ]:
            payload = media_fragment_to_payload(
                restored, render_profile=MediaRenderProfile(content_profile=profile),
                world_id=world.label, world_media_root=root,
            )
            wire = json.loads(json.dumps(payload))
            assert wire["content_format"] == transport
            assert wire["rit_id"] == str(emitted.rit_id)
            assert wire["uid"] == str(emitted.uid)
            assert wire["media_type"] == "audio"
            assert wire["media_role"] == emitted.media_role
            assert wire["media_format"] == "wav"
            assert wire["mime_type"] == "audio/wav"
            if transport == "path":
                assert wire["path"] == str(path)
            elif transport == "url":
                assert wire["url"] == "/media/world/audio_transport/soundtrack/tone.wav"
            else:
                assert b64decode(wire["data"]) == path.read_bytes()
        assert Json.serialize(ledger.unstructure()) == before


def test_unsupported_audio_profile_keeps_narrative_playable_and_journal_unchanged(
    audio_session: AudioSession,
) -> None:
    persistence, manager, user, world, _envelope, _path, _root = audio_session
    envelope = manager.get_story_update(user_id=user.uid)
    with manager.open_session(user_id=user.uid) as session:
        before = Json.serialize(session.ledger.unstructure())
        fragment = next(f for f in session.ledger.output_stream.values() if isinstance(f, MediaFragment))
        assert media_fragment_to_payload(
            fragment, render_profile=MediaRenderProfile(include_audio=False),
        ) is None
        assert Json.serialize(session.ledger.unstructure()) == before
    assert any(isinstance(f, ContentFragment) and not isinstance(f, MediaFragment)
               for f in envelope.fragments)
    choice = next(f for f in envelope.fragments if isinstance(f, ChoiceFragment))
    result = manager.resolve_choice(
        user_id=user.uid, request=DirectEdgeRequest(edge_id=choice.edge_id),
    )
    assert any(isinstance(f, ContentFragment) and f.content == "You continued."
               for f in result.fragments)
    with ServiceManager(persistence).open_session(user_id=user.uid) as session:
        assert session.ledger.graph.get(fragment.rit_id) is not None
        assert session.ledger.output_stream.get(fragment.uid).rit_id == fragment.rit_id


def test_unsupported_audio_can_use_existing_text_fallback() -> None:
    fragment = MediaFragment(
        content="https://example.invalid/music.wav", content_format="url",
        content_type=MediaDataType.AUDIO, fallback_text="Music is available.",
    )
    before = fragment.unstructure()
    payload = media_fragment_to_payload(fragment, render_profile=MediaRenderProfile(include_audio=False))
    assert payload["fragment_type"] == "content"
    assert payload["text"] == "Music is available."
    assert fragment.unstructure() == before


def test_audio_omission_uses_resource_medium_even_with_generic_fragment_type(
    audio_session: AudioSession,
) -> None:
    _persistence, _manager, _user, _world, envelope, _path, _root = audio_session
    fragment = next(f for f in envelope.fragments if isinstance(f, MediaFragment))
    generic = fragment.evolve(content_type=MediaDataType.MEDIA)
    assert media_fragment_to_payload(
        generic, render_profile=MediaRenderProfile(include_audio=False),
    ) is None


@pytest.mark.parametrize("scope", ["world", "story", "sys"])
def test_audio_url_uses_existing_scope_routing(audio_session: AudioSession, scope: str) -> None:
    _persistence, _manager, _user, _world, envelope, _path, root = audio_session
    fragment = next(f for f in envelope.fragments if isinstance(f, MediaFragment)).evolve(scope=scope)
    payload = media_fragment_to_payload(
        fragment, world_id="world", story_id="story", world_media_root=root,
        story_media_root=root, system_media_root=root,
    )
    prefix = {"world": "/media/world/world", "story": "/media/story/story", "sys": "/media/sys"}[scope]
    assert payload["url"] == f"{prefix}/soundtrack/tone.wav"
    assert payload["content_format"] == "url"


def test_fallback_metadata_and_identity_describe_actual_audio_resource(
    audio_session: AudioSession,
) -> None:
    _persistence, _manager, _user, world, _envelope, path, root = audio_session
    actual = world.resources.get_rit("tone.wav")
    pending = MediaRIT(
        status=MediaRITStatus.PENDING, data_type=MediaDataType.AUDIO,
        derivation_spec={"fallback_ref": "tone.wav"},
        media_format="m4a", mime_type="audio/mp4",
    )
    fragment = MediaFragment(content=pending, content_format="rit", content_type=MediaDataType.AUDIO)
    payload = media_fragment_to_payload(
        fragment, world_id=world.label, world_media_root=root,
        render_profile=MediaRenderProfile(static_inventories=(
            MediaInventory(registry=world.resources.registry, scope="world"),
        )),
    )
    assert payload["rit_id"] == str(actual.uid) != str(pending.uid)
    assert payload["media_format"] == "wav"
    assert payload["mime_type"] == "audio/wav"
    assert payload["url"].endswith("/soundtrack/tone.wav")


@pytest.mark.parametrize("data_type", [MediaDataType.VIDEO, MediaDataType.ANIMATION])
def test_non_audio_media_server_exclusions_are_unchanged(
    tmp_path: Path, data_type: MediaDataType,
) -> None:
    path = tmp_path / "clip.mp4"
    path.write_bytes(b"transport-only fixture")
    fragment = MediaFragment(
        content=MediaRIT(path=path, data_type=data_type), content_format="rit", content_type=data_type,
    )
    payload = media_fragment_to_payload(fragment, world_id="world")
    assert payload["content_format"] is None
    assert payload["unsupported_reason"] == "unsupported_media_type"


LFS_POINTER = (
    "version https://git-lfs.github.com/spec/v1\n"
    f"oid sha256:{'a' * 64}\n"
    "size 1400000\n"
)


@pytest.mark.parametrize("profile", list(MediaContentProfile))
@pytest.mark.parametrize("fallback_text", [None, "Music has not been downloaded."])
def test_authored_lfs_pointer_is_unavailable_without_impairing_choices(
    tmp_path: Path, profile: MediaContentProfile, fallback_text: str | None,
) -> None:
    path = tmp_path / "theme.mp3"
    path.write_text(LFS_POINTER, encoding="ascii")
    resources = ResourceManager(tmp_path)
    resources.index_directory(".")
    assert resources.get_rit("theme.mp3") is None
    with pytest.raises(ValueError, match="not materialized"):
        resources.register_file(path)
    # A reference retained before a file becomes a pointer must also be safe.
    rit = MediaRIT(path=path)
    assert rit.preset_content_hash is None
    assert rit.get_content_hash() is None
    world = World.from_script_data(
        script_data={
            "label": "unfetched_audio",
            "scenes": {"intro": {"blocks": {
                "start": {
                    "content": "The story remains playable.",
                    "media": [{"name": "theme.mp3", "media_role": "music",
                               "fallback_text": fallback_text}],
                    "actions": [{"text": "Continue", "successor": "after"}],
                },
                "after": {"content": "You continued."},
            }}},
        },
        resources=resources,
    )
    persistence = PersistenceManagerFactory.create_persistence_manager(
        manager_name="json_sqlite_in_mem",
    )
    user = User(label="offline_reader")
    persistence.save(user)
    manager = ServiceManager(persistence)
    envelope = manager.create_story(user_id=user.uid, world_id=world.label, world=world)
    with ServiceManager(persistence).open_session(user_id=user.uid) as session:
        ledger = session.ledger
        before = Json.serialize(ledger.unstructure())
        for fragment in ledger.output_stream.values():
            projected = media_fragment_to_payload(
                fragment, world_id=world.label, world_media_root=tmp_path,
                render_profile=MediaRenderProfile(content_profile=profile),
            )
            if projected is not None:
                assert not {"url", "path", "data"} & projected.keys()
        if fallback_text is not None:
            assert any(isinstance(f, ContentFragment) and f.content == fallback_text
                       for f in ledger.output_stream.values())
        fragment = MediaFragment(
            content=rit, content_format="rit", content_type=MediaDataType.AUDIO,
            fallback_text=fallback_text,
        )
        fragment_before = fragment.unstructure()
        payload = media_fragment_to_payload(
            fragment, world_id=world.label, world_media_root=tmp_path,
            render_profile=MediaRenderProfile(content_profile=profile),
        )
        if fallback_text is None:
            assert payload is None
        else:
            assert payload["fragment_type"] == "content"
            assert payload["text"] == fallback_text
            assert not {"url", "path", "data"} & payload.keys()
        assert fragment.unstructure() == fragment_before
        assert Json.serialize(ledger.unstructure()) == before
    choice = next(f for f in envelope.fragments if isinstance(f, ChoiceFragment))
    result = manager.resolve_choice(
        user_id=user.uid, request=DirectEdgeRequest(edge_id=choice.edge_id),
    )
    assert any(isinstance(f, ContentFragment) and f.content == "You continued."
               for f in result.fragments)


@pytest.mark.parametrize("profile", list(MediaContentProfile))
def test_unmaterialized_source_is_retryable_after_wav_arrives(
    audio_session: AudioSession, tmp_path: Path, profile: MediaContentProfile,
) -> None:
    _persistence, _manager, _user, _world, _envelope, wav_path, _root = audio_session
    path = tmp_path / "optional" / "theme.wav"
    path.parent.mkdir()
    path.write_text(LFS_POINTER, encoding="ascii")
    resources = ResourceManager(path.parent)
    assert resources.index_directory(".") == []
    with pytest.raises(ValueError, match="not materialized"):
        resources.register_file(path)
    rit = MediaRIT(path=path)
    fragment = MediaFragment(content=rit, content_format="rit", content_type=MediaDataType.AUDIO)
    render_profile = MediaRenderProfile(content_profile=profile)
    before = fragment.unstructure()
    assert media_fragment_to_payload(fragment, render_profile=render_profile, world_id="retry") is None
    path.write_bytes(wav_path.read_bytes())
    payload = media_fragment_to_payload(fragment, render_profile=render_profile, world_id="retry")
    assert payload["content_format"] == {
        MediaContentProfile.MEDIA_SERVER: "url",
        MediaContentProfile.PASSTHROUGH: "path",
        MediaContentProfile.INLINE_DATA: "data",
    }[profile]
    assert payload["rit_id"] == str(rit.uid)
    assert payload["mime_type"] == "audio/wav"
    assert fragment.unstructure() == before
    fresh = resources.register_file(path)
    assert fresh.preset_content_hash is not None
    assert fresh.get_content_hash() == rit.get_content_hash()
