"""Live-session tests for the pygame bridge against a real world bundle."""

from __future__ import annotations

from pathlib import Path

import pytest

from tangl.pygame_client.bridge import PygameSessionBridge

@pytest.fixture
def bridge() -> PygameSessionBridge:
    return PygameSessionBridge()


def test_start_registers_a_user_and_binds_a_ledger(
    bridge: PygameSessionBridge, repartee_world: str
) -> None:
    """The service rejects an invented user id, so start() must create one."""

    bridge.start(repartee_world)

    assert bridge.user_id is not None
    assert bridge.ledger_id is not None


def test_opening_turn_carries_narration_and_an_available_choice(
    bridge: PygameSessionBridge, repartee_world: str
) -> None:
    envelope = bridge.start(repartee_world)
    turns = bridge.build_turns(list(envelope.fragments))

    lines = [line for turn in turns for line in turn.lines]
    choices = [choice for turn in turns for choice in turn.choices]

    assert any("every introduction is also a challenge" in line.text for line in lines)
    assert any(choice.available and choice.text for choice in choices)


def test_choosing_by_edge_id_advances_the_story(
    bridge: PygameSessionBridge, repartee_world: str
) -> None:
    envelope = bridge.start(repartee_world)
    turns = bridge.build_turns(list(envelope.fragments))
    opening = next(
        choice for turn in turns for choice in turn.choices if choice.available
    )

    advanced = bridge.choose(opening.edge_id, opening.payload)
    lines = [
        line
        for turn in bridge.build_turns(list(advanced.fragments))
        for line in turn.lines
    ]

    assert any("opening line" in line.text for line in lines)
