"""Exact lexical adoption, scoped role dereferencing, and durable ledger output."""
from collections.abc import Iterator
from copy import deepcopy
from pathlib import Path
import subprocess
import sys
from typing import Any

import pytest
import yaml

from tangl.core import Selector
from tangl.journal.fragments import AttributedFragment, ContentFragment
from tangl.loaders import WorldBundle
from tangl.loaders.compiler import WorldCompiler
from tangl.prose.linking import lower_linked_prose
from tangl.prose.naming import BindingReference, NamingOperations, NamingPolicy, ProseBlock
from tangl.story import Actor, InitMode, World
from tangl.vm import Ledger, Requirement
from tangl.vm.replay import CheckpointRecord, Patch, get_replay_engine
from tangl.vm.runtime.frame import PhaseCtx


@pytest.fixture
def ledger() -> Iterator[Ledger]:
    World.clear_instances()
    bundle = WorldBundle.load(Path(__file__).resolve().parents[3] / "worlds/concept_linking_demo")
    world = WorldCompiler().compile(bundle)
    assert world.bundle.issues == []
    graph = world.create_story("concept_linking_demo", init_mode=InitMode.EAGER).graph
    yield Ledger.from_graph(graph, entry_id=graph.initial_cursor_id)
    World.clear_instances()


def choose(ledger: Ledger) -> None:
    ledger.resolve_choice(next(ledger.cursor.edges_out()).uid)


def contents(ledger: Ledger) -> list[str]:
    return [f.content for f in ledger.get_journal() if isinstance(f, ContentFragment)]


def test_world_links_roles_and_orders_provider_knowledge(ledger: Ledger) -> None:
    assert ledger.cursor.content == "Rin waits. No lexical consent here."
    before = ledger.graph.value_hash()
    block = ledger.graph.find_one(Selector(label="introduction", has_kind=ProseBlock))
    part = next(p for p in block.prose[0].text if not isinstance(p, str))
    assert part.ref == BindingReference(scope="meeting", label="host")
    ctx = PhaseCtx(graph=ledger.graph, cursor_id=block.uid)
    assert NamingOperations(ctx).realize(block.prose[0].text) == "the blonde girl approaches at Market Square."
    assert ledger.graph.value_hash() == before
    choose(ledger)
    texts = contents(ledger)
    assert "the blonde girl approaches at Market Square." in texts
    assert "This is my sister, Nanae. Rin #intro." in texts
    assert "Rin smiles. Rin waves." in texts
    assert "The blonde girl waits; the blonde girl watches Ringo." in texts
    assert "Rin #intro stays literal here." in texts
    assert "Explicit template: Rin." in texts
    speakers = [f.speaker_name for f in ledger.get_journal() if isinstance(f, AttributedFragment)]
    assert speakers == ["the blonde girl", "Rin"]
    assert ledger.graph.find_one(Selector(label="nanae", has_kind=Actor)).peek_knowledge() is None


def test_same_compiled_link_follows_recast_and_never_inherits_knowledge(ledger: Ledger) -> None:
    choose(ledger)
    ctx = PhaseCtx(graph=ledger.graph, cursor_id=ledger.cursor_id)
    role = ctx.get_ns(ctx.cursor)["host_role"]
    assert role.narrator_knowledge == {}
    nanae = ledger.graph.find_one(Selector(label="nanae", has_kind=Actor))
    block = ledger.cursor
    compiled = deepcopy(block.prose)
    role.requirement = Requirement(has_kind=Actor)
    role.set_provider(nanae)
    assert NamingOperations(ctx).realize(block.prose[0].text) == "the brunette girl approaches at Market Square."
    assert nanae.peek_knowledge() is None
    restored = Ledger.structure(ledger.unstructure())
    restored_ctx = PhaseCtx(graph=restored.graph, cursor_id=restored.cursor_id)
    assert NamingOperations(restored_ctx).realize(restored.cursor.prose[0].text) == "the brunette girl approaches at Market Square."
    choose(ledger)
    assert contents(ledger)[-1] == "the brunette girl greets you."
    choose(ledger)
    assert "Nanae smiles. Nanae waves." in contents(ledger)
    assert nanae.peek_knowledge().state == "IDENTIFIED"
    assert ledger.cursor.prose == compiled


def test_unbound_nearer_role_does_not_fall_through_to_outer_provider(ledger: Ledger) -> None:
    block = ledger.graph.find_one(Selector(label="shadow", has_kind=ProseBlock))
    ctx = PhaseCtx(graph=ledger.graph, cursor_id=block.uid)
    role = ctx.get_ns(block)["role_edges"]["host"]
    role.set_provider(None)
    ctx = PhaseCtx(graph=ledger.graph, cursor_id=block.uid)
    assert ctx.get_ns(block)["host"].name == "Rin"  # Existing provider-symbol fallback.
    assert NamingOperations(ctx).resolve(BindingReference(scope="meeting.shadow", label="host")) is role
    with pytest.raises(TypeError, match="bound actor/place"):
        NamingOperations(ctx).realize(block.prose[0].text)
    with pytest.raises(LookupError, match="outside the current scope"):
        NamingOperations(ctx).resolve(BindingReference(scope="meeting", label="host"))


def test_reference_environment_roundtrip_preserves_full_nominal_and_whitespace(ledger: Ledger) -> None:
    block = ledger.graph.find_one(Selector(label="introduction", has_kind=ProseBlock))
    ctx = PhaseCtx(graph=ledger.graph, cursor_id=block.uid)
    rin = ctx.get_ns(block)["host"]
    rin.naming_policy = NamingPolicy.PROPER
    before = ledger.graph.value_hash()
    assert NamingOperations(ctx).realize(block.prose[0].text) == "Rin approaches at Market Square."
    assert NamingOperations(ctx).realize(block.prose[4].text) == "The blonde girl waits; the blonde girl watches Ringo."
    assert rin.peek_knowledge() is None
    assert ledger.graph.value_hash() == before


def source() -> dict[str, Any]:
    return {
        "label": "test_links", "link_prose": True,
        "actors": {"rin": {"kind": "NamingActor", "name": "Rin", "anonymous_name": "the girl"},
                   "nanae": {"kind": "NamingActor", "name": "Nanae", "anonymous_name": "the woman"}},
        "scenes": {"scene": {"roles": {"host": {"actor_ref": "rin"}},
                              "blocks": {"start": {"content": "Rin, Ringo; the girl."}}}},
    }


def test_scope_shadowing_source_preservation_and_distinct_scene_links() -> None:
    data = source()
    blocks = data["scenes"]["scene"]["blocks"]
    blocks["near"] = {"roles": {"host": {"actor_ref": "nanae"}}, "content": "Nanae Rin host."}
    data["scenes"]["other"] = {"roles": {"host": {"actor_ref": "rin"}},
                                  "blocks": {"start": {"content": "Rin"}}}
    original = deepcopy(data)
    result = lower_linked_prose(data)
    assert data == original
    parts = result["scenes"]["scene"]["blocks"]["start"]["prose"][0]["text"]
    assert parts[0] == ""
    assert ", Ringo; " in parts
    assert parts[3]["intent"] == "anonymous"
    near = result["scenes"]["scene"]["blocks"]["near"]["prose"][0]["text"]
    assert near[1]["ref"]["scope"] == "scene.near"
    assert " Rin " in near
    other = result["scenes"]["other"]["blocks"]["start"]["prose"][0]["text"]
    assert other[1]["ref"]["scope"] == "other"


def test_ambiguity_is_source_attributed_and_longest_spelling_wins() -> None:
    data = source()
    scene = data["scenes"]["scene"]
    scene["roles"]["second"] = {"actor_ref": "rin"}
    with pytest.raises(ValueError, match=r"script:scene.start.prose\[0\]:0: ambiguous.*scene:host.*scene:second"):
        lower_linked_prose(data)
    scene["link_forms"] = {"second": {"proper": "Rin Senior", "anonymous": "the elder"}}
    scene["blocks"]["start"]["content"] = "Rin Senior\tmet Rin."
    result = lower_linked_prose(data)
    parts = result["scenes"]["scene"]["blocks"]["start"]["prose"][0]["text"]
    assert parts[1]["ref"]["label"] == "second"
    assert parts[2] == "\tmet "
    assert parts[3]["ref"]["label"] == "host"


def test_raw_optout_templates_and_escapes_are_not_lexically_interpreted() -> None:
    data = source()
    blocks = data["scenes"]["scene"]["blocks"]
    blocks["start"]["link_prose"] = False
    blocks["jinja"] = {"content": "Rin {{ 'Rin #intro' }} {% set Rin = 1 %}"}
    blocks["escaped"] = {"content": r"\Rin #intro meets Rin."}
    result = lower_linked_prose(data)
    assert result["scenes"]["scene"]["blocks"]["start"]["content"] == "Rin, Ringo; the girl."
    assert result["scenes"]["scene"]["blocks"]["jinja"] == blocks["jinja"]
    parts = result["scenes"]["scene"]["blocks"]["escaped"]["prose"][0]["text"]
    assert "Rin #intro" in parts
    assert parts[3]["introduce"] is False
    blocks["bad"] = {"content": "Unknown #intro"}
    with pytest.raises(ValueError, match="unmatched #intro"):
        lower_linked_prose(data)


def test_scene_optout_and_nearer_block_optin_and_explicit_templates() -> None:
    data = source()
    scene = data["scenes"]["scene"]
    scene["link_prose"] = False
    scene["blocks"]["literal"] = {"prose": [{"text": "Rin #intro {{ literal }}"}]}
    template = "{{ 'Rin #intro' }} {% set Rin = 'Rin' %} {# Rin #intro #}"
    scene["blocks"]["opted"] = {
        "link_prose": True,
        "prose": [{"template": template}, {"text": "Rin#intro greets Rin."}],
    }
    result = lower_linked_prose(data)
    blocks = result["scenes"]["scene"]["blocks"]
    assert blocks["start"]["content"] == scene["blocks"]["start"]["content"]
    assert blocks["literal"]["prose"][0]["text"] == ["Rin #intro {{ literal }}"]
    assert blocks["opted"]["prose"][0] == {"template": template}
    assert blocks["opted"]["prose"][1]["text"][1]["introduce"] is True
    # The lowered source is plain YAML data; no codec-specific serializer is needed.
    assert yaml.safe_load(yaml.safe_dump(result)) == result


def test_custom_block_kind_is_preserved_or_explicitly_rejected() -> None:
    from tangl.story import Block

    class LinkedCustomBlock(ProseBlock):
        badge: str = ""

    class UnrelatedCustomBlock(Block):
        badge: str = ""

    data = source()
    block = data["scenes"]["scene"]["blocks"]["start"]
    block.update(kind="LinkedCustomBlock", badge="keep me")
    registry = {"LinkedCustomBlock": LinkedCustomBlock,
                "UnrelatedCustomBlock": UnrelatedCustomBlock}
    result = lower_linked_prose(data, class_registry=registry)
    assert result["scenes"]["scene"]["blocks"]["start"]["kind"] == "LinkedCustomBlock"
    assert result["scenes"]["scene"]["blocks"]["start"]["badge"] == "keep me"
    block["kind"] = "UnrelatedCustomBlock"
    with pytest.raises(ValueError, match="custom block kind must inherit ProseBlock"):
        lower_linked_prose(data, class_registry=registry)


def test_unavailable_adoption_and_duplicate_declarations_are_attributed() -> None:
    data = source()
    data["link_forms"] = {"missing": {"proper": "Rin"}}
    with pytest.raises(ValueError, match="script:scene.start: unavailable.*missing"):
        lower_linked_prose(data)
    data.pop("link_forms")
    data["scenes"]["scene"]["roles"] = [
        {"label": "host", "actor_ref": "rin"}, {"label": "host", "actor_ref": "nanae"},
    ]
    with pytest.raises(ValueError, match="script:scene: duplicate role_edges.*host"):
        lower_linked_prose(data)


def test_scoped_template_supplies_spelling_without_becoming_the_durable_link() -> None:
    data = source()
    scene = data["scenes"]["scene"]
    scene["templates"] = {"guest": {"kind": "NamingActor", "name": "Guest", "anonymous_name": "a guest"}}
    scene["roles"] = {"host": {"actor_template_ref": "scene.guest"}}
    scene["blocks"]["start"]["content"] = "Guest and a guest."
    parts = lower_linked_prose(data)["scenes"]["scene"]["blocks"]["start"]["prose"][0]["text"]
    assert parts[1]["ref"] == {"scope": "scene", "label": "host", "collection": "role_edges"}
    assert parts[3]["intent"] == "anonymous"


def test_constructor_restore_replay_and_actual_internal_return(ledger: Ledger) -> None:
    choose(ledger)
    historical = [f.unstructure() for f in ledger.get_journal()]
    restored = Ledger.structure(ledger.unstructure())
    assert [f.unstructure() for f in restored.get_journal()] == historical
    engine = get_replay_engine(restored.replay_algorithm_id)
    checkpoint = next(Selector(has_kind=CheckpointRecord).filter(restored.output_stream))
    replayed = engine.restore_checkpoint(checkpoint)
    for patch in Selector(has_kind=Patch).filter(restored.output_stream):
        replayed = engine.apply_delta(graph=replayed, delta=patch)
    ctx = PhaseCtx(graph=replayed, cursor_id=restored.cursor_id)
    assert NamingOperations(ctx).realize(ctx.cursor.prose[0].text) == "Rin approaches at Market Square."
    choose(restored)
    choose(restored)
    assert contents(restored).count("Rin smiles. Rin waves.") == 2
    restored.rollback_to_step(0)
    choose(restored)
    assert contents(restored).count("Rin smiles. Rin waves.") == 1
    assert contents(restored).count("the blonde girl approaches at Market Square.") == 1


def test_normal_yaml_export_retains_symbolic_references_without_a_custom_serializer(
    ledger: Ledger,
) -> None:
    from tangl.story.fabula import StoryCompiler

    bundle = WorldBundle.load(Path(__file__).resolve().parents[3] / "worlds/concept_linking_demo")
    before = ledger.graph.value_hash()
    encoded = WorldCompiler().encode(bundle, ledger.graph.world.bundle)
    data = yaml.safe_load(encoded.artifacts["script.yaml"])
    lowered = lower_linked_prose(data)
    recompiled = StoryCompiler().compile(lowered)
    assert recompiled.issues == []
    block = recompiled.template_registry.find_one(Selector(label="meeting.introduction")).payload
    ref = next(p for p in block.prose[0].text if not isinstance(p, str))
    assert ref.ref == BindingReference(scope="meeting", label="host")
    assert ledger.graph.value_hash() == before


def test_json_restore_in_cold_process_bootstraps_symbolic_links(ledger: Ledger, tmp_path: Path) -> None:
    from tangl.persistence import PersistenceManagerFactory
    from tangl.service import ServiceManager
    from tangl.service.response import DirectEdgeRequest
    from tangl.service.user.user import User

    persistence = PersistenceManagerFactory.json_file(base_path=tmp_path)
    manager = ServiceManager(persistence)
    user = User(label="linking-reader")
    persistence.save(user)
    manager.create_story(user_id=user.uid, world_id=ledger.graph.world.label,
                         world=ledger.graph.world, init_mode=InitMode.EAGER.value)
    with manager.open_session(user_id=user.uid) as session:
        edge = next(session.ledger.cursor.edges_out())
    manager.resolve_choice(user_id=user.uid, request=DirectEdgeRequest(edge_id=edge.uid))
    code = """
from pathlib import Path
import sys
from uuid import UUID
from tangl.persistence import PersistenceManagerFactory
from tangl.service import ServiceManager
from tangl.service.response import DirectEdgeRequest
from tangl.prose.naming import NamingOperations, BindingReference
from tangl.vm.runtime.frame import PhaseCtx
from tangl.story import World
assert World.get_instance('concept_linking_demo') is None
manager = ServiceManager(PersistenceManagerFactory.json_file(base_path=Path(sys.argv[1])))
manager.open_world('concept_linking_demo')
with manager.open_session(user_id=UUID(sys.argv[2])) as session:
    ledger = session.ledger
    before = [f.unstructure() for f in ledger.get_journal()]
    ctx = PhaseCtx(graph=ledger.graph, cursor_id=ledger.cursor_id)
    part = next(p for p in ctx.cursor.prose[0].text if not isinstance(p, str))
    assert part.ref == BindingReference(scope='meeting', label='host')
    assert NamingOperations(ctx).realize(ctx.cursor.prose[0].text) == 'Rin approaches at Market Square.'
    edge = next(ledger.cursor.edges_out())
result = manager.resolve_choice(user_id=UUID(sys.argv[2]), request=DirectEdgeRequest(edge_id=edge.uid))
assert any(getattr(f, 'content', '') == 'the brunette girl greets you.' for f in result.fragments)
with manager.open_session(user_id=UUID(sys.argv[2])) as session:
    after = [f.unstructure() for f in session.ledger.get_journal()]
    assert after[:len(before)] == before
print('cold symbolic restore passed')
"""
    completed = subprocess.run([sys.executable, "-c", code, str(tmp_path), str(user.uid)],
                               capture_output=True, text=True, check=True)
    assert "cold symbolic restore passed" in completed.stdout
