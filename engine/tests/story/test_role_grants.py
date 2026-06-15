"""Contract tests for provider-bound role grants (mu-affordances, phase 1).

Covers grant materialization on an active binding, scope visibility, automatic
removal/swap when the binding changes, and deterministic multi-binding
precedence. See ``docs/src/notes/MU_AFFORDANCES.md`` and issue #141.
"""

from __future__ import annotations

from tangl.story import InitMode, World
from tangl.story.concepts import Actor, Role, RoleGrant
from tangl.story.episode import Block, Scene
from tangl.story.story_graph import StoryGraph
from tangl.vm import Requirement
from tangl.vm.runtime.frame import PhaseCtx


def _build_scene_with_block() -> tuple[StoryGraph, Scene, Block]:
    graph = StoryGraph(label="grant_story")
    scene = Scene(label="scene")
    block = Block(label="block")
    graph.add(scene)
    graph.add(block)
    scene.add_child(block)
    return graph, scene, block


def _gather(graph: StoryGraph, block: Block) -> dict:
    """Gather a fresh scoped namespace (a new ctx avoids per-ctx ns caching)."""
    return PhaseCtx(graph=graph, cursor_id=block.uid).get_ns(block)


def _role(label: str, predecessor: object, **kwargs) -> Role:
    return Role(
        label=label,
        predecessor_id=predecessor.uid,
        requirement=Requirement(has_kind=Actor, hard_requirement=False),
        **kwargs,
    )


# ---------------------------------------------------------------------------
# RoleGrant authoring shape
# ---------------------------------------------------------------------------


def test_role_grant_folds_flat_authoring_into_locals_and_tags() -> None:
    grant = RoleGrant.model_validate({"title": "boss", "rank": 3, "tags": ["mgmt"], "priority": 2})

    assert grant.locals == {"title": "boss", "rank": 3}
    assert grant.tags == {"mgmt"}
    assert grant.priority == 2
    assert not grant.is_empty


def test_role_grant_accepts_structured_authoring() -> None:
    grant = RoleGrant.model_validate({"locals": {"title": "boss"}, "tags": ["a", "b"]})

    assert grant.locals == {"title": "boss"}
    assert grant.tags == {"a", "b"}
    assert RoleGrant().is_empty


# ---------------------------------------------------------------------------
# Materialization on an active binding
# ---------------------------------------------------------------------------


def test_grant_projects_onto_bound_provider() -> None:
    graph, scene, block = _build_scene_with_block()
    actor = Actor(label="joe", name="Joe")
    graph.add(actor)
    role = _role("boss", scene, grants={"title": "boss", "tags": ["management"]})
    graph.add(role)
    role.set_provider(actor)

    ns = _gather(graph, block)

    # Label-scoped projection rides alongside the existing provider symbols.
    assert ns["boss"] is actor
    assert ns["boss_title"] == "boss"
    assert ns["boss_tags"] == {"management"}
    # Canonical per-binding accessor and merged scope views.
    assert ns["role_grants"]["boss"].locals == {"title": "boss"}
    assert ns["grants"] == {"title": "boss"}
    assert ns["grant_tags"] == {"management"}


def test_grant_overrides_same_named_provider_symbol() -> None:
    graph, scene, block = _build_scene_with_block()
    actor = Actor(label="joe", name="Joe")
    graph.add(actor)
    role = _role("boss", scene, grants={"name": "The Boss"})
    graph.add(role)
    role.set_provider(actor)

    ns = _gather(graph, block)

    # Grant is layered after provider.get_ns(), so it wins for a shared key.
    assert ns["boss_name"] == "The Boss"


def test_unbound_role_contributes_no_grant() -> None:
    graph, scene, block = _build_scene_with_block()
    role = _role("boss", scene, grants={"title": "boss"})
    graph.add(role)  # never bound

    ns = _gather(graph, block)

    assert "boss_title" not in ns
    assert "grants" not in ns
    assert "role_grants" not in ns


def test_role_without_grants_projects_nothing_extra() -> None:
    graph, scene, block = _build_scene_with_block()
    actor = Actor(label="joe", name="Joe")
    graph.add(actor)
    role = _role("boss", scene)
    graph.add(role)
    role.set_provider(actor)

    ns = _gather(graph, block)

    assert ns["boss"] is actor
    assert "boss_title" not in ns
    assert "grants" not in ns
    assert "grant_tags" not in ns


# ---------------------------------------------------------------------------
# Rebinding / unbinding update the derived grants automatically
# ---------------------------------------------------------------------------


def test_grant_follows_swapped_provider() -> None:
    graph, scene, block = _build_scene_with_block()
    actor_a = Actor(label="amy", name="Amy")
    actor_b = Actor(label="ben", name="Ben")
    graph.add(actor_a)
    graph.add(actor_b)
    role = _role("boss", scene, grants={"title": "boss"})
    graph.add(role)

    role.set_provider(actor_a)
    ns_a = _gather(graph, block)
    assert ns_a["boss"] is actor_a
    assert ns_a["boss_title"] == "boss"

    role.set_provider(actor_b)
    ns_b = _gather(graph, block)
    # The overlay moves with the binding: it now decorates Ben, not Amy.
    assert ns_b["boss"] is actor_b
    assert ns_b["boss_title"] == "boss"
    # Nothing was stamped onto the provider itself.
    assert "title" not in actor_a.get_ns()


def test_grant_disappears_when_binding_cleared() -> None:
    graph, scene, block = _build_scene_with_block()
    actor = Actor(label="joe", name="Joe")
    graph.add(actor)
    role = _role("boss", scene, grants={"title": "boss", "tags": ["mgmt"]})
    graph.add(role)

    role.set_provider(actor)
    assert _gather(graph, block)["boss_title"] == "boss"

    role.set_provider(None)
    ns = _gather(graph, block)
    assert "boss_title" not in ns
    assert "boss_tags" not in ns
    assert "grants" not in ns
    assert "grant_tags" not in ns


# ---------------------------------------------------------------------------
# Multi-binding precedence
# ---------------------------------------------------------------------------


def test_merged_grants_resolve_same_key_by_priority() -> None:
    graph, scene, block = _build_scene_with_block()
    captain = Actor(label="cap", name="Cap")
    deputy = Actor(label="dep", name="Dep")
    graph.add(captain)
    graph.add(deputy)

    role_high = _role("captain", scene, grants={"clearance": "high", "priority": 10})
    role_low = _role("deputy", scene, grants={"clearance": "low", "priority": 1})
    graph.add(role_high)
    graph.add(role_low)
    role_high.set_provider(captain)
    role_low.set_provider(deputy)

    ns = _gather(graph, block)

    # Same merged key -> higher priority wins; label-scoped keys stay distinct.
    assert ns["grants"]["clearance"] == "high"
    assert ns["captain_clearance"] == "high"
    assert ns["deputy_clearance"] == "low"


def test_merged_grant_tags_union_across_bindings() -> None:
    graph, scene, block = _build_scene_with_block()
    a = Actor(label="a", name="A")
    b = Actor(label="b", name="B")
    graph.add(a)
    graph.add(b)

    role_a = _role("alpha", scene, grants={"tags": ["x"]})
    role_b = _role("beta", scene, grants={"tags": ["y"]})
    graph.add(role_a)
    graph.add(role_b)
    role_a.set_provider(a)
    role_b.set_provider(b)

    ns = _gather(graph, block)

    assert ns["grant_tags"] == {"x", "y"}


def test_nearer_scope_grant_overrides_parent_scope() -> None:
    graph, scene, block = _build_scene_with_block()
    scene_actor = Actor(label="scene_boss", name="Scene Boss")
    block_actor = Actor(label="block_boss", name="Block Boss")
    graph.add(scene_actor)
    graph.add(block_actor)

    scene_role = _role("boss", scene, grants={"title": "scene-boss"})
    block_role = _role("boss", block, grants={"title": "block-boss"})
    graph.add(scene_role)
    graph.add(block_role)
    scene_role.set_provider(scene_actor)
    block_role.set_provider(block_actor)

    ns = _gather(graph, block)

    # Nearer (block) binding wins for the shared label.
    assert ns["boss"] is block_actor
    assert ns["boss_title"] == "block-boss"
    assert ns["role_grants"]["boss"].locals == {"title": "block-boss"}
    assert ns["grants"]["title"] == "block-boss"


def test_nearer_scope_role_without_grant_clears_parent_grant() -> None:
    graph, scene, block = _build_scene_with_block()
    scene_actor = Actor(label="scene_boss", name="Scene Boss")
    block_actor = Actor(label="block_boss", name="Block Boss")
    graph.add(scene_actor)
    graph.add(block_actor)

    scene_role = _role("boss", scene, grants={"title": "scene-boss"})
    block_role = _role("boss", block)  # nearer binding, no grant
    graph.add(scene_role)
    graph.add(block_role)
    scene_role.set_provider(scene_actor)
    block_role.set_provider(block_actor)

    ns = _gather(graph, block)

    assert ns["boss"] is block_actor
    assert "boss_title" not in ns
    assert "role_grants" not in ns
    assert "grants" not in ns


def test_nearer_scope_unbound_role_inherits_parent_provider_and_grant() -> None:
    # A nearer role that is *unbound* is an empty slot, not an override: the
    # parent's bound provider and its grant show through, mirroring provider-symbol
    # inheritance. (Contrast the bound case above, where the nearer binding does
    # override and clear.)
    graph, scene, block = _build_scene_with_block()
    scene_actor = Actor(label="scene_boss", name="Scene Boss")
    graph.add(scene_actor)

    scene_role = _role("boss", scene, grants={"title": "scene-boss"})
    block_role = _role("boss", block)  # nearer, unbound slot
    graph.add(scene_role)
    graph.add(block_role)
    scene_role.set_provider(scene_actor)

    ns = _gather(graph, block)

    assert ns["boss"] is scene_actor
    assert ns["boss_title"] == "scene-boss"
    assert ns["role_grants"]["boss"].locals == {"title": "scene-boss"}
    assert ns["grants"]["title"] == "scene-boss"


# ---------------------------------------------------------------------------
# Authoring round-trip through compile + materialize
# ---------------------------------------------------------------------------


def _grant_script() -> dict:
    return {
        "label": "grant_demo",
        "metadata": {"title": "Grant Demo", "start_at": "intro.start"},
        "actors": {
            "guard": {"name": "Joe", "kind": "tangl.story.concepts.actor.actor.Actor"},
        },
        "scenes": {
            "intro": {
                "blocks": {
                    "start": {
                        "content": "Start",
                        "roles": [
                            {
                                "label": "host",
                                "actor_ref": "guard",
                                "grants": {"title": "boss", "tags": ["management"]},
                            }
                        ],
                    },
                },
            }
        },
    }


def test_authored_grants_materialize_onto_role_binding() -> None:
    world = World.from_script_data(script_data=_grant_script())
    result = world.create_story("grant_run", init_mode=InitMode.EAGER)
    graph = result.graph

    from tangl.core import Selector

    role = next(iter(Selector(has_kind=Role).filter(graph.values())))
    assert role.grants is not None
    assert role.grants.locals == {"title": "boss"}
    assert role.grants.tags == {"management"}
    assert role.satisfied

    block = next(
        node
        for node in Selector(has_kind=Block).filter(graph.values())
        if node.get_label().endswith("start")
    )
    ns = PhaseCtx(graph=graph, cursor_id=block.uid).get_ns(block)
    assert ns["host_title"] == "boss"
    assert ns["host_tags"] == {"management"}
    assert ns["grants"] == {"title": "boss"}
