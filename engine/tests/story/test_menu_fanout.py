"""Story integration tests for menu fanout and planning-time action projection."""

from __future__ import annotations

from tangl.core import Selector
from tangl.story import InitMode, World
from tangl.story.episode import Action, Block
from tangl.story.fragments import ChoiceFragment
from tangl.vm import Fanout, Ledger
from tangl.vm.dispatch import do_journal, do_provision
from tangl.vm.runtime.frame import PhaseCtx


def _menu_script() -> dict:
    return {
        "label": "menu_story",
        "metadata": {
            "start_at": "lab.start",
        },
        "scenes": {
            "lab": {
                "blocks": [
                    {
                        "label": "start",
                        "content": "Start",
                        "actions": [{"text": "Enter lab", "successor": "hub"}],
                    },
                    {
                        "label": "hub",
                        "kind": "MenuBlock",
                        "content": "What should we do?",
                        "menu_items": {
                            "has_tags": ["activity"],
                            "return_when_done": True,
                        },
                    },
                    {
                        "label": "aria",
                        "tags": ["activity"],
                        "locals": {"action_text": "Listen to Aria"},
                        "content": "Aria tunes her harp.",
                    },
                    {
                        "label": "brew",
                        "tags": ["activity"],
                        "action_name": "Brew tea",
                        "content": "The kettle is ready.",
                    },
                    {
                        "label": "notes",
                        "tags": ["activity"],
                        "locals": {"menu_text": "Read the notes"},
                        "content": "The notes are scattered across the desk.",
                    },
                    {
                        "label": "archive",
                        "tags": ["activity"],
                        "content": "Shelves of old records line the wall.",
                    },
                    {
                        "tags": ["activity"],
                        "action_name": "Secret project",
                        "content": "A hidden prototype hums quietly in the corner.",
                    },
                ]
            }
        },
    }


def _create_story(script: dict | None = None, *, freeze_shape: bool = False):
    world = World.from_script_data(script_data=script or _menu_script())
    return world.create_story(
        "menu_story",
        init_mode=InitMode.EAGER,
        freeze_shape=freeze_shape,
    )


def _block(graph, label: str) -> Block:
    return next(Selector(has_kind=Block, label=label).filter(graph.values()))


def _dynamic_menu_actions(block: Block) -> list[Action]:
    return [
        edge
        for edge in block.edges_out(Selector(has_kind=Action, trigger_phase=None))
        if {"dynamic", "fanout", "menu"}.issubset(getattr(edge, "tags", set()) or set())
    ]


def _enter_hub(result):
    ledger = Ledger.from_graph(result.graph, entry_id=result.graph.initial_cursor_id)
    action = next(ledger.cursor.edges_out(Selector(has_kind=Action, trigger_phase=None)))
    ledger.resolve_choice(action.uid)
    hub = ledger.cursor
    assert isinstance(hub, Block)
    assert hub.label == "hub"
    return ledger, hub


def test_materialized_menu_block_wires_fanout_edges() -> None:
    result = _create_story()
    hub = _block(result.graph, "hub")

    fanouts = list(hub.edges_out(Selector(has_kind=Fanout)))

    assert len(fanouts) == 1
    assert fanouts[0].requirement.satisfied_by(_block(result.graph, "brew"))


def test_entering_menu_block_projects_dynamic_actions_during_planning() -> None:
    result = _create_story()
    _, hub = _enter_hub(result)

    actions = _dynamic_menu_actions(hub)

    assert len(actions) == 5
    assert all(action.return_phase is None for action in actions)
    assert {action.text for action in actions} >= {
        "Listen to Aria",
        "Brew tea",
        "Read the notes",
        "archive",
        "Secret project",
    }


def test_menu_choices_render_through_normal_block_journal_handler() -> None:
    result = _create_story()
    _, hub = _enter_hub(result)
    ctx = PhaseCtx(graph=result.graph, cursor_id=hub.uid)

    fragments = do_journal(hub, ctx=ctx)

    assert isinstance(fragments, list)
    choices = [fragment for fragment in fragments if isinstance(fragment, ChoiceFragment)]
    assert {choice.text for choice in choices} >= {
        "Listen to Aria",
        "Brew tea",
        "Read the notes",
        "archive",
        "Secret project",
    }


def test_anonymous_activity_block_can_be_gathered_as_menu_choice() -> None:
    result = _create_story()
    _, hub = _enter_hub(result)

    secret_action = next(action for action in _dynamic_menu_actions(hub) if action.text == "Secret project")

    assert secret_action.successor is not None
    assert getattr(secret_action.successor, "is_anonymous", False) is True


def test_menu_action_text_precedence_uses_provider_metadata() -> None:
    result = _create_story()
    _, hub = _enter_hub(result)

    texts = {action.text for action in _dynamic_menu_actions(hub)}

    assert "Listen to Aria" in texts
    assert "Brew tea" in texts
    assert "Read the notes" in texts
    assert "archive" in texts


def test_menu_refresh_rebuilds_actions_and_removes_stale_choices() -> None:
    result = _create_story()
    _, hub = _enter_hub(result)
    initial_actions = _dynamic_menu_actions(hub)
    initial_ids = {action.uid for action in initial_actions}

    brew = _block(result.graph, "brew")
    brew.tags.discard("activity")

    ctx = PhaseCtx(graph=result.graph, cursor_id=hub.uid)
    do_provision(hub, ctx=ctx)
    refreshed_actions = _dynamic_menu_actions(hub)

    assert "Brew tea" not in {action.text for action in refreshed_actions}
    assert initial_ids.isdisjoint({action.uid for action in refreshed_actions})
    assert len(refreshed_actions) == 4


def test_frozen_shape_eager_init_prebuilds_menu_actions() -> None:
    result = _create_story(freeze_shape=True)
    hub = _block(result.graph, "hub")

    actions = _dynamic_menu_actions(hub)

    assert result.graph.frozen_shape is True
    assert len(actions) == 5
    assert {action.text for action in actions} >= {
        "Listen to Aria",
        "Brew tea",
        "Read the notes",
        "archive",
        "Secret project",
    }


def test_frozen_shape_menu_does_not_refresh_during_planning() -> None:
    result = _create_story(freeze_shape=True)
    hub = _block(result.graph, "hub")
    initial_actions = _dynamic_menu_actions(hub)
    initial_ids = {action.uid for action in initial_actions}

    brew = _block(result.graph, "brew")
    brew.tags.discard("activity")

    ctx = PhaseCtx(graph=result.graph, cursor_id=hub.uid)
    do_provision(hub, ctx=ctx)
    refreshed_actions = _dynamic_menu_actions(hub)

    assert {action.uid for action in refreshed_actions} == initial_ids
    assert "Brew tea" in {action.text for action in refreshed_actions}
