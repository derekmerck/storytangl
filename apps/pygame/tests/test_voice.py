"""Fresh attributed bark batches, serial playback, completion and local ducking."""
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from unittest.mock import Mock
from uuid import uuid4
import wave

import pytest

pygame = pytest.importorskip("pygame")

from tangl.journal.fragments import ChoiceFragment, MediaFragment
from tangl.media.media_resource.resource_manager import ResourceManager
from tangl.persistence import PersistenceManagerFactory
from tangl.pygame_client.bridge import PygameSessionBridge
from tangl.pygame_client.music import MusicPlayer
from tangl.pygame_client.voice import VoicePlayer
from tangl.service import ServiceManager
from tangl.service.media import media_fragment_to_payload
from tangl.service.response import PresentationSnapshot, RuntimeEnvelope
from tangl.service.world_registry import register_manual_world, pop_manual_world
from tangl.story import World


@pytest.fixture
def world(tmp_path: Path) -> Iterator[World]:
    for index, filename in enumerate(("theme", "mara", "ivo"), start=1):
        with wave.open(str(tmp_path / f"{filename}.wav"), "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(8000)
            output.writeframes(index.to_bytes(2, "little") * 800)
    resources = ResourceManager(tmp_path)
    resources.index_directory(".")
    world = World.from_script_data(script_data={
        "label": "pygame_barks_fixture",
        "actors": {"mara": {"label": "mara"}, "ivo": {"label": "ivo"}},
        "scenes": {"meeting": {"blocks": {
            "start": {
                "content": "Mara: Ready?\nIvo: Ready.",
                "media": [
                    {"name": "theme.wav", "media_type": "AUDIO", "media_role": "music",
                     "staging_hints": {"media_timing": "loop"}},
                    {"name": "mara.wav", "media_type": "AUDIO", "media_role": "character_vox",
                     "presentation_handle": "mara", "text": "Mara: Ready?"},
                    {"name": "ivo.wav", "media_type": "AUDIO", "media_role": "character_vox",
                     "presentation_handle": "ivo", "text": "Ivo: Ready."},
                ],
                "actions": [{"text": "Continue", "successor": "meeting.next"}],
            },
            "next": {
                "content": "Mara: Let's go.",
                "media": [{"name": "mara.wav", "media_type": "AUDIO",
                           "media_role": "character_vox", "presentation_handle": "mara",
                           "text": "Mara: Let's go."}],
                "actions": [{"text": "Quiet", "successor": "meeting.quiet"}],
            },
            "quiet": {"content": "They leave in silence."},
        }}},
    }, resources=resources)
    register_manual_world(world)
    yield world
    pop_manual_world(world.label)


@pytest.fixture
def backend(monkeypatch: pytest.MonkeyPatch) -> dict[str, Mock]:
    calls = {name: Mock() for name in ("load", "play", "stop", "set_volume", "reserve")}
    calls["channel"] = Mock()
    channel = calls["channel"]
    channel.get_busy.return_value = False
    def play(sound: str) -> None:
        assert not channel.get_busy(), "voice clips overlapped"
        channel.get_busy.return_value = True
    channel.play.side_effect = play
    channel.stop.side_effect = lambda: setattr(channel.get_busy, "return_value", False)
    calls["sound"] = Mock(side_effect=lambda path: path)
    monkeypatch.setattr(pygame.mixer, "get_init", lambda: (44100, -16, 2))
    monkeypatch.setattr(pygame.mixer, "Channel", lambda index: calls["channel"])
    monkeypatch.setattr(pygame.mixer, "set_reserved", calls["reserve"])
    monkeypatch.setattr(pygame.mixer, "Sound", calls["sound"])
    for name in ("load", "play", "stop", "set_volume"):
        monkeypatch.setattr(pygame.mixer.music, name, calls[name])
    return calls


@pytest.fixture
def client(world: World) -> Iterator[PygameSessionBridge]:
    music = MusicPlayer()
    bridge = PygameSessionBridge(music_player=music, voice_player=VoicePlayer(music))
    yield bridge
    bridge.close()


def barks(envelope: RuntimeEnvelope) -> list[MediaFragment]:
    return [f for f in envelope.fragments
            if isinstance(f, MediaFragment) and f.media_role == "character_vox"]


def finish(client: PygameSessionBridge, backend: dict[str, Mock]) -> None:
    backend["channel"].get_busy.return_value = False
    assert client.voice_player.handle_event(pygame.event.Event(client.voice_player._end_event))


def test_opening_serial_order_provenance_and_no_image_drawing(
    client: PygameSessionBridge, backend: dict[str, Mock],
) -> None:
    envelope = client.start("pygame_barks_fixture")
    cues = barks(envelope)
    assert [cue.presentation_handle for cue in cues] == ["mara", "ivo"]
    assert cues[0].source_id == cues[1].source_id is not None
    assert cues[0].origin_id == cues[1].origin_id
    assert cues[0].step == cues[1].step
    assert cues[0].uid != cues[1].uid
    assert client.voice_player.current.uid == cues[0].uid
    assert backend["channel"].play.call_count == 1
    backend["reserve"].assert_called_once_with(1)
    assert backend["set_volume"].call_args.args == (0.125,)
    assert all(not turn.images for turn in client.build_turns(list(envelope.fragments)))
    finish(client, backend)
    assert client.voice_player.current.uid == cues[1].uid
    assert backend["channel"].play.call_count == 2
    assert [Path(call.args[0]).name for call in backend["sound"].call_args_list] == [
        "mara.wav", "ivo.wav",
    ]
    assert backend["set_volume"].call_args.args == (0.125,)
    finish(client, backend)
    assert client.voice_player.current is None
    assert backend["set_volume"].call_args.args == (0.5,)
    backend["load"].assert_called_once()
    backend["play"].assert_called_once_with(loops=-1)


@pytest.mark.parametrize("completed", [0, 1, 2])
def test_duplicate_delivery_active_queued_and_completed_is_silent(
    client: PygameSessionBridge, backend: dict[str, Mock], completed: int,
) -> None:
    envelope = client.start("pygame_barks_fixture")
    for _ in range(completed):
        finish(client, backend)
    count = backend["channel"].play.call_count
    current = client.voice_player.current
    client._sync(envelope, live=True)
    client.refresh()
    client.build_turns(list(envelope.fragments))
    assert backend["channel"].play.call_count == count
    assert client.voice_player.current is current


def test_advance_cancels_old_queue_and_stale_completion_cannot_interrupt_new_voice(
    client: PygameSessionBridge, backend: dict[str, Mock],
) -> None:
    envelope = client.start("pygame_barks_fixture")
    old_event = pygame.event.Event(client.voice_player._end_event)
    choice = next(f for f in envelope.fragments if isinstance(f, ChoiceFragment))
    next_envelope = client.choose(choice.edge_id)
    current = barks(next_envelope)[0]
    assert client.voice_player.current.uid == current.uid
    assert backend["channel"].play.call_count == 2
    client.voice_player.handle_event(old_event)
    assert client.voice_player.current.uid == current.uid
    assert backend["set_volume"].call_args.args == (0.125,)
    quiet = client.choose(next(f.edge_id for f in next_envelope.fragments
                               if isinstance(f, ChoiceFragment)))
    assert not barks(quiet)
    assert client.voice_player.current is None
    assert backend["set_volume"].call_args.args == (0.5,)
    client.voice_player.handle_event(old_event)
    assert backend["channel"].play.call_count == 2


def test_distinct_occurrences_same_recording_play_twice(
    client: PygameSessionBridge, backend: dict[str, Mock],
) -> None:
    cue = barks(client.start("pygame_barks_fixture"))[0]
    client.voice_player.cancel()
    second, third = cue.evolve(uid=uuid4()), cue.evolve(uid=uuid4())
    payload = media_fragment_to_payload(cue, render_profile=client.media_render_profile)
    client.voice_player.present([(second, payload), (third, payload), (third, payload)], fresh=True)
    assert client.voice_player.current.uid == second.uid
    finish(client, backend)
    assert client.voice_player.current.uid == third.uid
    finish(client, backend)
    assert client.voice_player.current is None
    assert backend["channel"].play.call_count == 3


@pytest.mark.parametrize("failure_at", [0, 1])
@pytest.mark.parametrize("failure", ["decode", "play", "missing", "pointer", "url"])
def test_failed_first_or_middle_clip_skips_without_stall(
    client: PygameSessionBridge, backend: dict[str, Mock], failure_at: int, failure: str,
) -> None:
    envelope = client.start("pygame_barks_fixture")
    client.voice_player.cancel()
    cues = [cue.evolve(uid=uuid4()) for cue in barks(envelope)]
    cues.append(cues[0].evolve(uid=uuid4()))
    profile = client.media_render_profile
    if failure in ("missing", "pointer"):
        path = cues[failure_at].content.path
        if failure == "missing":
            path.unlink()
        else:
            # A source that exists but is an LFS pointer is unavailable, not a decoder input.
            with path.open("wb") as output:
                output.write(b"version https://git-lfs.github.com/spec/v1\noid sha256:abc\nsize 12\n")
    deliveries = [(cue, media_fragment_to_payload(cue, render_profile=profile)) for cue in cues]
    if failure == "url":
        cue, payload = deliveries[failure_at]
        deliveries[failure_at] = (cue, {**payload, "content_format": "url"})
    if failure == "decode":
        count = 0
        def load(path: str) -> str:
            nonlocal count
            index, count = count, count + 1
            if index == failure_at:
                raise pygame.error("bad decoder")
            return path
        backend["sound"].side_effect = load
    if failure == "play":
        play = backend["channel"].play.side_effect
        count = 0
        def fail_play(sound: str) -> None:
            nonlocal count
            index, count = count, count + 1
            if index == failure_at:
                raise pygame.error("bad play")
            play(sound)
        backend["channel"].play.side_effect = fail_play
    client.voice_player.present(deliveries, fresh=True)
    assert client.voice_player.current is not None
    for _ in range(3):
        finish(client, backend)
    assert client.voice_player.current is None
    assert backend["set_volume"].call_args.args == (0.5,)
    assert not client.voice_player._pending
    loads = backend["sound"].call_count
    client.voice_player.present(deliveries, fresh=True)
    assert backend["sound"].call_count == loads


def test_duck_uses_current_controls_and_track_changes_never_restarts_on_unduck(
    client: PygameSessionBridge, backend: dict[str, Mock],
) -> None:
    envelope = client.start("pygame_barks_fixture")
    music = client.music_player
    music.set_volume(0.8)
    assert backend["set_volume"].call_args.args == (0.2,)
    music.toggle_mute()
    assert backend["set_volume"].call_args.args == (0.0,)
    music.set_volume(0.4)
    music.toggle_mute()
    assert backend["set_volume"].call_args.args == (0.1,)
    track = envelope.presentation.music.evolve(uid=uuid4(), rit_id=uuid4(),
                                             content_format="path",
                                             content=str(envelope.presentation.music.content.path))
    payload = media_fragment_to_payload(track, render_profile=client.media_render_profile)
    music.synchronize(PresentationSnapshot(music=track), payload)
    assert backend["set_volume"].call_args.args == (0.1,)
    music.synchronize(PresentationSnapshot(music=None), None)
    plays = backend["play"].call_count
    finish(client, backend)
    finish(client, backend)
    assert backend["play"].call_count == plays
    assert music.current is None
    assert backend["set_volume"].call_args.args == (0.4,)


def test_all_skipped_or_failed_clips_unduck_and_are_consumed(
    client: PygameSessionBridge, backend: dict[str, Mock],
) -> None:
    envelope = client.start("pygame_barks_fixture")
    cues = [cue.evolve(uid=uuid4()) for cue in barks(envelope)]
    backend["sound"].side_effect = pygame.error("unreadable clip")
    deliveries = [(cue, media_fragment_to_payload(cue, render_profile=client.media_render_profile))
                  for cue in cues]
    client.voice_player.present(deliveries, fresh=True)
    assert client.voice_player.current is None
    assert backend["set_volume"].call_args.args == (0.5,)
    count = backend["sound"].call_count
    client.voice_player.present(deliveries, fresh=True)
    assert backend["sound"].call_count == count


def test_completion_while_muted_and_device_loss_do_not_leak_ducking(
    client: PygameSessionBridge, backend: dict[str, Mock],
) -> None:
    client.start("pygame_barks_fixture")
    client.music_player.toggle_mute()
    finish(client, backend)
    finish(client, backend)
    assert backend["set_volume"].call_args.args == (0.0,)
    client.music_player.toggle_mute()
    assert backend["set_volume"].call_args.args == (0.5,)
    client.start("pygame_barks_fixture")
    backend["channel"].get_busy.side_effect = pygame.error("lost device")
    client.voice_player.handle_event(pygame.event.Event(client.voice_player._end_event))
    assert client.voice_player.current is None
    assert not client.voice_player._pending
    assert backend["set_volume"].call_args.args == (0.5,)


def test_json_service_restore_preserves_provenance_without_replaying_history(
    world: World, backend: dict[str, Mock], tmp_path: Path,
) -> None:
    root = tmp_path / "sessions"
    music = MusicPlayer()
    first = PygameSessionBridge(
        ServiceManager(PersistenceManagerFactory.json_file(base_path=root)),
        music_player=music, voice_player=VoicePlayer(music),
    )
    envelope = first.start(world.label)
    cues = barks(envelope)
    first.close()
    music = MusicPlayer()
    reopened = PygameSessionBridge(
        ServiceManager(PersistenceManagerFactory.json_file(base_path=root)),
        user_id=first.user_id, music_player=music, voice_player=VoicePlayer(music),
    )
    try:
        restored = reopened.refresh()
        history = barks(restored)
        fields = lambda cue: (cue.uid, cue.rit_id, cue.source_id, cue.origin_id, cue.step,
                              cue.presentation_handle, cue.text)
        assert list(map(fields, history)) == list(map(fields, cues))
        with reopened.service_manager.open_session(user_id=reopened.user_id) as session:
            graph = session.ledger.graph
            assert graph.get(history[0].source_id).label == "start"
            assert [graph.get(cue.rit_id).path.name for cue in history] == ["mara.wav", "ivo.wav"]
        assert reopened.voice_player.current is None
        assert backend["channel"].play.call_count == 1
        reopened.refresh()
        reopened._sync(restored, live=True)
        assert backend["channel"].play.call_count == 1
        next_envelope = reopened.choose(next(f.edge_id for f in restored.fragments
                                             if isinstance(f, ChoiceFragment)))
        assert reopened.voice_player.current.uid == barks(next_envelope)[0].uid
        assert backend["channel"].play.call_count == 2
    finally:
        reopened.close()


def test_device_failure_recovery_and_teardown(
    client: PygameSessionBridge, backend: dict[str, Mock], monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(pygame.mixer, "get_init", lambda: None)
    initialize = Mock(side_effect=pygame.error("no device"))
    monkeypatch.setattr(pygame.mixer, "init", initialize)
    envelope = client.start("pygame_barks_fixture")
    assert client.voice_player.current is None
    assert not client.voice_player._pending
    initialize.assert_called_once()
    client.refresh()
    initialize.assert_called_once()
    client.close()
    monkeypatch.setattr(pygame.mixer, "get_init", lambda: (44100, -16, 2))
    client.start("pygame_barks_fixture")
    assert client.voice_player.current is not None
    client.close()
    assert client.voice_player.current is None
    assert not client.voice_player._pending
    assert client.music_player._duck_gain == 1.0


def test_dummy_channel_completion_wakes_idle_event_loop(
    world: World, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tangl.pygame_client.__main__ import _next_events

    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    pygame.mixer.quit()
    pygame.display.init()
    pygame.display.set_mode((1, 1))
    sound = Mock(wraps=pygame.mixer.Sound)
    monkeypatch.setattr(pygame.mixer, "Sound", sound)
    music = MusicPlayer()
    client = PygameSessionBridge(music_player=music, voice_player=VoicePlayer(music))
    timeout = pygame.event.custom_type()
    try:
        envelope = client.start(world.label)
        assert client.voice_player.current.uid == barks(envelope)[0].uid
        pygame.event.clear()
        # A bounded safety event fails this test if native completion cannot wake
        # the same indefinite event wait used by a motionless stage.
        pygame.time.set_timer(timeout, 2000, loops=1)
        stage = Mock(animating=False)
        while client.voice_player.current is not None:
            for event in _next_events(stage):
                assert event.type != timeout, "voice completion did not wake the idle loop"
                client.voice_player.handle_event(event)
        assert music._duck_gain == 1.0
        assert [Path(call.args[0]).name for call in sound.call_args_list] == [
            "mara.wav", "ivo.wav",
        ]
        assert pygame.mixer.music.get_busy()
        assert pygame.mixer.music.get_volume() == pytest.approx(0.5)
        # Automatic Sound.play() must not claim even an idle voice channel.
        other = pygame.mixer.Sound(buffer=b"\0\0" * 800)
        assert other.play() is not None
        assert not pygame.mixer.Channel(0).get_busy()
    finally:
        pygame.time.set_timer(timeout, 0)
        client.close()
        pygame.quit()
