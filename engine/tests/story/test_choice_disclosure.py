"""Story policy for showing unavailable choices without changing availability."""

from __future__ import annotations

import pytest

from tangl.core import Selector
from tangl.ir.story_ir.choice_disclosure import UnavailableChoiceDisclosure
from tangl.journal.fragments import ChoiceFragment
from tangl.presentation.intent import Blocker
from tangl.story import InitMode
from tangl.story.episode import Action
from tangl.story.fabula.world import World
from tangl.story.system_handlers import render_block_choices
from tangl.vm import Ledger
from tangl.vm.runtime.frame import PhaseCtx


def _script(
    *,
    world_policy: str | None = None,
    scene_policy: str | None = None,
    block_policy: str | None = None,
    action_policy: str | None = None,
) -> dict:
    locals_: dict[str, str] = {}
    if world_policy is not None:
        locals_["unavailable_choice_disclosure"] = world_policy
    scene_locals: dict[str, str] = {}
    if scene_policy is not None:
        scene_locals["unavailable_choice_disclosure"] = scene_policy
    block_locals: dict[str, str] = {}
    if block_policy is not None:
        block_locals["unavailable_choice_disclosure"] = block_policy

    return {
        "label": "choice_disclosure_world",
        "locals": locals_,
        "metadata": {"title": "Choice disclosure", "start_at": "s.start"},
        "scenes": {
            "s": {
                "locals": scene_locals,
                "blocks": {
                    "start": {
                        "content": "Start.",
                        "locals": block_locals,
                        "actions": [
                            {
                                "text": "Hidden lock",
                                "successor": "locked",
                                "conditions": ["False"],
                                "blockers": [
                                    {"code": "locked", "message": "The lock will not turn."},
                                ],
                                **(
                                    {"unavailable_choice_disclosure": action_policy}
                                    if action_policy is not None
                                    else {}
                                ),
                            },
                            {
                                "text": "Always available",
                                "successor": "open",
                            },
                        ],
                    },
                    "locked": {"content": "Locked."},
                    "open": {"content": "Open."},
                },
            },
        },
    }


def _graph(**policies):
    world = World.from_script_data(script_data=_script(**policies))
    return world.create_story("choice_disclosure_story", init_mode=InitMode.EAGER).graph


def _node(graph, label: str):
    return next(node for node in graph.find_nodes(Selector()) if node.get_label() == label)


def _choices(graph) -> list[ChoiceFragment]:
    start = _node(graph, "start")
    return list(render_block_choices(caller=start, ctx=PhaseCtx(graph=graph, cursor_id=start.uid)) or [])


def _action(graph, text: str) -> Action:
    return next(
        edge
        for edge in _node(graph, "start").edges_out(Selector(has_kind=Action))
        if edge.text == text
    )


def test_default_discloses_unavailable_choice_with_authored_blocker() -> None:
    choices = _choices(_graph())

    locked = next(choice for choice in choices if choice.text == "Hidden lock")
    assert locked.available is False
    assert locked.unavailable_reason == "locked"
    assert locked.blockers == [Blocker(code="locked", message="The lock will not turn.")]


@pytest.mark.parametrize(
    ("policies", "expected_locked"),
    [
        ({"world_policy": "hide"}, False),
        ({"world_policy": "hide", "scene_policy": "disclose"}, True),
        ({"world_policy": "disclose", "scene_policy": "hide", "block_policy": "disclose"}, True),
        ({"world_policy": "disclose", "action_policy": "hide"}, False),
        ({"world_policy": "hide", "action_policy": "disclose"}, True),
    ],
)
def test_scoped_and_action_policy_control_only_unavailable_disclosure(
    policies: dict[str, str], expected_locked: bool
) -> None:
    choices = _choices(_graph(**policies))

    assert ("Hidden lock" in {choice.text for choice in choices}) is expected_locked
    assert "Always available" in {choice.text for choice in choices}


def test_authored_action_override_is_typed_and_materialized() -> None:
    action = _action(_graph(action_policy="HIDE"), "Hidden lock")

    assert action.unavailable_choice_disclosure is UnavailableChoiceDisclosure.HIDE


def test_hidden_unavailable_choice_still_rejects_direct_selection() -> None:
    graph = _graph(world_policy="hide")
    hidden = _action(graph, "Hidden lock")
    ledger = Ledger.from_graph(graph=graph, entry_id=_node(graph, "start").uid)

    assert all(choice.edge_id != hidden.uid for choice in _choices(graph))
    with pytest.raises(ValueError, match="Edge validation failed"):
        ledger.resolve_choice(hidden.uid)


def test_a_hidden_choice_its_guard_refuses_is_not_asked_why(monkeypatch) -> None:
    # Working out why a choice is unavailable previews its destination, which is
    # the costly part of rendering a menu. A hidden choice needs no reason.
    from tangl.story import system_handlers

    asked: list[str] = []
    reason = system_handlers._choice_unavailable_reason

    def spy(*, edge, ctx):
        asked.append(edge.text)
        return reason(edge=edge, ctx=ctx)

    monkeypatch.setattr(system_handlers, "_choice_unavailable_reason", spy)
    choices = _choices(_graph(world_policy="hide"))

    assert asked == ["Always available"]
    assert [choice.text for choice in choices] == ["Always available"]
