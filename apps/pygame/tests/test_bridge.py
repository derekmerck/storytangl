"""Adapter tests for the pygame bridge. No pygame import, no display needed."""

from __future__ import annotations

from uuid import uuid4

import pytest

from tangl.journal.fragments import (
    AttributedFragment,
    ChoiceFragment,
    ContentFragment,
    GroupFragment,
    MediaFragment,
)
from tangl.pygame_client.bridge import PygameSessionBridge


@pytest.fixture
def bridge() -> PygameSessionBridge:
    return PygameSessionBridge()


def test_attributed_fragments_become_speaker_lines(bridge: PygameSessionBridge) -> None:
    turns = bridge.build_turns(
        [
            AttributedFragment(
                content="You fight like a dairy farmer.", who="You", how="calls", media="", step=1
            ),
            ContentFragment(content="You win the exchange.", step=1),
        ]
    )

    (turn,) = turns
    assert [(line.speaker, line.manner, line.text) for line in turn.lines] == [
        ("You", "calls", "You fight like a dairy farmer."),
        (None, None, "You win the exchange."),
    ]


def test_choices_carry_edge_id_and_availability(bridge: PygameSessionBridge) -> None:
    edge_id = uuid4()
    turns = bridge.build_turns(
        [
            ChoiceFragment(
                text="Challenge the salon master",
                edge_id=edge_id,
                available=False,
                unavailable_reason="You have no reply yet.",
                step=2,
            )
        ]
    )

    (choice,) = turns[0].choices
    assert choice.edge_id == edge_id
    assert choice.available is False
    assert choice.unavailable_reason == "You have no reply yet."


def test_turns_group_by_step_in_order(bridge: PygameSessionBridge) -> None:
    turns = bridge.build_turns(
        [
            ContentFragment(content="second", step=2),
            ContentFragment(content="first", step=1),
        ]
    )

    assert [turn.step for turn in turns] == [1, 2]
    assert [turn.lines[0].text for turn in turns] == ["first", "second"]


def test_group_fragments_are_flattened(bridge: PygameSessionBridge) -> None:
    turns = bridge.build_turns(
        [
            GroupFragment(
                content=[ContentFragment(content="nested", step=1)],
                step=1,
            )
        ]
    )

    assert [line.text for line in turns[0].lines] == ["nested"]


def test_blank_content_produces_no_line(bridge: PygameSessionBridge) -> None:
    assert bridge.build_turns([ContentFragment(content="   ", step=1)])[0].lines == []


def test_choose_without_a_session_is_refused(bridge: PygameSessionBridge) -> None:
    with pytest.raises(RuntimeError, match="active story session"):
        bridge.choose(uuid4())


def test_choice_forwards_the_activation_payload(bridge: PygameSessionBridge) -> None:
    """The field is ``activation_payload``; ``choice_payload`` does not exist."""

    turns = bridge.build_turns(
        [ChoiceFragment(text="Taunt", edge_id=uuid4(), payload={"move": "taunt"}, step=1)]
    )

    assert turns[0].choices[0].payload == {"move": "taunt"}


# ``src``/``ref`` are also accepted, for parity with the Ren'Py bridge, but
# ``tangl.service.media`` only ever emits ``path``, ``url``, or ``data``.
@pytest.mark.parametrize("key", ["path", "url"])
def test_media_sources_are_read_from_service_payload_keys(
    monkeypatch: pytest.MonkeyPatch, bridge: PygameSessionBridge, key: str
) -> None:
    """Service payloads name media by ``path``/``url``, never ``content``."""

    monkeypatch.setattr(
        "tangl.pygame_client.bridge.media_fragment_to_payload",
        lambda fragment, **_: {
            "fragment_type": "media",
            "media_role": "narrative_im_landscape",
            key: "/assets/bg_quay.png",
        },
    )
    fragment = MediaFragment(
        content="bg_quay.png", content_format="url", media_role="narrative_im_landscape", step=1
    )

    (image,) = bridge.build_turns([fragment])[0].images
    assert image.source == "/assets/bg_quay.png"
    assert image.role == "narrative_im_landscape"


def test_undereferenceable_media_degrades_to_payload_text(
    monkeypatch: pytest.MonkeyPatch, bridge: PygameSessionBridge
) -> None:
    """A content-shaped payload is the service's own text floor; prefer it."""

    monkeypatch.setattr(
        "tangl.pygame_client.bridge.media_fragment_to_payload",
        lambda fragment, **_: {"fragment_type": "content", "content": "[a rainy quay]"},
    )
    fragment = MediaFragment(
        content="missing.png", content_format="url", media_role="narrative_im", step=1
    )

    turn = bridge.build_turns([fragment])[0]
    assert turn.images == []
    assert [line.text for line in turn.lines] == ["[a rainy quay]"]
