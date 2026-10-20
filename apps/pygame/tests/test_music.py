"""Desired music through real bridge/profile resolution and one client owner."""
from __future__ import annotations

from collections.abc import Iterator, Sequence
from pathlib import Path
from unittest.mock import Mock
from uuid import uuid4
import wave

import pytest

pygame = pytest.importorskip("pygame")

from tangl.journal.fragments import ChoiceFragment, ControlFragment, MediaFragment
from tangl.loaders import WorldBundle
from tangl.loaders.compiler import WorldCompiler
from tangl.media import MediaDataType
from tangl.media.media_resource import MediaInventory, MediaRITStatus
from tangl.media.media_resource import MediaResourceInventoryTag as MediaRIT
from tangl.media.media_resource.media_resource_inv_tag import is_materialized_media_file
from tangl.media.media_resource.resource_manager import ResourceManager
from tangl.presentation.targets import FragmentTarget, HandleTarget, RitTarget, RoleTarget
from tangl.persistence import PersistenceManagerFactory
from tangl.pygame_client.bridge import PygameSessionBridge
from tangl.pygame_client.music import MusicPlayer
from tangl.service.media import MediaContentProfile, MediaRenderProfile
from tangl.service import ServiceManager
from tangl.service.response import PresentationSnapshot, RuntimeEnvelope
from tangl.service.world_registry import register_manual_world, pop_manual_world
from tangl.story import World


def write_wav(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(8000)
        output.writeframes(b"\0\0" * 800)


@pytest.fixture
def backend(monkeypatch: pytest.MonkeyPatch) -> dict[str, Mock]:
    calls = {name: Mock() for name in ("load", "play", "stop", "set_volume")}
    monkeypatch.setattr(pygame.mixer, "get_init", lambda: (44100, -16, 2))
    for name, mock in calls.items():
        monkeypatch.setattr(pygame.mixer.music, name, mock)
    return calls


@pytest.fixture
def bridge(tmp_path: Path) -> Iterator[PygameSessionBridge]:
    write_wav(tmp_path / "music" / "theme.wav")
    resources = ResourceManager(tmp_path)
    resources.index_directory(".")
    world = World.from_script_data(script_data={
        "label": "pygame_music_fixture",
        "scenes": {
            "first": {"blocks": {"start": {
                "content": "A playable opening.",
                "media": [{"name": "music/theme.wav", "media_type": "AUDIO",
                           "media_role": "music", "presentation_handle": "theme",
                           "staging_hints": {"media_timing": "loop"}}],
                "actions": [{"text": "Continue", "successor": "second.start"}],
            }}},
            "second": {"blocks": {"start": {"content": "An adjacent scene."}}},
        },
    }, resources=resources)
    register_manual_world(world)
    client = PygameSessionBridge(music_player=MusicPlayer())
    yield client
    client.close()
    pop_manual_world(world.label)


def selected(bridge: PygameSessionBridge) -> MediaFragment:
    envelope = bridge.start("pygame_music_fixture")
    assert isinstance(envelope.presentation.music, MediaFragment)
    return envelope.presentation.music


def deliver(
    bridge: PygameSessionBridge, music: MediaFragment | None,
    controls: Sequence[ControlFragment] = (), *, live: bool = True, snapshot: bool = True,
) -> None:
    bridge._sync(RuntimeEnvelope(
        fragments=list(controls), metadata={"ledger_id": bridge.ledger_id},
        presentation=PresentationSnapshot(music=music) if snapshot else None,
    ), live=live)


def other_track(path: Path, *, timing: str = "start") -> MediaFragment:
    write_wav(path)
    return MediaFragment(content=MediaRIT(path=path), content_format="rit",
                         content_type=MediaDataType.AUDIO, media_role="music",
                         staging_hints={"media_timing": timing})


def test_real_bridge_cue_continues_across_scene_get_and_redraw(
    bridge: PygameSessionBridge, backend: dict[str, Mock],
) -> None:
    envelope = bridge.start("pygame_music_fixture")
    cue = envelope.presentation.music
    assert cue.content.path.name == "theme.wav"
    assert backend["load"].call_args.args == (str(cue.content.path),)
    backend["play"].assert_called_once_with(loops=-1)
    turns = bridge.build_turns(list(envelope.fragments))
    assert all(not turn.images for turn in turns)
    choice = next(f for f in envelope.fragments if isinstance(f, ChoiceFragment))
    advanced = bridge.choose(choice.edge_id)
    assert advanced.presentation.music.rit_id == cue.rit_id
    bridge.refresh()
    bridge.build_turns(list(envelope.fragments))
    assert backend["load"].call_count == backend["play"].call_count == 1


def test_identity_not_path_decides_continuity_and_different_resource_replaces(
    bridge: PygameSessionBridge, backend: dict[str, Mock], tmp_path: Path,
) -> None:
    cue = selected(bridge)
    deliver(bridge, cue.evolve(uid=uuid4()))
    assert backend["play"].call_count == 1
    second = other_track(tmp_path / "second.wav")
    deliver(bridge, second)
    assert backend["load"].call_count == 2
    backend["play"].assert_called_with(loops=0)
    # Distinct admitted identity, even when a locator happens to be identical.
    deliver(bridge, second.evolve(rit_id=uuid4(), content=str(tmp_path / "second.wav"),
                                 content_format="path"))
    assert backend["load"].call_count == 3


def test_continuity_uses_the_resolved_fallback_rit_not_the_original_identity(
    bridge: PygameSessionBridge, backend: dict[str, Mock], tmp_path: Path,
) -> None:
    cue = selected(bridge)
    write_wav(tmp_path / "fallback.wav")
    resources = ResourceManager(tmp_path)
    fallback = resources.register_file(tmp_path / "fallback.wav")
    bridge.media_render_profile = MediaRenderProfile(
        content_profile=MediaContentProfile.PASSTHROUGH,
        static_inventories=(MediaInventory(resources.registry),),
    )
    cue.content.status = MediaRITStatus.PENDING
    cue.content.derivation_spec = {"fallback_ref": "fallback.wav"}
    deliver(bridge, cue)
    assert bridge.music_player._playing_rit == fallback.uid != cue.rit_id
    assert backend["load"].call_count == 2
    deliver(bridge, cue)
    assert backend["load"].call_count == 2
    cue.content.status = MediaRITStatus.RESOLVED
    deliver(bridge, cue)
    assert bridge.music_player._playing_rit == cue.rit_id
    assert backend["load"].call_count == 3


@pytest.mark.parametrize("target_kind", ["fragment", "rit", "role", "handle"])
def test_restart_once_per_control_uid_and_target_matching(
    bridge: PygameSessionBridge, backend: dict[str, Mock], target_kind: str,
) -> None:
    cue = selected(bridge)
    target = {
        "fragment": FragmentTarget(fragment_id=cue.uid), "rit": RitTarget(rit_id=cue.rit_id),
        "role": RoleTarget(media_role="music"), "handle": HandleTarget(handle="theme"),
    }[target_kind]
    restart = ControlFragment(target=target, media_action="restart", media=cue)
    deliver(bridge, cue, [restart])
    deliver(bridge, cue, [restart])
    assert backend["play"].call_count == 2 and backend["load"].call_count == 1
    absent = ControlFragment(target=RoleTarget(media_role="ambience"),
                             media_action="restart", media=cue)
    deliver(bridge, cue, [absent])
    assert backend["play"].call_count == 2


def test_absence_retains_but_null_and_descriptor_free_stop_clear(
    bridge: PygameSessionBridge, backend: dict[str, Mock],
) -> None:
    cue = selected(bridge)
    deliver(bridge, None, snapshot=False)
    assert bridge.music_player.current.rit_id == cue.rit_id and backend["play"].call_count == 1
    stop = ControlFragment(fragment_type="delete", target=RoleTarget(media_role="music"))
    deliver(bridge, None, [stop], snapshot=False)
    assert bridge.music_player.current is None
    deliver(bridge, cue)
    deliver(bridge, None)
    assert bridge.music_player.current is None
    assert bridge.music_player._playing_rit is None


def test_final_snapshot_wins_over_stale_stop_restart_and_historical_tracks(
    bridge: PygameSessionBridge, backend: dict[str, Mock], tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cue = selected(bridge)
    second = other_track(tmp_path / "second.wav")
    stop = ControlFragment(fragment_type="delete", target=RoleTarget(media_role="music"))
    restart = ControlFragment(target=RoleTarget(media_role="music"),
                             media_action="restart", media=cue)
    history = RuntimeEnvelope(metadata={"ledger_id": bridge.ledger_id},
                              fragments=[cue, restart, stop, second],
                              presentation=PresentationSnapshot(music=second))
    monkeypatch.setattr(bridge.service_manager, "get_story_update", lambda **_kw: history)
    bridge.refresh()
    assert backend["load"].call_count == backend["play"].call_count == 2
    # Redelivery of historical controls through a live response is still silent.
    monkeypatch.setattr(bridge.service_manager, "resolve_choice", lambda **_kw: history)
    bridge.choose(uuid4())
    assert backend["play"].call_count == 2
    fresh_stale = ControlFragment(target=restart.target, media_action="restart", media=cue)
    deliver(bridge, second, [stop.evolve(uid=uuid4()), fresh_stale])
    assert bridge.music_player.current.rit_id == second.rit_id
    assert backend["play"].call_count == 2


def test_local_mute_volume_survive_changes_and_story_switch_teardown_stops(
    bridge: PygameSessionBridge, backend: dict[str, Mock], tmp_path: Path,
) -> None:
    selected(bridge)
    bridge.music_player.set_volume(0.3)
    bridge.music_player.toggle_mute()
    deliver(bridge, other_track(tmp_path / "second.wav"))
    backend["set_volume"].assert_called_with(0.0)
    bridge.start("pygame_music_fixture")
    assert bridge.music_player.muted and bridge.music_player.volume == 0.3
    bridge.music_player.toggle_mute()
    backend["set_volume"].assert_called_with(0.3)
    before = backend["stop"].call_count
    bridge.close()
    assert backend["stop"].call_count == before + 1
    assert bridge.music_player.current is None


@pytest.mark.parametrize("failure", ["device", "decode", "missing"])
def test_audio_failure_keeps_real_choices_playable(
    bridge: PygameSessionBridge, backend: dict[str, Mock], failure: str,
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture,
) -> None:
    if failure == "device":
        monkeypatch.setattr(pygame.mixer, "get_init", lambda: None)
        monkeypatch.setattr(pygame.mixer, "init", Mock(side_effect=pygame.error("no device")))
    else:
        backend["load"].side_effect = (pygame.error("bad codec") if failure == "decode"
                                        else FileNotFoundError("missing"))
    envelope = bridge.start("pygame_music_fixture")
    assert bridge.music_player.error and "Music unavailable" in caplog.text
    choice = next(f for f in envelope.fragments if isinstance(f, ChoiceFragment))
    assert any(turn.choices for turn in bridge.build_turns(list(envelope.fragments)))
    assert bridge.choose(choice.edge_id).fragments


@pytest.mark.parametrize("boundary", ["new_story", "empty", "delete"])
@pytest.mark.parametrize("recovers", [False, True])
def test_device_failure_retries_at_session_or_empty_slot_boundaries(
    bridge: PygameSessionBridge, backend: dict[str, Mock], monkeypatch: pytest.MonkeyPatch,
    boundary: str, recovers: bool,
) -> None:
    initialized = False
    attempts = Mock(side_effect=[
        pygame.error("no device"), None if recovers else pygame.error("still no device"),
    ])

    def initialize() -> None:
        nonlocal initialized
        attempts()
        initialized = True

    monkeypatch.setattr(pygame.mixer, "get_init", lambda: (44100, -16, 2) if initialized else None)
    monkeypatch.setattr(pygame.mixer, "init", initialize)
    player = bridge.music_player
    player.set_volume(0.3)
    player.toggle_mute()
    cue = selected(bridge)
    assert player.status == "unavailable" and player.error
    for _ in range(2):
        deliver(bridge, cue)
        assert player.status == "unavailable"
    assert attempts.call_count == 1
    backend["load"].assert_not_called()

    if boundary == "new_story":
        bridge.close()
        bridge.start("pygame_music_fixture")
    else:
        if boundary == "empty":
            deliver(bridge, None)
        else:
            deliver(bridge, None, [ControlFragment(
                fragment_type="delete", target=RoleTarget(media_role="music"),
            )], snapshot=False)
        assert player.current is None
        deliver(bridge, cue)

    assert attempts.call_count == 2
    assert player.volume == 0.3 and player.muted
    if recovers:
        assert player.error is None and player.status == "muted"
        backend["load"].assert_called_once()
        backend["play"].assert_called_once_with(loops=-1)
        backend["set_volume"].assert_called_with(0.0)
        player.toggle_mute()
        backend["set_volume"].assert_called_with(0.3)
        assert player.status == "30%"
    else:
        assert player.error and player.status == "unavailable"
        backend["load"].assert_not_called()
        backend["play"].assert_not_called()
    deliver(bridge, player.current)
    assert attempts.call_count == 2  # No timer or repeated snapshot retry.


def test_device_initialized_elsewhere_is_used_despite_an_earlier_failure(
    bridge: PygameSessionBridge, backend: dict[str, Mock], monkeypatch: pytest.MonkeyPatch,
) -> None:
    initialized = False
    attempts = Mock(side_effect=pygame.error("no device"))
    monkeypatch.setattr(pygame.mixer, "get_init", lambda: (44100, -16, 2) if initialized else None)
    monkeypatch.setattr(pygame.mixer, "init", attempts)
    cue = selected(bridge)
    assert attempts.call_count == 1 and bridge.music_player.status == "unavailable"
    initialized = True
    deliver(bridge, cue)
    assert attempts.call_count == 1
    backend["load"].assert_called_once()
    backend["play"].assert_called_once_with(loops=-1)
    assert bridge.music_player.error is None and bridge.music_player.status == "50%"


def test_mixer_loss_after_load_does_not_claim_playback_and_same_rit_recovers(
    bridge: PygameSessionBridge, backend: dict[str, Mock], monkeypatch: pytest.MonkeyPatch,
) -> None:
    initialized = True
    monkeypatch.setattr(pygame.mixer, "get_init", lambda: (44100, -16, 2) if initialized else None)
    initialize = Mock()
    monkeypatch.setattr(pygame.mixer, "init", initialize)

    def lose_device(path: str) -> None:
        nonlocal initialized
        initialized = False

    backend["load"].side_effect = lose_device
    cue = selected(bridge)
    player = bridge.music_player
    backend["play"].assert_not_called()
    assert player._playing_rit is None
    assert player.error is not None and player.status == "unavailable"

    initialized = True  # Another consumer reinitializes the mixer.
    backend["load"].side_effect = None
    player.set_volume(0.6)
    player.set_ducked(True)
    deliver(bridge, cue)
    assert backend["load"].call_count == 2
    backend["play"].assert_called_once_with(loops=-1)
    backend["set_volume"].assert_called_with(0.15)
    assert player._playing_rit == cue.rit_id
    assert player.error is None and player.status == "60%"
    initialize.assert_not_called()
    deliver(bridge, cue)
    assert backend["play"].call_count == 1


def test_mixer_loss_during_live_restart_clears_identity_without_replaying_control(
    bridge: PygameSessionBridge, backend: dict[str, Mock], monkeypatch: pytest.MonkeyPatch,
) -> None:
    initialized = True
    monkeypatch.setattr(pygame.mixer, "get_init", lambda: (44100, -16, 2) if initialized else None)
    cue = selected(bridge)
    restart = ControlFragment(target=RoleTarget(media_role="music"),
                              media_action="restart", media=cue)
    initialized = False
    deliver(bridge, cue, [restart])
    player = bridge.music_player
    assert player._playing_rit is None
    assert player.error is not None and player.status == "unavailable"
    assert backend["play"].call_count == 1

    initialized = True
    deliver(bridge, cue, [restart])
    assert backend["load"].call_count == 2
    assert backend["play"].call_count == 2
    assert player._playing_rit == cue.rit_id
    assert player.error is None and player.status == "50%"
    deliver(bridge, cue, [restart])
    assert backend["play"].call_count == 2


def test_idle_gain_updates_without_device_are_harmless(
    backend: dict[str, Mock], monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(pygame.mixer, "get_init", lambda: None)
    initialize = Mock()
    monkeypatch.setattr(pygame.mixer, "init", initialize)
    player = MusicPlayer()
    player.set_volume(0.6)
    player.set_ducked(True)
    player.toggle_mute()
    player.set_ducked(False)
    player.toggle_mute()
    assert player.error is None and player.status == "60%"
    assert player._playing_rit is None
    initialize.assert_not_called()
    backend["set_volume"].assert_not_called()
    backend["play"].assert_not_called()


@pytest.mark.parametrize("profile", [MediaContentProfile.MEDIA_SERVER, MediaContentProfile.INLINE_DATA])
def test_unsupported_transport_is_not_guessed_into_local_path(
    bridge: PygameSessionBridge, backend: dict[str, Mock], profile: MediaContentProfile,
) -> None:
    cue = selected(bridge)
    bridge.media_render_profile = MediaRenderProfile(content_profile=profile)
    deliver(bridge, cue)
    assert bridge.music_player._playing_rit is None
    assert bridge.music_player.error
    assert backend["load"].call_count == 1


def test_disappearing_optional_source_stops_stale_music_without_blocking_choices(
    bridge: PygameSessionBridge, backend: dict[str, Mock], caplog: pytest.LogCaptureFixture,
) -> None:
    cue = selected(bridge)
    cue.content.path.unlink()  # Generated temporary WAV, never a shipped asset.
    envelope = bridge.refresh()
    assert bridge.music_player._playing_rit is None
    assert bridge.music_player.error and "Music unavailable" in caplog.text
    assert backend["load"].call_count == 1
    assert any(turn.choices for turn in bridge.build_turns(list(envelope.fragments)))


def test_unadmitted_optional_music_is_logged_without_image_loading_or_lost_choices(
    bridge: PygameSessionBridge, backend: dict[str, Mock], caplog: pytest.LogCaptureFixture,
) -> None:
    unresolved = MediaFragment(content="unresolved optional cue", content_format="json",
                               content_type=MediaDataType.AUDIO, media_role="music")
    turn = bridge.build_turns([unresolved, ChoiceFragment(text="Continue", edge_id=uuid4())])[0]
    assert "Music cue unavailable: no admitted resource" in caplog.text
    assert turn.choices and not turn.images
    backend["load"].assert_not_called()


def test_create_and_reconnect_never_execute_historical_restarts(
    bridge: PygameSessionBridge, backend: dict[str, Mock], monkeypatch: pytest.MonkeyPatch,
) -> None:
    cue = selected(bridge)
    restart = ControlFragment(target=RoleTarget(media_role="music"),
                             media_action="restart", media=cue)
    envelope = RuntimeEnvelope(metadata={"ledger_id": uuid4()}, fragments=[cue, restart],
                               presentation=PresentationSnapshot(music=cue))
    monkeypatch.setattr(bridge.service_manager, "create_story", lambda **_kw: envelope)
    bridge.start("pygame_music_fixture")
    assert backend["play"].call_count == 2  # A new story starts the final track once.
    deliver(bridge, cue, [restart])
    assert backend["play"].call_count == 2
    monkeypatch.setattr(bridge.service_manager, "get_story_update", lambda **_kw: envelope)
    restored = PygameSessionBridge(bridge.service_manager, user_id=bridge.user_id,
                                   music_player=MusicPlayer())
    restored.refresh()
    assert backend["play"].call_count == 3
    restored.refresh()
    assert backend["play"].call_count == 3
    restored.close()


def test_music_shortcuts_are_local_and_do_not_steal_choice_keys(
    backend: dict[str, Mock],
) -> None:
    from tangl.pygame_client.__main__ import _music_key

    player = MusicPlayer(volume=0.5)
    def key(code: int, mod: int) -> pygame.event.Event:
        return pygame.event.Event(pygame.KEYDOWN, key=code, mod=mod)
    assert not _music_key(key(pygame.K_m, 0), player)
    assert not _music_key(key(pygame.K_F1, 0), player)
    assert _music_key(key(pygame.K_m, pygame.KMOD_CTRL), player) and player.muted
    assert _music_key(key(pygame.K_LEFTBRACKET, pygame.KMOD_CTRL), player)
    assert player.volume == pytest.approx(0.4)
    backend["set_volume"].assert_called_with(0.0)
    assert _music_key(key(pygame.K_m, pygame.KMOD_CTRL), player) and not player.muted
    backend["set_volume"].assert_called_with(pytest.approx(0.4))


def test_application_teardown_stops_music_even_on_screenshot(
    tmp_path: Path, backend: dict[str, Mock], monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tangl.pygame_client import __main__ as client

    closed = Mock(wraps=MusicPlayer.close)
    def close(player: MusicPlayer) -> None:
        closed(player)
    monkeypatch.setattr(MusicPlayer, "close", close)
    assert client.main(["--world", "repartee_loop", "--mute", "--volume", "0.2",
                        "--screenshot", str(tmp_path / "frame.png")]) == 0
    assert closed.call_count >= 2  # Initial session boundary plus final teardown.
    assert closed.call_args.args[0].current is None
    assert closed.call_args.args[0].muted and closed.call_args.args[0].volume == 0.2


@pytest.mark.parametrize("pack", ["media", "media_spaceport"])
def test_optional_marmoset_theme_real_world_profile_and_dummy_mixer(
    pack: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = Path(__file__).resolve().parents[3] / "worlds" / "repartee_loop"
    theme = root / pack / "music" / "theme.mp3"
    if not is_materialized_media_file(theme):
        pytest.skip(f"Optional {pack}/music/theme.mp3 absent or unmaterialized Git LFS pointer")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    pygame.mixer.quit()
    load = Mock(wraps=pygame.mixer.music.load)
    play = Mock(wraps=pygame.mixer.music.play)
    monkeypatch.setattr(pygame.mixer.music, "load", load)
    monkeypatch.setattr(pygame.mixer.music, "play", play)
    bundle = WorldBundle.load(root)
    bundle.manifest.media_dir = pack
    world = WorldCompiler().compile(bundle)
    register_manual_world(world)
    player = MusicPlayer()
    bridge = PygameSessionBridge(music_player=player)
    try:
        envelope = bridge.start("repartee_loop")
        cue = envelope.presentation.music
        assert isinstance(cue, MediaFragment) and cue.content_type is MediaDataType.AUDIO
        assert cue.content.path == theme and cue.staging_hints.media_timing == "loop"
        assert player.error is None and player._playing_rit == cue.rit_id
        assert pygame.mixer.music.get_busy()
        for text in (
            "Step into the practice court", "Step out onto the quay", "Go to The Practice Yard",
            "Challenge the dockhand",
        ):
            turns = bridge.build_turns(list(envelope.fragments))
            assert all(image.role != "music" for turn in turns for image in turn.images)
            choice = next(c for turn in turns for c in turn.choices if c.text == text and c.available)
            envelope = bridge.choose(choice.edge_id, choice.payload)
            assert envelope.presentation.music.rit_id == cue.rit_id
            assert player._playing_rit == cue.rit_id and player.error is None
        turns = bridge.build_turns(list(envelope.fragments))
        move = next(c for turn in turns for c in turn.choices if c.available)
        envelope = bridge.choose(move.edge_id, move.payload)
        assert envelope.presentation.music.rit_id == cue.rit_id and player.error is None
        assert bridge.map_plate() is None  # We have left the map for an ordinary location.
        bridge.refresh()
        load.assert_called_once_with(str(theme))
        play.assert_called_once_with(loops=-1)
    finally:
        bridge.close()
        pygame.mixer.quit()
        pop_manual_world(world.label)


def test_generated_wav_uses_real_dummy_mixer(
    bridge: PygameSessionBridge, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    pygame.mixer.quit()
    try:
        cue = selected(bridge)
        assert bridge.music_player.error is None
        assert bridge.music_player._playing_rit == cue.rit_id
        assert pygame.mixer.music.get_busy()
    finally:
        bridge.close()
        pygame.mixer.quit()


def test_malformed_materialized_wav_is_reported_as_decode_failure_not_success(
    bridge: PygameSessionBridge, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    pygame.mixer.quit()
    selected(bridge)
    path = tmp_path / "malformed.wav"
    path.write_bytes(b"materialized but not a WAV recording")
    invalid = MediaFragment(content=MediaRIT(path=path), content_format="rit",
                            content_type=MediaDataType.AUDIO, media_role="music")
    try:
        deliver(bridge, invalid)
        assert bridge.music_player.error is not None
        assert bridge.music_player._playing_rit is None
        assert not pygame.mixer.music.get_busy()
    finally:
        bridge.close()
        pygame.mixer.quit()


def test_json_service_reopen_plays_current_music_without_historical_restart(
    bridge: PygameSessionBridge, backend: dict[str, Mock], tmp_path: Path,
) -> None:
    root = tmp_path / "sessions"
    first = PygameSessionBridge(
        ServiceManager(PersistenceManagerFactory.json_file(base_path=root)),
        music_player=MusicPlayer(),
    )
    envelope = first.start("pygame_music_fixture")
    cue = envelope.presentation.music
    with first.service_manager.open_session(user_id=first.user_id, write_back=True) as session:
        session.ledger.output_stream.add(ControlFragment(
            target=RoleTarget(media_role="music"), media_action="restart", media=cue,
        ))
    first.refresh()
    assert backend["play"].call_count == 1
    first.close()
    reopened = PygameSessionBridge(
        ServiceManager(PersistenceManagerFactory.json_file(base_path=root)),
        user_id=first.user_id, music_player=MusicPlayer(),
    )
    try:
        restored = reopened.refresh()
        assert restored.presentation.music.rit_id == cue.rit_id
        assert reopened.music_player._playing_rit == cue.rit_id
        assert backend["load"].call_count == backend["play"].call_count == 2
        reopened.refresh()
        assert backend["play"].call_count == 2
    finally:
        reopened.close()
