"""Naming through world compilation, binding, JOURNAL, and stored output."""
from collections.abc import Iterator
from pathlib import Path

import pytest

from tangl.core import Selector
from tangl.journal.fragments import AttributedFragment, ChoiceFragment, ContentFragment
from tangl.loaders import WorldBundle
from tangl.loaders.compiler import WorldCompiler
from tangl.prose.naming import NamingActor, NamingOperations, NamingPolicy
from tangl.story import Actor, InitMode, Role, World
from tangl.vm import Ledger, Requirement, ResolutionPhase
from tangl.vm.replay import CheckpointRecord, Patch, get_replay_engine
from tangl.vm.runtime.frame import PhaseCtx


@pytest.fixture
def ledger() -> Iterator[Ledger]:
    World.clear_instances()
    bundle = WorldBundle.load(Path(__file__).resolve().parents[3] / "worlds/concept_naming_demo")
    world = WorldCompiler().compile(bundle)
    graph = world.create_story("concept_naming_demo", init_mode=InitMode.EAGER).graph
    result = Ledger.from_graph(graph, entry_id=graph.initial_cursor_id)
    yield result
    World.clear_instances()


def meet(ledger: Ledger) -> None:
    ledger.resolve_choice(next(ledger.cursor.edges_out()).uid)


def test_ordered_introduction_and_shared_speaker_choice_names(ledger: Ledger) -> None:
    meet(ledger)
    journal = ledger.get_journal()
    texts = [fragment.content for fragment in journal if isinstance(fragment, ContentFragment)]
    assert "the blonde girl approaches at Market Square." in texts
    assert "Hi, I am Rin." in texts
    assert "Rin smiles." in texts
    speakers = [fragment for fragment in journal if isinstance(fragment, AttributedFragment)]
    assert [fragment.speaker_name for fragment in speakers] == ["the blonde girl", "Rin"]
    assert speakers[0].speaker_id == speakers[1].speaker_id
    assert [fragment.text for fragment in journal if isinstance(fragment, ChoiceFragment)] == ["Say hi to Rin"]


def test_reads_do_not_create_knowledge_and_narrators_are_isolated(ledger: Ledger) -> None:
    actor = ledger.graph.find_one(Selector(has_kind=Actor, label="rin"))
    ctx = PhaseCtx(graph=ledger.graph, cursor_id=ledger.cursor_id)
    before = ledger.graph.value_hash()
    operations = NamingOperations(ctx)
    assert operations.reference(actor) == "the blonde girl"
    assert operations.reference(actor, "proper") == "Rin"
    ctx.get_ns(ctx.cursor)
    assert actor.narrator_knowledge == {}
    assert ledger.graph.value_hash() == before
    with pytest.raises(RuntimeError, match="JOURNAL"):
        operations.introduce(actor)
    ctx.current_phase = ResolutionPhase.JOURNAL
    assert operations.introduce(actor) == "Rin"
    identified_hash = ledger.graph.value_hash()
    assert operations.introduce(actor) == "Rin"
    assert ledger.graph.value_hash() == identified_hash
    assert operations.reference(actor, "anonymous") == "the blonde girl"
    other = ctx.derive(meta={"narrator_key": "other"})
    assert NamingOperations(other).reference(actor) == "the blonde girl"
    assert "other" not in actor.narrator_knowledge


def test_override_opt_out_and_missing_nominal(ledger: Ledger) -> None:
    ctx = PhaseCtx(graph=ledger.graph, cursor_id=ledger.cursor_id)
    operations = NamingOperations(ctx)
    hidden = ledger.graph.find_one(Selector(label="hideout"))
    square = ledger.graph.find_one(Selector(label="square"))
    assert operations.reference(hidden) == "a hidden room"
    assert operations.reference(square) == "Market Square"
    assert square.narrator_knowledge == {}
    ctx.current_phase = ResolutionPhase.JOURNAL
    assert operations.introduce(hidden) == "Rin's Hideout"
    assert operations.reference(hidden) == "Rin's Hideout"
    actor = NamingActor(name="Named", naming_policy=NamingPolicy.OFF, registry=ledger.graph)
    assert operations.reference(actor) == "Named"
    assert operations.introduce(actor) == "Named"
    assert actor.narrator_knowledge == {}
    actor.naming_policy = NamingPolicy.CONCEALED
    with pytest.raises(ValueError, match="Missing anonymous_name"):
        operations.reference(actor)


def test_provider_knowledge_survives_scene_change_but_not_recasting(ledger: Ledger) -> None:
    meet(ledger)
    actor = ledger.graph.find_one(Selector(label="rin", has_kind=Actor))
    beth = ledger.graph.find_one(Selector(label="beth", has_kind=Actor))
    ctx = PhaseCtx(graph=ledger.graph, cursor_id=ledger.cursor_id)
    role = ctx.get_ns(ctx.cursor)["host_role"]
    assert isinstance(role, Role)
    assert role.narrator_knowledge == {}
    assert NamingOperations(ctx).reference(role) == "Rin"
    role.requirement = Requirement(has_kind=Actor)
    role.set_provider(beth)
    assert NamingOperations(ctx).reference(role) == "the dark-haired girl"
    assert beth.narrator_knowledge == {}
    role.set_provider(actor)
    ledger.resolve_choice(next(ledger.cursor.edges_out()).uid)
    assert any(getattr(fragment, "content", "") == "Hello again, Rin."
               for fragment in ledger.get_journal())


def test_constructor_restore_patch_replay_and_explicit_rollback(ledger: Ledger) -> None:
    meet(ledger)
    historical = [fragment.unstructure() for fragment in ledger.get_journal()]
    restored = Ledger.structure(ledger.unstructure())
    actor = restored.graph.find_one(Selector(has_kind=Actor, label="rin"))
    assert actor.peek_knowledge().state == "IDENTIFIED"
    assert [fragment.unstructure() for fragment in restored.get_journal()] == historical
    engine = get_replay_engine(restored.replay_algorithm_id)
    checkpoint = next(Selector(has_kind=CheckpointRecord).filter(restored.output_stream))
    replayed = engine.restore_checkpoint(checkpoint)
    for patch in Selector(has_kind=Patch).filter(restored.output_stream):
        replayed = engine.apply_delta(graph=replayed, delta=patch)
    assert replayed.get(actor.uid).peek_knowledge().state == "IDENTIFIED"
    restored.rollback_to_step(0)
    assert restored.graph.get(actor.uid).peek_knowledge() is None
    assert not any(getattr(fragment, "content", "") == "Hi, I am Rin."
                   for fragment in restored.get_journal())
    meet(restored)
    speakers = [fragment for fragment in restored.get_journal()
                if isinstance(fragment, AttributedFragment)]
    assert [fragment.speaker_name for fragment in speakers] == ["the blonde girl", "Rin"]


def test_json_service_roundtrip_retains_identification_and_output(
    ledger: Ledger, tmp_path: Path,
) -> None:
    from tangl.persistence import PersistenceManagerFactory
    from tangl.service import ServiceManager
    from tangl.service.response import DirectEdgeRequest
    from tangl.service.user.user import User

    persistence = PersistenceManagerFactory.json_file(base_path=tmp_path)
    manager = ServiceManager(persistence)
    user = User(label="naming-reader")
    persistence.save(user)
    manager.create_story(user_id=user.uid, world_id=ledger.graph.world.label,
                         world=ledger.graph.world, init_mode=InitMode.EAGER.value)
    with manager.open_session(user_id=user.uid) as session:
        edge_id = next(session.ledger.cursor.edges_out()).uid
    result = manager.resolve_choice(user_id=user.uid, request=DirectEdgeRequest(edge_id=edge_id))
    assert any(isinstance(fragment, ChoiceFragment) and fragment.text == "Say hi to Rin"
               for fragment in result.fragments)
    restarted = ServiceManager(PersistenceManagerFactory.json_file(base_path=tmp_path))
    with restarted.open_session(user_id=user.uid) as session:
        actor = session.ledger.graph.find_one(Selector(has_kind=Actor, label="rin"))
        assert actor.peek_knowledge().state == "IDENTIFIED"
        assert any(getattr(fragment, "content", "") == "Hi, I am Rin."
                   for fragment in session.ledger.get_journal())


def test_jinja_and_semantic_references_share_policy_and_generated_text_is_literal(
    ledger: Ledger,
) -> None:
    from tangl.prose.naming import ConceptReference, ProseBlock, ProseSegment

    block = ledger.graph.find_one(Selector(has_kind=ProseBlock))
    block.prose = [
        ProseSegment(template="{{ reference(host) }} / {{ introduce(host) }} / {{ reference(host) }}"),
        ProseSegment(text=[ConceptReference(ref="host", intent="anonymous"), " / ",
                          ConceptReference(ref="host")]),
    ]
    meet(ledger)
    texts = [getattr(fragment, "content", "") for fragment in ledger.get_journal()]
    assert "the blonde girl / Rin / Rin" in texts
    assert "the blonde girl / Rin" in texts


def test_linked_labels_reject_introductions_without_disclosure(ledger: Ledger) -> None:
    from tangl.prose.naming import ConceptReference

    ctx = PhaseCtx(graph=ledger.graph, cursor_id=ledger.cursor_id)
    actor = ctx.get_ns(ctx.cursor)["host"]
    with pytest.raises(ValueError, match="display label"):
        NamingOperations(ctx).realize([ConceptReference(ref="host", introduce=True)])
    assert actor.narrator_knowledge == {}


def test_template_generated_wording_is_not_executed_again(ledger: Ledger) -> None:
    from tangl.prose.naming import ProseBlock, ProseSegment

    actor = ledger.graph.find_one(Selector(has_kind=Actor, label="rin"))
    actor.name = "{{ introduce(host) }}"
    block = ledger.graph.find_one(Selector(has_kind=ProseBlock))
    block.prose = [ProseSegment(template="{{ reference(host, 'proper') }}")]
    meet(ledger)
    assert actor.narrator_knowledge == {}
    assert any(getattr(fragment, "content", "") == "{{ introduce(host) }}"
               for fragment in ledger.get_journal())


def test_nearest_kind_default_and_world_text_aspect_override(ledger: Ledger) -> None:
    from tangl.core import BehaviorRegistry, DispatchLayer, Priority

    actor = ledger.graph.find_one(Selector(has_kind=Actor, label="rin"))
    ctx = PhaseCtx(graph=ledger.graph, cursor_id=ledger.cursor_id)
    ns = ctx.get_ns(ctx.cursor)
    ns["naming_defaults"] = {"NamingActor": "proper", "Actor": "concealed"}
    assert NamingOperations(ctx).reference(actor) == "Rin"
    actor.naming_policy = NamingPolicy.CONCEALED
    assert NamingOperations(ctx).reference(actor) == "the blonde girl"
    authority = BehaviorRegistry(default_dispatch_layer=DispatchLayer.AUTHOR)

    @authority.register(task="render_text", priority=Priority.LATE)
    def alternate_wording(*, caller: object, aspect: str, **kwargs: object) -> str | None:
        if caller is actor and aspect == "reference_auto":
            return "a world-selected handle"
        return None

    ctx.local_authorities.append(authority)
    assert NamingOperations(ctx).reference(actor) == "a world-selected handle"
    assert actor.narrator_knowledge == {}


def test_vanilla_world_has_no_naming_operations_or_text_rewriting() -> None:
    world = World.from_script_data(script_data={
        "label": "vanilla_naming_control",
        "metadata": {"start_at": "s.start"},
        "scenes": {"s": {"blocks": {"start": {"content": "Rin #intro is raw prose."}}}},
    })
    try:
        graph = world.create_story("vanilla_naming_control", init_mode=InitMode.EAGER).graph
        ctx = PhaseCtx(graph=graph, cursor_id=graph.initial_cursor_id)
        assert "introduce" not in ctx.get_ns(ctx.cursor)
        ledger = Ledger.from_graph(graph, entry_id=graph.initial_cursor_id)
        frame = ledger.get_frame()
        frame.goto_node(ledger.cursor)
        assert any(getattr(fragment, "content", "") == "Rin #intro is raw prose."
                   for fragment in ledger.get_journal())
    finally:
        World.clear_instances()
