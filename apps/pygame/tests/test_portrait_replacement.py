"""Speaker identity survives journal, delivery, restoration and in-place staging."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from uuid import uuid4

import pytest

pygame = pytest.importorskip("pygame")

from tangl.core import Selector
from tangl.journal.fragments import MediaFragment, fragment_from_dto, fragment_to_dto
from tangl.media.media_resource.resource_manager import ResourceManager
from tangl.persistence import PersistenceManagerFactory
from tangl.persistence.serializers import JsonSerializationHandler as Json
from tangl.prose import DialogMuBlock
from tangl.prose.naming import NamedActor, ProseBlock, naming_dispatch
from tangl.prose.portraits import HasPortraits, portrait_dispatch
from tangl.pygame_client.__main__ import _frame, _merge
from tangl.pygame_client.bridge import PygameSessionBridge
from tangl.pygame_client.models import StageImage, Turn
from tangl.pygame_client.stage import Stage
from tangl.service import ServiceManager
from tangl.service.media import MediaContentProfile, MediaRenderProfile, media_fragment_to_payload
from tangl.service.response import RuntimeEnvelope
from tangl.service.user.user import User
from tangl.story import Actor, Role, World
from tangl.story.fabula.builder import WorldBuilder
from tangl.story.fabula.compiler import StoryCompiler
from tangl.vm import Ledger, Requirement, ResolutionPhase
from tangl.vm.dispatch import do_journal, do_update
from tangl.vm.runtime.frame import PhaseCtx


class PortraitSpeaker(HasPortraits, NamedActor):
    pass


@pytest.fixture
def portrait_world(tmp_path: Path) -> World:
    for name, colour in (("base", "red"), ("happy", "blue"), ("dry", "green")):
        surface = pygame.Surface((20, 20))
        surface.fill(colour)
        surface.fill("yellow", (0, 0, 10, 20))
        pygame.image.save(surface, str(tmp_path / f"{name}.png"))
    resources = ResourceManager(tmp_path)
    resources.index_directory(".")
    portraits = {
        "default_look": "day", "attitudes": {"amused": "happy", "dry": "dry"},
        "looks": {"day": {"base": "base.png", "expressions": {
            "happy": "happy.png", "dry": "dry.png",
        }}},
    }
    classes = {"PortraitSpeaker": PortraitSpeaker, "ProseBlock": ProseBlock}
    bundle = StoryCompiler().compile({
        "label": "portrait_stage", "metadata": {"start_at": "s.start"},
        "actors": {name: {"kind": "PortraitSpeaker", "name": name, "portraits": portraits}
                   for name in ("rin", "kai")},
        "scenes": {"s": {"roles": {"host": {"actor_ref": "rin"},
                                   "guest": {"actor_ref": "kai"}}, "blocks": {
            "start": {"kind": "ProseBlock", "prose": [
                {"dialog_class": "host.amused", "text": "Hello."},
                {"dialog_class": "host.dry", "text": "Really?"},
            ], "media": [{"name": "base.png", "media_role": "avatar_im", "speaker": "host",
                          "staging_hints": {"media_x": 0.25, "media_y": 0.8,
                                            "media_flip_h": True,
                                            "media_visibility": {"preference_id": "portraits",
                                                                 "values": [True]},
                                            "media_clip_binding": {"axes": ["motion"], "rows": [
                                                {"values": [True], "clip": "idle"},
                                            ]}}}]},
        }}},
    }, class_registry=classes)
    return WorldBuilder().build(
        label="portrait_stage", bundle=bundle, resources=resources, class_registry=classes,
        extra_authorities=[naming_dispatch, portrait_dispatch],
    )


def delivered_frame(envelope: RuntimeEnvelope, world: World) -> Turn:
    # Use the same JSON DTO and ordinary path payload consumed by the bridge.
    profile = MediaRenderProfile(content_profile=MediaContentProfile.PASSTHROUGH)
    payloads = [media_fragment_to_payload(item, render_profile=profile, world_id=world.label)
                if isinstance(item, MediaFragment) else fragment_to_dto(item)
                for item in envelope.fragments]
    fragments = [fragment_from_dto(item) for item in Json.deserialize(Json.serialize(payloads))]
    bridge = PygameSessionBridge(media_render_profile=profile)
    bridge.world_id = world.label
    return _merge(bridge.build_turns(fragments))


def test_service_portraits_replace_in_place_and_survive_json(
    portrait_world: World, tmp_path: Path,
) -> None:
    world = portrait_world
    persistence = PersistenceManagerFactory.json_file(base_path=tmp_path / "sessions")
    manager = ServiceManager(persistence)
    user = User(label="reader")
    persistence.save(user)
    envelope = manager.create_story(user_id=user.uid, world_id=world.label, world=world)
    media = [item for item in envelope.fragments if isinstance(item, MediaFragment)]
    assert len(media) == 3 and len({item.speaker_id for item in media}) == 1
    assert all(item.speaker_id != item.source_id for item in media)
    for fragment in media:
        payload = media_fragment_to_payload(fragment, world_id=world.label)
        assert payload["speaker_id"] == str(fragment.speaker_id)
        assert payload["rit_id"] == str(fragment.rit_id)
        assert payload["content_format"] == "url"
    frame = delivered_frame(envelope, world)
    assert len(frame.images) == 1
    image = frame.images[0]
    assert Path(image.source).name == "dry.png"
    assert image.role == "dialog_im"
    assert (image.x_frac, image.y_frac, image.flip_h) == (0.25, 0.8, True)
    assert image.visibility.preference_id == "portraits"
    assert image.clip_binding.axes == ["motion"]
    expression = media[-1]
    assert expression.staging_hints is None
    override = expression.evolve(staging_hints={"media_x": "right", "media_flip_h": False})
    changed = delivered_frame(RuntimeEnvelope(fragments=[*envelope.fragments, override]), world)
    assert (changed.images[0].x_slot, changed.images[0].x_frac, changed.images[0].flip_h) == (
        "right", None, False,
    )
    assert changed.images[0].y_frac == image.y_frac
    assert changed.images[0].visibility == image.visibility

    stage = Stage()
    try:
        stage.surface.fill("black")
        stage._draw_portraits(frame, {"portraits": True, "motion": False}, fresh=True)
        assert tuple(stage.surface.get_at((72, 145)))[:3] == (0, 255, 0)
        assert tuple(stage.surface.get_at((82, 145)))[:3] == (255, 255, 0)
        stage.surface.fill("black")
        stage._draw_portraits(frame, {"portraits": False, "motion": False}, fresh=False)
        assert tuple(stage.surface.get_at((72, 145)))[:3] == (0, 0, 0)
    finally:
        pygame.quit()

    with manager.open_session(user_id=user.uid) as session:
        original = session.ledger
        forms = [original.unstructure(), Json.deserialize(Json.serialize(original.unstructure()))]
        for data in forms:
            restored = Ledger.structure(data)
            assert [fragment_to_dto(item) for item in restored.get_journal()] == [
                fragment_to_dto(item) for item in original.get_journal()
            ]
            restored_envelope = RuntimeEnvelope(fragments=list(restored.get_journal()))
            assert delivered_frame(restored_envelope, world).images == frame.images
    reopened = ServiceManager(PersistenceManagerFactory.json_file(base_path=tmp_path / "sessions"))
    assert delivered_frame(
        reopened.get_story_update(user_id=user.uid), world,
    ).images == frame.images


def test_two_scoped_speakers_trade_lines_without_using_a_third_slot(portrait_world: World) -> None:
    world = portrait_world
    graph = world.create_story("portrait_stage").graph
    ledger = Ledger.from_graph(graph=graph, entry_id=graph.initial_cursor_id)
    base = ledger.cursor.media[0]
    ledger.cursor.media.append({**base, "speaker": "guest", "staging_hints": {"media_x": "right"}})
    ledger.cursor.prose.insert(1, DialogMuBlock(dialog_class="guest.amused", text="Hello back."))
    ledger.get_frame().goto_node(ledger.cursor)
    frame = delivered_frame(RuntimeEnvelope(fragments=list(ledger.get_journal())), world)
    assert len(frame.images) == 2
    assert [Path(image.source).name for image in frame.images] == ["dry.png", "happy.png"]
    assert frame.images[0].speaker_id != frame.images[1].speaker_id
    assert frame.images[0].x_frac == 0.25 and frame.images[1].x_slot == "right"


def test_scoped_base_binding_tracks_recast_and_rejects_display_names(portrait_world: World) -> None:
    world = portrait_world
    graph = world.create_story("portrait_stage").graph
    ledger = Ledger.from_graph(graph=graph, entry_id=graph.initial_cursor_id)
    ctx = PhaseCtx(graph=graph, cursor_id=ledger.cursor_id, current_phase=ResolutionPhase.UPDATE)
    role: Role = ctx.get_ns(ledger.cursor)["host_role"]
    replacement = graph.find_one(Selector(has_kind=PortraitSpeaker, label="kai"))
    role.requirement = Requirement(has_kind=Actor)
    role.set_provider(replacement)
    ctx = PhaseCtx(graph=graph, cursor_id=ledger.cursor_id, current_phase=ResolutionPhase.UPDATE)
    do_update(ledger.cursor, ctx=ctx)
    fragments = do_journal(ledger.cursor, ctx=ctx.derive(current_phase=ResolutionPhase.JOURNAL))
    assert {item.speaker_id for item in fragments
            if isinstance(item, MediaFragment)} == {replacement.uid}
    ledger.cursor.media[0]["speaker"] = "Kai is a display name, not a binding"
    with pytest.raises(ValueError, match="unbound media speaker"):
        do_journal(ledger.cursor, ctx=ctx.derive(current_phase=ResolutionPhase.JOURNAL))


def test_missing_packed_art_keeps_explicit_base(portrait_world: World) -> None:
    world = portrait_world
    graph = world.create_story("portrait_stage").graph
    ledger = Ledger.from_graph(graph=graph, entry_id=graph.initial_cursor_id)
    for subject in graph.find_all(Selector(has_kind=PortraitSpeaker)):
        subject.portraits.default_look = None
    ledger.get_frame().goto_node(ledger.cursor)
    frame = delivered_frame(RuntimeEnvelope(fragments=list(ledger.get_journal())), world)
    assert len(frame.images) == 1 and Path(frame.images[0].source).name == "base.png"


def test_unstaged_speaker_uses_normal_default_placement(portrait_world: World) -> None:
    world = portrait_world
    graph = world.create_story("portrait_stage").graph
    ledger = Ledger.from_graph(graph=graph, entry_id=graph.initial_cursor_id)
    ledger.cursor.media.clear()
    ledger.get_frame().goto_node(ledger.cursor)
    frame = delivered_frame(RuntimeEnvelope(fragments=list(ledger.get_journal())), world)
    assert len(frame.images) == 1
    assert frame.images[0].x_slot is None and frame.images[0].x_frac is None
    stage = Stage()
    try:
        stage.surface.fill("black")
        stage._draw_portraits(frame, {}, fresh=True)
        point = (stage.margin + 1, stage.logical_size[1] - 10)
        assert tuple(stage.surface.get_at(point))[:3] == (255, 255, 0)
    finally:
        pygame.quit()


def test_next_response_without_art_keeps_associated_portrait() -> None:
    image = StageImage(role="avatar_im", source="base", speaker_id=uuid4(), x_frac=0.25)
    bridge = PygameSessionBridge()
    frame = _frame(bridge, RuntimeEnvelope(fragments=[]), previous=Turn(step=1, images=[image]))
    assert frame.images == [image]


def test_two_speakers_handles_defaults_and_explicit_false() -> None:
    left, right = uuid4(), uuid4()
    base = StageImage(role="avatar_im", source="base", speaker_id=left,
                      x_slot="left", flip_h=True)
    other = StageImage(role="avatar_im", source="other", speaker_id=right, x_slot="right")
    variant = StageImage(role="dialog_im", source="happy", speaker_id=left)
    final = replace(variant, source="dry", x_frac=0.4, flip_h=False)
    separate = replace(base, source="deliberate", presentation_handle="mirror")
    frame = _merge([Turn(step=1, images=[base, other, separate, variant,
                                replace(variant, source="other-happy", speaker_id=right), final])])
    assert [image.source for image in frame.images] == ["dry", "other-happy", "deliberate"]
    assert (frame.images[0].x_slot, frame.images[0].x_frac, frame.images[0].flip_h) == (
        None, 0.4, False,
    )
    assert frame.images[1].x_slot == "right"
    assert len(_merge([Turn(step=1, images=[variant, replace(variant, source="dry")])]).images) == 1
    decorations = [StageImage(role="avatar_im", source="decoration", x_slot=slot)
                   for slot in ("left", "right")]
    assert _merge([Turn(step=1, images=decorations)]).images == decorations
