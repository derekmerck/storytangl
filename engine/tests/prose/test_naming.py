"""Naming through world compilation, binding, JOURNAL, and stored output."""
from collections.abc import Iterator
from pathlib import Path
import subprocess
import sys

import pytest

from tangl.core import Selector
from tangl.journal.fragments import AttributedFragment, ChoiceFragment, ContentFragment
from tangl.loaders import WorldBundle
from tangl.loaders.compiler import WorldCompiler
from tangl.prose.naming import NamedActor, NamingOperations, NamingPolicy
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


def test_symbolic_role_speakers_resolve_provider_per_unit_before_metadata(
    ledger: Ledger, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tangl.prose import DialogMuBlock
    from tangl.prose.naming import ProseBlock, render_linked_prose

    monkeypatch.setattr(NamedActor, "get_dialog_style",
                        lambda self, dialog_class: {"speaker": self.label}, raising=False)
    monkeypatch.setattr(NamedActor, "get_dialog_image",
                        lambda self, dialog_class: f"{self.label}.svg", raising=False)
    block = ledger.graph.find_one(Selector(has_kind=ProseBlock, label="introduction"))
    ctx = PhaseCtx(graph=ledger.graph, cursor_id=block.uid,
                   current_phase=ResolutionPhase.JOURNAL)
    ns = ctx.get_ns(block)
    role = ns["host_role"]
    rin = role.provider
    role.requirement = Requirement(has_kind=Actor)
    role.set_provider(rin)
    beth = ledger.graph.find_one(Selector(label="beth", has_kind=Actor))
    ns["replacement"] = beth
    block.prose = [
        DialogMuBlock(label="host_role", dialog_class="NPC.happy",
                      template="{% set _ = host_role.set_provider(replacement) %}Hello."),
        DialogMuBlock(label="host_role", dialog_class="NPC.happy", text="Again."),
    ]
    authored = [unit.unstructure() for unit in block.prose]
    first, second = render_linked_prose(caller=block, ctx=ctx)
    assert [first.speaker_key, second.speaker_key] == ["host_role", "host_role"]
    assert [first.speaker_id, second.speaker_id] == [str(rin.uid), str(beth.uid)]
    assert [first.speaker_label, second.speaker_label] == ["rin", "beth"]
    assert [first.speaker_name, second.speaker_name] == ["the blonde girl", "the dark-haired girl"]
    assert first.presentation_hints.style_dict == {"speaker": "rin"}
    assert second.presentation_hints.style_dict == {"speaker": "beth"}
    assert first.media_payload["ref"] == "rin.svg"
    assert second.media_payload["ref"] == "beth.svg"
    assert rin.peek_knowledge() is None and beth.peek_knowledge() is None
    assert [unit.unstructure() for unit in block.prose] == authored
    before = ledger.graph.value_hash()
    assert render_linked_prose(caller=block, ctx=ctx)[0].speaker_id == str(beth.uid)
    assert ledger.graph.value_hash() == before


@pytest.mark.parametrize("unbound", [False, True])
def test_explicit_speaker_missing_or_unbound_fails_before_body(
    ledger: Ledger, unbound: bool,
) -> None:
    from tangl.prose import DialogMuBlock
    from tangl.prose.naming import ProseBlock, render_linked_prose

    block = ledger.graph.find_one(Selector(has_kind=ProseBlock, label="introduction"))
    ctx = PhaseCtx(graph=ledger.graph, cursor_id=block.uid,
                   current_phase=ResolutionPhase.JOURNAL)
    if unbound:
        ctx.get_ns(block)["host_role"].set_provider(None)
    block.prose = [DialogMuBlock(
        label="host_role" if unbound else "unbound_role", dialog_class="dialog",
        template="{{ introduce(sister) }}",
    )]
    before = ledger.graph.value_hash()
    with pytest.raises(TypeError if unbound else KeyError):
        render_linked_prose(caller=block, ctx=ctx)
    assert ledger.graph.value_hash() == before
    assert ctx.get_ns(block)["sister"].peek_knowledge() is None


def test_symbolic_setting_speaker_projects_location_not_setting(ledger: Ledger) -> None:
    from tangl.prose import DialogMuBlock
    from tangl.prose.naming import ProseBlock, render_linked_prose

    block = ledger.graph.find_one(Selector(has_kind=ProseBlock, label="introduction"))
    ctx = PhaseCtx(graph=ledger.graph, cursor_id=block.uid,
                   current_phase=ResolutionPhase.JOURNAL)
    setting = ctx.get_ns(block)["place_setting"]
    block.prose = [DialogMuBlock(label="place_setting", dialog_class="aside", text="Welcome.")]
    before = ledger.graph.value_hash()
    fragment = render_linked_prose(caller=block, ctx=ctx)[0]
    assert fragment.speaker_key == "place_setting"
    assert fragment.speaker_id == str(setting.provider.uid)
    assert fragment.speaker_label == "square"
    assert fragment.speaker_name == "Market Square"
    assert ledger.graph.value_hash() == before


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
    actor = NamedActor(name="Named", naming_policy=NamingPolicy.OFF, registry=ledger.graph)
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
    reopened = ServiceManager(PersistenceManagerFactory.json_file(base_path=tmp_path))
    with reopened.open_session(user_id=user.uid) as session:
        actor = session.ledger.graph.find_one(Selector(has_kind=Actor, label="rin"))
        assert actor.peek_knowledge().state == "IDENTIFIED"
        assert any(getattr(fragment, "content", "") == "Hi, I am Rin."
                   for fragment in session.ledger.get_journal())
    code = """
from pathlib import Path
import sys
from uuid import UUID
from tangl.core import Selector
from tangl.persistence import PersistenceManagerFactory
from tangl.service import ServiceManager
from tangl.service.response import DirectEdgeRequest
from tangl.story import Actor, World
from tangl.prose import DialogMuBlock, MuBlock
from tangl.prose.mu_block import ConceptReference
from tangl.lang.personal_name import PersonalName
from tangl.prose.naming import NamedConcept, PersonalNamedActor

assert World.get_instance('concept_naming_demo') is None
manager = ServiceManager(PersistenceManagerFactory.json_file(base_path=Path(sys.argv[1])))
manager.open_world('concept_naming_demo')
with manager.open_session(user_id=UUID(sys.argv[2])) as session:
    units = session.ledger.cursor.prose
    assert [type(unit) for unit in units] == [MuBlock, DialogMuBlock, MuBlock, DialogMuBlock]
    assert isinstance(units[0].text[0], ConceptReference)
    assert units[1].dialog_class == 'dialog'
    assert units[1].label == 'host'
    assert 'speaker_name' not in units[1].unstructure()
    actor = session.ledger.graph.find_one(Selector(has_kind=Actor, label='rin'))
    assert type(actor) is PersonalNamedActor
    assert type(actor.personal_name) is PersonalName
    assert actor.adopts()['Ms. Northstar'] == {'form': 'formal'}
    assert actor.peek_knowledge().state == 'IDENTIFIED'
    assert any(getattr(f, 'content', '') == 'Hi, I am Rin.' for f in session.ledger.get_journal())
    assert any(getattr(f, 'text', '') == 'Say hi to Rin' for f in session.ledger.get_journal())
    edge = next(session.ledger.cursor.edges_out())
result = manager.resolve_choice(user_id=UUID(sys.argv[2]), request=DirectEdgeRequest(edge_id=edge.uid))
assert any(getattr(f, 'content', '') == 'Hello again, Rin.' for f in result.fragments)
assert any(getattr(f, 'content', '') == 'You find an old sword.' for f in result.fragments)
assert any(getattr(f, 'content', '') == 'You carry Dawnblade.' for f in result.fragments)
with manager.open_session(user_id=UUID(sys.argv[2])) as session:
    sword = session.ledger.graph.find_one(Selector(has_kind=NamedConcept, label='sword'))
    assert sword.peek_knowledge().state == 'IDENTIFIED'
    assert sword.proper_forms == {'inscription': 'Dawnblade of the East'}
    assert session.ledger.cursor.prose[1].text[1].params == {'form': 'inscription'}
    assert sum(n.uid == sword.uid for n in session.ledger.graph.values()) == 1
print('bootstrapped cold restore and subsequent reference passed')
"""
    completed = subprocess.run(
        [sys.executable, "-c", code, str(tmp_path), str(user.uid)],
        capture_output=True, text=True, check=True,
    )
    assert "bootstrapped cold restore" in completed.stdout


def test_world_item_introduction_replay_restore_and_rollback(ledger: Ledger) -> None:
    from tangl.prose.naming import NamedConcept

    meet(ledger)
    ledger.resolve_choice(next(ledger.cursor.edges_out()).uid)
    sword = ledger.graph.find_one(Selector(has_kind=NamedConcept, label="sword"))
    assert sword.peek_knowledge().state == "IDENTIFIED"
    historical = [f.unstructure() for f in ledger.get_journal()]
    restored = Ledger.structure(ledger.unstructure())
    assert [f.unstructure() for f in restored.get_journal()] == historical
    engine = get_replay_engine(restored.replay_algorithm_id)
    checkpoint = next(Selector(has_kind=CheckpointRecord).filter(restored.output_stream))
    replayed = engine.restore_checkpoint(checkpoint)
    for patch in Selector(has_kind=Patch).filter(restored.output_stream):
        replayed = engine.apply_delta(graph=replayed, delta=patch)
    assert replayed.get(sword.uid).peek_knowledge().state == "IDENTIFIED"
    assert replayed.get(sword.uid).proper_forms == sword.proper_forms
    restored.rollback_to_step(1)
    assert restored.graph.get(sword.uid).peek_knowledge() is None
    ledger_sword_hash = restored.graph.value_hash()
    ctx = PhaseCtx(graph=restored.graph, cursor_id=restored.cursor_id)
    assert NamingOperations(ctx).reference(restored.graph.get(sword.uid)) == "an old sword"
    assert restored.graph.value_hash() == ledger_sword_hash
    restored.resolve_choice(next(restored.cursor.edges_out()).uid)
    contents = [f.content for f in restored.get_journal() if isinstance(f, ContentFragment)]
    assert contents.count("Its inscription reads Dawnblade of the East.") == 1


def test_authored_update_introduction_precedes_prose_and_labels(ledger: Ledger) -> None:
    edge = next(edge for edge in ledger.cursor.edges_out() if edge.text == "Introduce before prose")
    ledger.resolve_choice(edge.uid)
    speakers = [f for f in ledger.get_journal() if isinstance(f, AttributedFragment)]
    assert speakers[0].speaker_name == "Rin"
    assert speakers[0].content == "This is my sister, Nanae."


def test_nonprinting_introduction_preserves_current_label_and_literal_names(ledger: Ledger) -> None:
    from tangl.prose import DialogMuBlock
    from tangl.prose.naming import ProseBlock

    block = ledger.graph.find_one(Selector(has_kind=ProseBlock, label="introduction"))
    block.prose = [
        DialogMuBlock(label="host", dialog_class="dialog",
                      template="This is my sister, Nanae.{% set _ = introduce(host) %}"),
        DialogMuBlock(label="host", dialog_class="dialog", text=["Hello again."]),
    ]
    meet(ledger)
    speakers = [f for f in ledger.get_journal() if isinstance(f, AttributedFragment)]
    assert [f.speaker_name for f in speakers] == ["the blonde girl", "Rin"]
    assert speakers[0].content == "This is my sister, Nanae."


def test_literal_spoken_name_does_not_introduce_speaker_or_sister(ledger: Ledger) -> None:
    from tangl.prose import DialogMuBlock, MuBlock
    from tangl.prose.mu_block import ConceptReference
    from tangl.prose.naming import ProseBlock

    block = ledger.graph.find_one(Selector(has_kind=ProseBlock, label="introduction"))
    block.prose = [
        MuBlock(text="Narrative before the speaker."),
        DialogMuBlock(label="host", dialog_class="dialog", text=["This is my sister, Nanae."]),
        MuBlock(text=[ConceptReference(ref="sister", introduce=True), " smiles at you."]),
        DialogMuBlock(label="sister", dialog_class="NPC.happy", text="Rin #intro stays literal."),
    ]
    authored = [unit.unstructure() for unit in block.prose]
    meet(ledger)
    journal = [f for f in ledger.get_journal() if isinstance(f, ContentFragment)]
    assert [f.content for f in journal] == [
        "Narrative before the speaker.", "This is my sister, Nanae.",
        "Nanae smiles at you.", "Rin #intro stays literal.",
    ]
    speakers = [f for f in journal if isinstance(f, AttributedFragment)]
    speaker = speakers[0]
    assert speaker.speaker_name == "the blonde girl"
    assert speaker.content == "This is my sister, Nanae."
    rin = ledger.graph.find_one(Selector(has_kind=Actor, label="rin"))
    nanae = ledger.graph.find_one(Selector(has_kind=Actor, label="nanae"))
    assert rin.narrator_knowledge == {}
    assert nanae.peek_knowledge().state == "IDENTIFIED"
    assert speakers[1].speaker_name == "Nanae"
    assert speakers[1].how == "NPC.happy"
    assert speakers[1].speaker_attitude == "happy"
    assert [unit.unstructure() for unit in block.prose] == authored


@pytest.mark.parametrize("identified", [False, True])
def test_ordinary_dialog_labels_share_policy_without_disclosing(
    ledger: Ledger, identified: bool,
) -> None:
    from tangl.vm.dispatch import do_journal

    block = ledger.cursor
    block.content = "> [!dialog] host\n> This is my sister, Nanae."
    ctx = PhaseCtx(graph=ledger.graph, cursor_id=block.uid, current_phase=ResolutionPhase.JOURNAL)
    actor = ctx.get_ns(block)["host"]
    if identified:
        NamingOperations(ctx).introduce(actor)
    before = ledger.graph.value_hash()
    fragments = do_journal(block, ctx=ctx)
    speaker = next(f for f in fragments if isinstance(f, AttributedFragment))
    assert speaker.speaker_name == ("Rin" if identified else "the blonde girl")
    assert speaker.speaker_id == str(actor.uid)
    assert speaker.content == "This is my sister, Nanae."
    assert ledger.graph.value_hash() == before
    nanae = ledger.graph.find_one(Selector(has_kind=Actor, label="nanae"))
    assert nanae.narrator_knowledge == {}


def test_ordinary_whole_block_jinja_keeps_late_label_binding(ledger: Ledger) -> None:
    from tangl.vm.dispatch import do_journal

    ledger.graph.locals["text_template"] = "jinja"
    block = ledger.cursor
    block.content = (
        "> [!dialog] host\n> This is my sister, Nanae. {% set _ = introduce(host) %}"
        "\n\n> [!dialog] host\n> Hello again."
    )
    ctx = PhaseCtx(graph=ledger.graph, cursor_id=block.uid, current_phase=ResolutionPhase.JOURNAL)
    speakers = [f for f in do_journal(block, ctx=ctx) if isinstance(f, AttributedFragment)]
    assert [f.speaker_name for f in speakers] == ["Rin", "Rin"]
    assert speakers[0].content == "This is my sister, Nanae."


def test_vanilla_ordinary_dialog_keeps_name_fallback() -> None:
    from tangl.story import Block, StoryGraph
    from tangl.story.system_handlers import compose_dialog_markup

    graph = StoryGraph()
    actor = Actor(label="rin", name="Rin", registry=graph)
    block = Block(content="> [!dialog] rin\n> This is my sister, Nanae.", registry=graph)
    ctx = PhaseCtx(graph=graph, cursor_id=block.uid)
    ctx._ns_cache[block.uid] = {"rin": actor}
    before = graph.value_hash()
    fragments = compose_dialog_markup(
        caller=block, ctx=ctx, fragments=[ContentFragment(content=block.content)],
    )
    speaker = next(f for f in fragments if isinstance(f, AttributedFragment))
    assert speaker.speaker_name == "Rin"
    assert speaker.content == "This is my sister, Nanae."
    assert graph.value_hash() == before


@pytest.mark.parametrize("phase", [ResolutionPhase.PLANNING, ResolutionPhase.PREREQS, ResolutionPhase.POSTREQS])
def test_introduction_rejected_in_read_only_phases(ledger: Ledger, phase: ResolutionPhase) -> None:
    ctx = PhaseCtx(graph=ledger.graph, cursor_id=ledger.cursor_id, current_phase=phase)
    actor = ctx.get_ns(ctx.cursor)["host"]
    before = ledger.graph.value_hash()
    with pytest.raises(RuntimeError, match="UPDATE/FINALIZE"):
        NamingOperations(ctx).introduce(actor)
    assert ledger.graph.value_hash() == before


def test_jinja_and_semantic_references_share_policy_and_generated_text_is_literal(
    ledger: Ledger,
) -> None:
    from tangl.prose import MuBlock
    from tangl.prose.mu_block import ConceptReference
    from tangl.prose.naming import ProseBlock

    block = ledger.graph.find_one(Selector(has_kind=ProseBlock, label="introduction"))
    block.prose = [
        MuBlock(template="{{ reference(host) }} / {{ introduce(host) }} / {{ reference(host) }}"),
        MuBlock(text=[ConceptReference(ref="host", intent="anonymous"), " / ",
                          ConceptReference(ref="host")]),
    ]
    meet(ledger)
    texts = [getattr(fragment, "content", "") for fragment in ledger.get_journal()]
    assert "the blonde girl / Rin / Rin" in texts
    assert "the blonde girl / Rin" in texts


def test_linked_labels_reject_introductions_without_disclosure(ledger: Ledger) -> None:
    from tangl.prose.mu_block import ConceptReference

    ctx = PhaseCtx(graph=ledger.graph, cursor_id=ledger.cursor_id)
    actor = ctx.get_ns(ctx.cursor)["host"]
    with pytest.raises(ValueError, match="display label"):
        NamingOperations(ctx).realize([ConceptReference(ref="host", introduce=True)])
    assert actor.narrator_knowledge == {}


def test_template_generated_wording_is_not_executed_again(ledger: Ledger) -> None:
    from tangl.prose import MuBlock
    from tangl.prose.naming import ProseBlock

    actor = ledger.graph.find_one(Selector(has_kind=Actor, label="rin"))
    actor.name = "{{ introduce(host) }}"
    block = ledger.graph.find_one(Selector(has_kind=ProseBlock, label="introduction"))
    block.prose = [MuBlock(template="{{ reference(host, 'proper') }}")]
    meet(ledger)
    assert actor.narrator_knowledge == {}
    assert any(getattr(fragment, "content", "") == "{{ introduce(host) }}"
               for fragment in ledger.get_journal())


def test_nearest_kind_default_and_world_text_aspect_override(ledger: Ledger) -> None:
    from tangl.core import BehaviorRegistry, DispatchLayer, Priority

    actor = ledger.graph.find_one(Selector(has_kind=Actor, label="rin"))
    ctx = PhaseCtx(graph=ledger.graph, cursor_id=ledger.cursor_id)
    ns = ctx.get_ns(ctx.cursor)
    ns["naming_defaults"] = {"NamedActor": "proper", "Actor": "concealed"}
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


def test_fresh_vanilla_story_does_not_import_optional_naming() -> None:
    code = """
import sys
from tangl.story import Actor, Location, World
world = World.from_script_data(script_data={
    'label': 'vanilla_import_control',
    'metadata': {'start_at': 's.start'},
    'scenes': {'s': {'blocks': {'start': {'content': 'Rin #intro stays literal.'}}}},
})
world.create_story('vanilla_import_control')
assert 'tangl.prose.naming' not in sys.modules
assert 'personal_name' not in Actor.model_fields
assert 'anonymous_name' not in Location.model_fields
"""
    subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
