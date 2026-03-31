from __future__ import annotations

from uuid import UUID

import pytest

from tangl.persistence import PersistenceManagerFactory
from tangl.renpy import RenPyChoice, RenPySessionBridge
from tangl.service import build_service_manager
from tangl.story.fabula.world import World


@pytest.fixture(autouse=True)
def reset_worlds() -> None:
    World.clear_instances()
    yield
    World.clear_instances()


def _service_manager():
    persistence = PersistenceManagerFactory.create_persistence_manager(
        manager_name="native_in_mem"
    )
    return build_service_manager(persistence)


def _choice_by_text(choices: list[RenPyChoice], text: str) -> UUID:
    return next(choice.choice_id for choice in choices if choice.text == text)


def test_renpy_demo_start_turn_has_background_and_intro_choice() -> None:
    bridge = RenPySessionBridge(service_manager=_service_manager())

    envelope = bridge.start("renpy_demo")
    turns = bridge.build_turns(envelope.fragments)

    assert len(turns) == 1
    turn = turns[0]
    assert any(op.role == "narrative_im" for op in turn.media_ops)
    assert any("Rain drums against the inn windows" in line.text for line in turn.lines)
    assert [choice.text for choice in turn.choices] == ["Approach the waiting guide"]


def test_renpy_demo_walks_lantern_road_branch() -> None:
    bridge = RenPySessionBridge(service_manager=_service_manager())

    start_turn = bridge.build_turns(bridge.start("renpy_demo").fragments)[0]
    guide_envelope = bridge.choose(
        _choice_by_text(start_turn.choices, "Approach the waiting guide")
    )
    guide_turn = bridge.build_turns(guide_envelope.fragments)[0]

    assert any(op.role == "dialog_im" for op in guide_turn.media_ops)
    assert any(line.speaker == "Guide" for line in guide_turn.lines)
    assert any("You're right on time." in line.text for line in guide_turn.lines)

    final_envelope = bridge.choose(_choice_by_text(guide_turn.choices, "Take the lantern road"))
    final_turn = bridge.build_turns(final_envelope.fragments)[0]

    assert any("You choose the lantern road." in line.text for line in final_turn.lines)
    assert final_turn.choices == []


def test_renpy_demo_walks_river_path_branch() -> None:
    bridge = RenPySessionBridge(service_manager=_service_manager())

    start_turn = bridge.build_turns(bridge.start("renpy_demo").fragments)[0]
    guide_envelope = bridge.choose(
        _choice_by_text(start_turn.choices, "Approach the waiting guide")
    )
    guide_turn = bridge.build_turns(guide_envelope.fragments)[0]

    final_envelope = bridge.choose(_choice_by_text(guide_turn.choices, "Risk the river path"))
    final_turn = bridge.build_turns(final_envelope.fragments)[0]

    assert any("You gamble on the river path." in line.text for line in final_turn.lines)
    assert final_turn.choices == []
