"""Live-session tests for the pygame bridge against a real world bundle."""

from __future__ import annotations

from pathlib import Path

import pytest

from tangl.journal.fragments import MediaFragment
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


def test_opening_turn_uses_the_canonical_narrative_background_role(
    bridge: PygameSessionBridge, repartee_world: str
) -> None:
    envelope = bridge.start(repartee_world)
    media = next(
        fragment for fragment in envelope.fragments if isinstance(fragment, MediaFragment)
    )
    images = [
        image
        for turn in bridge.build_turns(list(envelope.fragments))
        for image in turn.images
    ]

    assert media.media_role == "narrative_im"
    assert media.staging_hints is not None
    assert media.staging_hints.media_shape == "landscape"
    assert [(image.role, Path(image.source).name) for image in images] == [
        ("narrative_im", "quai_bg.png"),
    ]


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


def _advance_to_map(bridge: PygameSessionBridge, world: str):
    """Walk the opening beats until the reader is standing on the quay map."""

    envelope = bridge.start(world)
    for text in ("Step into the practice court", "Step out onto the quay"):
        turns = bridge.build_turns(list(envelope.fragments))
        choice = next(
            c for turn in turns for c in turn.choices if c.text == text and c.available
        )
        envelope = bridge.choose(choice.edge_id, choice.payload)
    return envelope


def test_the_map_hub_publishes_a_plate_the_client_can_draw(
    bridge: PygameSessionBridge, repartee_world: str
) -> None:
    """Geometry arrives over story-info, not in the journal."""

    _advance_to_map(bridge, repartee_world)
    plate = bridge.map_plate()

    assert plate is not None
    assert plate.name == "quay"
    assert plate.image == "quay_map.png"
    assert {region.name for region in plate.regions} == {
        "quayside",
        "practice_yard",
        "salon_terrace",
        "salon",
    }
    assert all(0.0 <= r.x < 1.0 and 0.0 <= r.y < 1.0 for r in plate.regions)


def test_every_plate_region_is_claimed_by_exactly_one_travel_choice(
    bridge: PygameSessionBridge, repartee_world: str
) -> None:
    """The join the renderer performs, asserted on real world output."""

    envelope = _advance_to_map(bridge, repartee_world)
    plate = bridge.map_plate()
    assert plate is not None
    choices = [c for turn in bridge.build_turns(list(envelope.fragments)) for c in turn.choices]

    for region in plate.regions:
        claimants = [c for c in choices if plate.claim(region) in c.tags]
        assert len(claimants) == 1, f"{region.name} has {len(claimants)} claimants"

    # Two places are guarded at this point in the story and must still be shown.
    guarded = {c.text for c in choices if c.tags and not c.available}
    assert guarded == {"Go to The Salon", "Go to The Salon Terrace"}
    assert all(c.unavailable_reason for c in choices if c.tags and not c.available)


def test_a_world_without_a_map_publishes_no_plate(
    bridge: PygameSessionBridge, repartee_world: str
) -> None:
    """The opening block is an ordinary block, so there is nothing to draw."""

    bridge.start(repartee_world)

    assert bridge.map_plate() is None
