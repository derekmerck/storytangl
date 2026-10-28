"""Packed look nomination, pre-JOURNAL admission and ordinary media delivery."""

from __future__ import annotations

from collections.abc import Iterator
import json
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from tangl.core import EntityTemplate, Selector
from tangl.journal.fragments import AttributedFragment, MediaFragment
from tangl.loaders import WorldBundle, WorldCompiler
from tangl.media.media_resource import MediaDep, MediaResourceInventoryTag as MediaRIT
from tangl.media.media_resource.resource_manager import ResourceManager
from tangl.media import story_media, system_media
from tangl.mechanics.presence.look.look import HasSimpleLook
from tangl.persistence.serializers import JsonSerializationHandler as Json
from tangl.presentation.hints import StagingHints
from tangl.prose import DialogMuBlock
from tangl.prose.naming import NamedActor, NamedLocation, ProseBlock, naming_dispatch
from tangl.prose.portraits import HasPortraits, PackedPortraits, PortraitLook, portrait_dispatch
from tangl.service.media import media_fragment_to_payload
from tangl.service.response import RuntimeEnvelope
from tangl.story import Actor, InitMode, Location, Role, Setting, World
from tangl.story.episode import Action
from tangl.story.fabula.builder import WorldBuilder
from tangl.story.fabula.compiler import StoryCompiler
from tangl.vm import Ledger, Requirement, ResolutionPhase
from tangl.vm.dispatch import do_journal, do_update
from tangl.vm.runtime.frame import PhaseCtx
from tangl.vm.replay import CheckpointRecord, Patch, get_replay_engine


class PortraitActor(HasPortraits, NamedActor):
    def nominate_portrait_look(self, *, ctx: PhaseCtx, attitude: str | None) -> str | None:
        return ctx.get_ns(ctx.cursor).get("portrait_look", self.portraits.default_look)


class DefaultPortraitActor(HasPortraits, Actor):
    """No naming, Presence, or generated-media infrastructure required."""


class PortraitLocation(HasPortraits, NamedLocation):
    """Settings use the same current-provider contract, not location-prop policy."""


class SimplePortraitActor(HasSimpleLook, PortraitActor):
    """An existing descriptive adapter must not shadow packed portrait output."""


def portrait_data(prefix: str = "rin") -> dict[str, object]:
    return {
        "default_look": "everyday",
        "attitudes": {"amused": "happy", "relieved": "happy", "dry": "skeptical",
                      "dry.attentive": "skeptical", "flat": "neutral", "startled": "surprised"},
        "looks": {
            look: {"base": f"{prefix}/{look}/base.svg", "expressions": {
                expression: f"{prefix}/{look}/{expression}.svg"
                for expression in ("happy", "skeptical")
            }} for look in ("everyday", "special")
        } | {"empty": {}},
    }


@pytest.fixture
def world(tmp_path: Path) -> Iterator[World]:
    resources = ResourceManager(tmp_path)
    for index, (look, face) in enumerate(
        (look, face) for look in ("everyday", "special") for face in ("base", "happy", "skeptical")
    ):
        path = tmp_path / "rin" / look / f"{face}.svg"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            f'<svg xmlns="http://www.w3.org/2000/svg"><rect fill="#{index:06x}"/></svg>'
        )
    resources.index_directory(".")
    classes = {"PortraitActor": PortraitActor, "ProseBlock": ProseBlock}
    bundle = StoryCompiler().compile({
        "label": "packed_portraits", "metadata": {"start_at": "s.start"},
        "actors": {"rin": {"kind": "PortraitActor", "name": "Rin",
                            "anonymous_name": "a stranger", "naming_policy": "concealed",
                            "portraits": portrait_data()}},
        "scenes": {"s": {"roles": {"host": {"actor_ref": "rin"}}, "blocks": {
            "start": {"kind": "ProseBlock", "prose": [
                {"dialog_class": "host.amused", "text": "Hello."},
                {"dialog_class": "host.dry", "text": "Really?"},
            ], "media": [{"name": "rin/everyday/base.svg", "media_role": "avatar_im"}],
                "actions": [{"text": "Continue", "successor": "again"}]},
            "again": {"content": "> [!host.dry.attentive] A literal title\n> Again.",
                      "actions": [{"text": "Return", "successor": "start"}]},
        }}},
    }, class_registry=classes)
    result = WorldBuilder().build(
        label="packed_portraits", bundle=bundle, resources=resources, class_registry=classes,
        extra_authorities=[naming_dispatch, portrait_dispatch],
    )
    yield result
    World.clear_instances()


def make_ledger(world: World, mode: InitMode = InitMode.EAGER) -> Ledger:
    graph = world.create_story("packed_portraits", init_mode=mode).graph
    return Ledger.from_graph(graph=graph, entry_id=graph.initial_cursor_id)


def actor(ledger: Ledger) -> PortraitActor:
    subject = ledger.graph.find_one(Selector(has_kind=PortraitActor))
    assert isinstance(subject, PortraitActor)
    return subject


def prepare(ledger: Ledger) -> PhaseCtx:
    ctx = PhaseCtx(graph=ledger.graph, cursor_id=ledger.cursor_id,
                   current_phase=ResolutionPhase.UPDATE)
    do_update(ledger.cursor, ctx=ctx)
    return ctx.derive(current_phase=ResolutionPhase.JOURNAL)


def test_actual_journal_emits_following_portraits_with_original_attitudes(world: World) -> None:
    ledger = make_ledger(world)
    ctx = prepare(ledger)
    before = ledger.graph.value_hash()
    fragments = do_journal(ledger.cursor, ctx=ctx)
    dialog = [item for item in fragments if isinstance(item, AttributedFragment)
              or isinstance(item, MediaFragment) and item.media_role == "dialog_im"]
    assert [type(item) for item in dialog] == [
        AttributedFragment, MediaFragment, AttributedFragment, MediaFragment,
    ]
    first, happy, second, skeptical = dialog
    assert first.who == second.who == "a stranger"
    for line in (first, second):
        assert isinstance(fragments[fragments.index(line) + 1], MediaFragment)
    assert [first.speaker_attitude, second.speaker_attitude] == ["amused", "dry"]
    assert [first.how, second.how] == ["dialog.amused", "dialog.dry"]
    assert happy.content is not skeptical.content
    assert happy.content.path.name == "happy.svg"
    assert skeptical.content.path.name == "skeptical.svg"
    assert happy.content.registry is ledger.graph
    assert first.source_id == happy.source_id == ledger.cursor_id
    assert happy.origin_id == first.origin_id and skeptical.origin_id == second.origin_id
    assert happy.speaker_id == skeptical.speaker_id == actor(ledger).uid
    assert happy.media_role == skeptical.media_role == "dialog_im"
    wire = json.loads(json.dumps(RuntimeEnvelope(fragments=fragments).to_dto()))
    projected = next(item for item in wire["fragments"] if item["uid"] == str(happy.uid))
    assert projected["rit_id"] == str(happy.content.uid)
    payload = media_fragment_to_payload(
        happy, world_id=world.label, world_media_root=world.resources.resource_path,
    )
    assert payload["content_format"] == "url"
    assert payload["url"].endswith("/rin/everyday/happy.svg")
    assert "media_payload" not in projected
    assert any(isinstance(item, MediaFragment) and item.media_role == "avatar_im"
               and item.content.path.name == "base.svg" for item in fragments)
    do_journal(ledger.cursor, ctx=ctx)
    assert ledger.graph.value_hash() == before
    assert all(resource.registry is world.resources.registry
               for resource in world.resources.registry.values())


def test_each_lines_portrait_carries_the_worlds_staging_and_keeps_it_restored(
        world: World) -> None:
    # A speaker with no staged portrait has no staging to take, so the world
    # says how a line's portrait is staged -- here, hidden with the viewer's
    # faces -- and every one a line brings carries it, before and after restore.
    ledger = make_ledger(world)
    hints = StagingHints(media_visibility={"preference_id": "portraits", "values": [True]})
    subject = actor(ledger)
    subject.portraits = subject.portraits.model_copy(update={"staging_hints": hints})
    restored = type(ledger.graph).structure(Json.deserialize(Json.serialize(
        ledger.graph.unstructure())))
    for graph in (ledger.graph, restored):
        story = Ledger.from_graph(graph=graph, entry_id=graph.initial_cursor_id)
        faces = [item for item in do_journal(story.cursor, ctx=prepare(story))
                 if isinstance(item, MediaFragment) and item.media_role == "dialog_im"]
        assert len(faces) == 2
        assert all(face.staging_hints == hints for face in faces)


def staged_portrait_world(root: Path, staging: dict[str, object]) -> Path:
    """A world folder whose one speaker gives each line's portrait `staging`."""
    root.mkdir()
    (root / "domain.py").write_text(
        "from tangl.prose.portraits import HasPortraits\n"
        "from tangl.story import Actor\n\n\n"
        "class Speaker(HasPortraits, Actor):\n    pass\n")
    (root / "world.yaml").write_text(yaml.safe_dump({
        "label": root.name, "scripts": "script.yaml", "domain_module": "domain",
        "metadata": {"ui_preferences": [
            {"id": "faces", "kind": "boolean", "label": "Faces", "default": True},
            {"id": "pose", "kind": "enum", "label": "Pose", "values": ["still", "wave"],
             "default": "still"},
        ]},
    }))
    (root / "script.yaml").write_text(yaml.safe_dump({
        "label": root.name, "metadata": {"start_at": "s.start"},
        "actors": {"rin": {"kind": "Speaker", "name": "Rin", "portraits": {
            "default_look": "day", "looks": {"day": {"base": "rin.svg"}},
            "staging_hints": staging}}},
        "scenes": {"s": {"roles": {"host": {"actor_ref": "rin"}},
                         "blocks": {"start": {"content": "Hello."}}}},
    }))
    return root


@pytest.mark.parametrize(("staging", "match"), [
    ({"media_visibility": {"preference_id": "portraits", "values": [True]}},
     "Unknown ui preference"),
    ({"media_visibility": {"preference_id": "faces", "values": ["true"]}},
     "outside ui preference"),
    ({"media_clip_binding": {"axes": ["mood"], "rows": [{"values": ["happy"], "clip": "smile"}]}},
     "Unknown ui preference"),
    ({"media_clip_binding": {"axes": ["pose"], "rows": [{"values": ["dance"], "clip": "wave"}]}},
     "outside ui preference"),
], ids=["unknown preference", "value outside a boolean", "unknown clip axis",
        "value outside an enum"])
def test_a_portraits_staging_bindings_are_checked_when_the_world_loads(
        tmp_path: Path, staging: dict[str, object], match: str) -> None:
    # A speaker's packed portraits bind each line's portrait to the world's
    # viewer preferences, as block media do, and are refused at load by the
    # same rules -- not left for a client to trip over when it draws.
    root = staged_portrait_world(tmp_path / "refused", staging)
    with pytest.raises(ValueError, match=match):
        WorldCompiler().compile(WorldBundle.load(root))


def test_a_portrait_bound_to_a_declared_preference_loads(tmp_path: Path) -> None:
    root = staged_portrait_world(tmp_path / "bound", {
        "media_visibility": {"preference_id": "faces", "values": [True]}})
    world = WorldCompiler().compile(WorldBundle.load(root))
    speaker = next(t.payload for t in world.bundle.template_registry.values()
                   if isinstance(t.payload, HasPortraits))
    assert speaker.portraits.staging_hints.media_visibility.preference_id == "faces"


@pytest.mark.parametrize("look", ["everyday", "special"])
@pytest.mark.parametrize("attitude, face", [
    ("amused", "happy"), ("relieved", "happy"), ("dry", "skeptical"),
    ("dry.attentive", "skeptical"), ("startled", "base"), ("flat", "base"),
    ("unknown", "base"), ("amused.attentive", "base"), (None, "base"),
])
def test_exact_expression_mapping_and_current_look_fallback(
    world: World, look: str, attitude: str | None, face: str,
) -> None:
    ledger = make_ledger(world)
    ledger.cursor.locals["portrait_look"] = look
    ctx = prepare(ledger)
    subject = actor(ledger)
    before = ledger.graph.value_hash()
    resource = subject.dialog_portrait(ctx=ctx, attitude=attitude)
    expected = f"rin/{look}/{face}.svg"
    assert resource.path.relative_to(world.resources.resource_path).as_posix() == expected
    payload = media_fragment_to_payload(
        MediaFragment(content=resource, content_format="rit", media_role="dialog_im"),
        world_id=world.label, world_media_root=world.resources.resource_path,
    )
    assert payload["url"] == f"/media/world/{world.label}/{expected}"
    assert ledger.graph.value_hash() == before


@pytest.mark.parametrize("look", [None, "empty"])
def test_no_nominated_look_or_no_art_emits_no_portrait(world: World, look: str | None) -> None:
    ledger = make_ledger(world)
    ledger.cursor.locals["portrait_look"] = look
    fragments = do_journal(ledger.cursor, ctx=prepare(ledger))
    assert not any(isinstance(fragment, MediaFragment) and fragment.media_role == "dialog_im"
                   for fragment in fragments)
    assert any(isinstance(fragment, MediaFragment) and fragment.media_role == "avatar_im"
               for fragment in fragments)


def test_missing_or_failed_variant_falls_back_only_to_this_look(world: World) -> None:
    ledger = make_ledger(world)
    ledger.cursor.locals["portrait_look"] = "special"
    ctx = prepare(ledger)
    subject = actor(ledger)
    variant = subject.dialog_portrait(ctx=ctx, attitude="amused")
    variant.path.unlink()
    base = subject.dialog_portrait(ctx=ctx, attitude="amused")
    assert base.path.parent.name == "special" and base.path.name == "base.svg"
    base.path.unlink()
    assert subject.dialog_portrait(ctx=ctx, attitude="amused") is None


def test_bad_declarations_fail_at_typed_boundary() -> None:
    with pytest.raises(ValidationError, match="default_look.*missing"):
        PackedPortraits(default_look="missing")
    with pytest.raises(ValidationError, match="looks.day.expressions.happy"):
        PackedPortraits(looks={"day": {"expressions": {"happy": ""}}})


def test_ledger_json_restores_declarations_and_graph_owned_history(world: World) -> None:
    ledger = make_ledger(world)
    ledger.get_frame().goto_node(ledger.cursor)
    before = list(ledger.get_journal())
    restored = Ledger.structure(Json.deserialize(Json.serialize(ledger.unstructure())))
    assert actor(restored).portraits == actor(ledger).portraits
    assert actor(restored).portrait_dependency_ids == actor(ledger).portrait_dependency_ids
    assert [fragment.uid for fragment in restored.get_journal()] == [
        fragment.uid for fragment in before
    ]
    for fragment in restored.get_journal():
        if isinstance(fragment, MediaFragment):
            assert fragment.content is restored.graph.get(fragment.rit_id)
            assert fragment.content.registry is restored.graph


def test_independent_stories_do_not_share_mutable_resources(world: World) -> None:
    first, second = make_ledger(world), make_ledger(world)
    left = actor(first).dialog_portrait(ctx=prepare(first), attitude="amused")
    right = actor(second).dialog_portrait(ctx=prepare(second), attitude="amused")
    assert left.uid == right.uid and left is not right
    assert left.registry is first.graph and right.registry is second.graph


def advance(ledger: Ledger) -> None:
    ledger.resolve_choice(next(ledger.cursor.edges_out(Selector(has_kind=Action))).uid)


def journal_dto(ledger: Ledger) -> list[dict[str, object]]:
    return RuntimeEnvelope(fragments=list(ledger.get_journal())).to_dto()["fragments"]


def test_preparsed_raw_and_internal_return_share_selection_without_duplicate_history(
    world: World, monkeypatch: pytest.MonkeyPatch,
) -> None:
    ledger = make_ledger(world)
    # Real ledger traversal records admission in its patch, unlike an untraced Frame.goto_node.
    advance(ledger)
    original = journal_dto(ledger)
    restored = Ledger.structure(Json.deserialize(Json.serialize(ledger.unstructure())))
    journal = list(restored.get_journal())
    line = next(item for item in journal if isinstance(item, AttributedFragment)
                and item.content == "Again.")
    portrait = journal[journal.index(line) + 1]
    assert line.who == "A literal title" and line.speaker_attitude == "dry.attentive"
    assert portrait.content.path.name == "skeptical.svg"
    advance(restored)
    advance(restored)
    advance(restored)
    journal = list(restored.get_journal())
    assert sum(isinstance(item, AttributedFragment) and item.content == "Hello."
               for item in journal) == 2
    assert journal_dto(restored)[:len(original)] == original
    historical = journal_dto(restored)

    def no_nomination(*_args: object, **_kwargs: object) -> None:
        pytest.fail("historical restore/replay must not nominate portraits")

    monkeypatch.setattr(PortraitActor, "nominate_portrait_look", no_nomination)
    reopened = Ledger.structure(Json.deserialize(Json.serialize(restored.unstructure())))
    engine = get_replay_engine(reopened.replay_algorithm_id)
    checkpoint = next(Selector(has_kind=CheckpointRecord).filter(reopened.output_stream))
    graph = engine.restore_checkpoint(checkpoint)
    for patch in Selector(has_kind=Patch).filter(reopened.output_stream):
        graph = engine.apply_delta(graph=graph, delta=patch)
    replayed_actor = graph.find_one(Selector(has_kind=PortraitActor))
    assert replayed_actor.portrait_dependency_ids == actor(restored).portrait_dependency_ids
    assert journal_dto(reopened) == historical


def test_recast_uses_new_provider_art_not_anonymous_or_literal_label(world: World) -> None:
    ledger = make_ledger(world)
    ledger.get_frame().goto_node(ledger.cursor)
    historical = list(ledger.get_journal())
    old_resource_ids = [item.rit_id for item in historical if isinstance(item, MediaFragment)
                        and item.media_role == "dialog_im"]
    role = ledger.graph.find_one(Selector(has_kind=Role))
    data = portrait_data()
    data["default_look"] = "special"
    replacement = EntityTemplate.from_data({
        "kind": PortraitActor, "label": "new_actor", "name": "Beth",
        "anonymous_name": "another stranger", "naming_policy": "concealed", "portraits": data,
    }).materialize(registry=ledger.graph)
    role.requirement = Requirement(has_kind=Actor)
    role.set_provider(replacement)
    advance(ledger)
    journal = list(ledger.get_journal())
    line = next(item for item in journal if isinstance(item, AttributedFragment)
                and item.content == "Again.")
    portrait = journal[journal.index(line) + 1]
    assert line.speaker_id == str(replacement.uid)
    assert line.who == "A literal title"
    assert portrait.content.path.parent.name == "special"
    assert portrait.rit_id not in old_resource_ids
    assert [item.unstructure() for item in journal[:len(historical)]] == [
        item.unstructure() for item in historical
    ]


def test_lazy_provider_preparation_and_repeated_journal_are_read_only(world: World) -> None:
    ledger = make_ledger(world, InitMode.LAZY)
    assert ledger.graph.find_one(Selector(has_kind=PortraitActor)) is None
    # Enter the role-owning scene so ordinary PLANNING creates its lazy actor.
    ledger.get_frame().goto_node(ledger.cursor.parent)
    subject = actor(ledger)
    assert len(subject.portrait_dependency_ids) == 6
    ctx = prepare(ledger)
    before = ledger.graph.value_hash()
    size = len(ledger.graph)
    assert subject.dialog_portrait(ctx=ctx, attitude="amused") is subject.dialog_portrait(
        ctx=ctx, attitude="relieved",
    )
    for _ in range(3):
        fragments = do_journal(ledger.cursor, ctx=ctx)
        assert any(isinstance(item, MediaFragment) and item.media_role == "dialog_im"
                   for item in fragments)
    prepare(ledger)
    assert len(ledger.graph) == size and ledger.graph.value_hash() == before


def test_service_json_reopen_reuses_graph_owned_history_without_nomination(
    world: World, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tangl.persistence import PersistenceManagerFactory
    from tangl.service import ServiceManager
    from tangl.service.user.user import User

    persistence = PersistenceManagerFactory.json_file(base_path=tmp_path / "sessions")
    manager = ServiceManager(persistence)
    user = User(label="portrait-reader")
    persistence.save(user)
    envelope = manager.create_story(user_id=user.uid, world_id=world.label, world=world)
    wire = json.loads(json.dumps(envelope.to_dto()))
    expected = [item for item in wire["fragments"] if item.get("media_role") == "dialog_im"]
    assert len(expected) == 2 and expected[0]["rit_id"] != expected[1]["rit_id"]

    def no_nomination(*_args: object, **_kwargs: object) -> None:
        pytest.fail("reading saved output must not nominate portraits")

    monkeypatch.setattr(PortraitActor, "nominate_portrait_look", no_nomination)
    reopened = ServiceManager(PersistenceManagerFactory.json_file(base_path=tmp_path / "sessions"))
    restored = reopened.get_story_update(user_id=user.uid)
    assert restored.to_dto() == envelope.to_dto()
    with reopened.open_session(user_id=user.uid) as session:
        subject = actor(session.ledger)
        assert subject.portraits.default_look == "everyday"
        for fragment in session.ledger.get_journal():
            if isinstance(fragment, MediaFragment):
                assert fragment.content is session.ledger.graph.get(fragment.rit_id)


def test_admission_is_update_only_and_selection_never_scans_inventory_or_graph(
    world: World, monkeypatch: pytest.MonkeyPatch,
) -> None:
    ledger = make_ledger(world)
    inventory_before = [resource.unstructure() for resource in world.resources.registry.values()]
    ctx = prepare(ledger)
    assert inventory_before == [
        resource.unstructure() for resource in world.resources.registry.values()
    ]
    subject = actor(ledger)
    before = ledger.graph.value_hash()
    ctx.get_ns(ctx.cursor)  # Assemble the ordinary scoped namespace once, not per line.

    def forbidden(*_args: object, **_kwargs: object) -> None:
        pytest.fail("portrait selection must not scan or admit resources")

    monkeypatch.setattr(world.resources, "get_rit", forbidden)
    monkeypatch.setattr(type(ledger.graph), "find_all", forbidden)
    monkeypatch.setattr(type(ledger.graph), "find_one", forbidden)
    monkeypatch.setattr(type(ledger.graph), "add", forbidden)
    for _ in range(3):
        assert subject.dialog_portrait(ctx=ctx, attitude="amused").registry is ledger.graph
    # Actual JOURNAL may perform unrelated choice/namespace queries; forbid admission there too.
    monkeypatch.undo()
    monkeypatch.setattr(type(ledger.graph), "add", forbidden)
    monkeypatch.setattr(world.resources, "get_rit", forbidden)
    do_journal(ledger.cursor, ctx=ctx)
    assert ledger.graph.value_hash() == before


def test_missing_optional_inventory_art_is_soft_and_uses_current_base(world: World) -> None:
    ledger = make_ledger(world)
    subject = actor(ledger)
    subject.portraits.looks["special"].expressions["happy"] = "missing/optional.svg"
    ledger.cursor.locals["portrait_look"] = "special"
    ctx = prepare(ledger)
    dependency = ledger.graph.get(subject.portrait_dependency_ids["missing/optional.svg"])
    assert dependency.provider is None and not dependency.requirement.hard_requirement
    selected = subject.dialog_portrait(ctx=ctx, attitude="amused")
    assert selected.path.parent.name == "special" and selected.path.name == "base.svg"


def test_in_place_default_declaration_state_survives_constructor_json(world: World) -> None:
    ledger = make_ledger(world)
    subject = actor(ledger)
    subject.portraits = PackedPortraits()
    subject.portraits.looks["new"] = PortraitLook()
    subject.portraits.looks["new"].expressions["skeptical"] = "rin/special/skeptical.svg"
    subject.portraits.attitudes["dry"] = "skeptical"
    subject.portraits.default_look = "new"
    restored = Ledger.structure(Json.deserialize(Json.serialize(ledger.unstructure())))
    assert actor(restored).portraits == subject.portraits
    ctx = prepare(restored)
    assert actor(restored).dialog_portrait(ctx=ctx, attitude="dry").path.parent.name == "special"


def test_non_adopted_world_keeps_explicit_block_media_and_has_no_portrait_state(
    world: World,
) -> None:
    world.extra_authorities[:] = [naming_dispatch]
    ledger = make_ledger(world)
    fragments = do_journal(ledger.cursor, ctx=prepare(ledger))
    assert actor(ledger).portrait_dependency_ids == {}
    assert not any(isinstance(item, MediaFragment) and item.media_role == "dialog_im"
                   for item in fragments)
    assert any(isinstance(item, MediaFragment) and item.media_role == "avatar_im"
               for item in fragments)


def test_raw_role_provider_without_naming_adoption_uses_default_nomination(world: World) -> None:
    world.extra_authorities[:] = [portrait_dispatch]
    ledger = make_ledger(world)
    replacement = EntityTemplate.from_data({
        "kind": DefaultPortraitActor, "label": "plain", "name": "A speaker",
        "portraits": portrait_data(),
    }).materialize(registry=ledger.graph)
    role = ledger.graph.find_one(Selector(has_kind=Role))
    role.requirement = Requirement(has_kind=Actor)
    role.set_provider(replacement)
    ledger.cursor.content = "> [!host_role.dry] Explicit override\n> Raw speech."
    fragments = do_journal(ledger.cursor, ctx=prepare(ledger))
    line = next(item for item in fragments if isinstance(item, AttributedFragment))
    portrait = fragments[fragments.index(line) + 1]
    assert line.speaker_id == str(replacement.uid) and line.who == "Explicit override"
    assert portrait.content.path.name == "skeptical.svg"


def test_has_simple_look_descriptive_payload_does_not_shadow_packed_portrait(world: World) -> None:
    ledger = make_ledger(world)
    replacement = EntityTemplate.from_data({
        "kind": SimplePortraitActor, "label": "simple", "name": "Rin",
        "portraits": portrait_data(),
    }).materialize(registry=ledger.graph)
    role = ledger.graph.find_one(Selector(has_kind=Role))
    role.requirement = Requirement(has_kind=Actor)
    role.set_provider(replacement)
    fragments = do_journal(ledger.cursor, ctx=prepare(ledger))
    line = next(item for item in fragments if isinstance(item, AttributedFragment))
    assert isinstance(line.media_payload, dict) and line.media_payload
    portrait = fragments[fragments.index(line) + 1]
    assert portrait.content.path.name == "happy.svg" and portrait.content.registry is ledger.graph


def test_setting_speaker_resolves_its_current_provider_before_portrait_selection(
    world: World,
) -> None:
    ledger = make_ledger(world)
    location = EntityTemplate.from_data({
        "kind": PortraitLocation, "label": "place", "name": "The room",
        "portraits": portrait_data(),
    }).materialize(registry=ledger.graph)
    setting = EntityTemplate.from_data({
        "kind": Setting, "label": "place", "predecessor_id": ledger.cursor.parent.uid,
        "requirement": Requirement(has_kind=Location),
    }).materialize(registry=ledger.graph)
    setting.set_provider(location)
    ledger.cursor.media[0]["speaker"] = "place_setting"
    ledger.cursor.prose = [DialogMuBlock(dialog_class="place_setting.dry", text="Welcome.")]
    fragments = do_journal(ledger.cursor, ctx=prepare(ledger))
    line = next(item for item in fragments if isinstance(item, AttributedFragment))
    portrait = fragments[fragments.index(line) + 1]
    assert line.speaker_id == str(location.uid)
    assert all(item.speaker_id == location.uid for item in fragments
               if isinstance(item, MediaFragment))
    assert portrait.content is location.dialog_portrait(ctx=prepare(ledger), attitude="dry")


@pytest.mark.parametrize("scope", ["story", "sys"])
@pytest.mark.parametrize("with_world_resources", [False, True])
def test_scoped_nested_aliases_use_their_manager_and_restore_history_without_lookup(
    world: World, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    scope: str, with_world_resources: bool,
) -> None:
    scoped_world = WorldBuilder().build(
        label=f"scoped_portraits_{scope}", bundle=world.bundle,
        resources=world.resources if with_world_resources else None,
        class_registry=world.class_registry, extra_authorities=world.extra_authorities,
    )
    root = tmp_path / scope
    for index, (look, face) in enumerate(
        (look, face) for look in ("everyday", "special") for face in ("base", "happy", "skeptical")
    ):
        path = root / "rin" / look / f"{face}.svg"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            f'<svg xmlns="http://www.w3.org/2000/svg"><rect fill="#{index + 100:06x}"/></svg>'
        )
    manager = ResourceManager(root, scope=scope)
    manager.index_directory(".")
    if scope == "sys":
        system_media.get_system_resource_manager.cache_clear()
        monkeypatch.setattr(system_media, "get_sys_media_dir", lambda: root)
        manager = system_media.get_system_resource_manager()
    try:
        ledger = make_ledger(scoped_world)
        if scope == "story":
            ledger.graph.story_resources = manager
        subject = actor(ledger)
        subject.portraits.scope = scope
        source = manager.get_rit("rin/everyday/happy.svg")
        source_state = [item.unstructure() for item in manager.registry.values()]
        if with_world_resources:
            assert source.content_hash() != world.resources.get_rit(
                "rin/everyday/happy.svg",
            ).content_hash()
        ctx = prepare(ledger)
        assert manager.registry in [inventory.registry for inventory in ctx.get_media_inventories()]
        dependencies = [ledger.graph.get(uid) for uid in subject.portrait_dependency_ids.values()]
        assert len(dependencies) == 6 and all(dep.provider is not None for dep in dependencies)
        assert all(dep.provider.registry is ledger.graph for dep in dependencies)
        assert all(dep.provider.path.is_relative_to(root) for dep in dependencies)
        selected = subject.dialog_portrait(ctx=ctx, attitude="amused")
        assert selected.uid == source.uid and selected is not source
        ledger.get_frame().goto_node(ledger.cursor)
        fragments = list(ledger.get_journal())
        line = next(item for item in fragments if isinstance(item, AttributedFragment))
        portrait = fragments[fragments.index(line) + 1]
        assert isinstance(portrait, MediaFragment) and portrait.scope == scope
        assert portrait.content is ledger.graph.get(source.uid)
        payload = media_fragment_to_payload(
            portrait, world_id=scoped_world.label, story_id=str(ledger.graph.story_id),
            world_media_root=world.resources.resource_path if with_world_resources else None,
            story_media_root=root if scope == "story" else None,
            system_media_root=root if scope == "sys" else None,
        )
        prefix = f"/media/story/{ledger.graph.story_id}" if scope == "story" else "/media/sys"
        assert payload["scope"] == scope and payload["rit_id"] == str(source.uid)
        assert payload["url"] == f"{prefix}/rin/everyday/happy.svg"
        assert source_state == [item.unstructure() for item in manager.registry.values()]
        historical = journal_dto(ledger)

        def forbidden(*_args: object, **_kwargs: object) -> None:
            pytest.fail("historical readback must not nominate or look up source inventory")

        monkeypatch.setattr(PortraitActor, "nominate_portrait_look", forbidden)
        monkeypatch.setattr(ResourceManager, "get_rit", forbidden)
        restored = Ledger.structure(Json.deserialize(Json.serialize(ledger.unstructure())))
        assert journal_dto(restored) == historical
        for fragment in restored.get_journal():
            if isinstance(fragment, MediaFragment) and fragment.content_format == "rit":
                assert fragment.content is restored.graph.get(fragment.rit_id)
    finally:
        if scope == "sys":
            system_media.get_system_resource_manager.cache_clear()


def test_story_portrait_manager_uses_normal_read_only_discovery(
    world: World, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    ledger = make_ledger(world)
    root = tmp_path / "discovered_story"
    path = root / "nested" / "portrait.svg"
    path.parent.mkdir(parents=True)
    path.write_text('<svg xmlns="http://www.w3.org/2000/svg"><circle r="4"/></svg>')
    monkeypatch.setattr(story_media, "get_story_media_dir", lambda _story_id: root)
    ledger.graph.story_resources = None
    subject = actor(ledger)
    subject.portraits = PackedPortraits(
        scope="story", default_look="day", looks={"day": PortraitLook(base="nested/portrait.svg")},
    )
    before = sorted(root.rglob("*"))

    ctx = prepare(ledger)

    assert ledger.graph.story_resources.resource_path == root
    resource = subject.dialog_portrait(ctx=ctx, attitude=None)
    assert resource.path == path and resource.registry is ledger.graph
    assert sorted(root.rglob("*")) == before
