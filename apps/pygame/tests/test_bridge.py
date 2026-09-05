"""Adapter tests for the pygame bridge. No pygame import, no display needed."""

from __future__ import annotations

from uuid import uuid4

import pytest

from tangl.journal.content import PresentationHints
from tangl.journal.fragments import (
    AttributedFragment,
    ChoiceFragment,
    ContentFragment,
    GroupFragment,
    KvFragment,
    MediaFragment,
    PieceFragment,
)
from tangl.journal.intent import (
    KvRow,
    PickAccepts,
    PieceConstraints,
    PiecesAccepts,
    QuantityAccepts,
    TextAccepts,
)
from tangl.pygame_client.bridge import (
    PygameSessionBridge,
    UnsupportedAccepts,
    commit_payload,
    remaining_pieces,
    selectable_pieces,
)
from tangl.pygame_client.models import Choice, PendingSelection


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
            "media_role": "narrative_im",
            key: "/assets/bg_quay.png",
        },
    )
    fragment = MediaFragment(
        content="bg_quay.png",
        content_format="url",
        media_role="narrative_im",
        staging_hints={"media_shape": "landscape"},
        step=1,
    )

    (image,) = bridge.build_turns([fragment])[0].images
    assert image.source == "/assets/bg_quay.png"
    assert image.role == "narrative_im"


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


# ── typed accepts ────────────────────────────────────────────────────────────


def _packet(bridge: PygameSessionBridge, zone_uid, *labels: str):
    """One zone holding a document piece per label, plus an unzoned candidate."""

    fragments = [
        PieceFragment(
            piece_id="candidate-0", piece_kind="candidate", content="Tomas Vey", step=1
        ),
        GroupFragment(uid=zone_uid, group_type="zone", zone_role="packet", step=1),
    ]
    fragments += [
        PieceFragment(
            piece_id=f"0:{label}",
            piece_kind="id_card",
            content=f"a {label}",
            zone_ref=zone_uid,
            hints=PresentationHints(label_text=label),
            step=1,
        )
        for label in labels
    ]
    return bridge.build_turns(fragments)[0]


def test_pieces_and_zones_reach_the_turn(bridge: PygameSessionBridge) -> None:
    zone = uuid4()
    turn = _packet(bridge, zone, "passport", "work permit")

    assert [piece.piece_id for piece in turn.pieces] == [
        "candidate-0",
        "0:passport",
        "0:work permit",
    ]
    assert [zone.role for zone in turn.zones] == ["packet"]
    assert [piece.label for piece in turn.pieces[1:]] == ["passport", "work permit"]


def test_a_zone_constraint_narrows_the_selectable_pieces(
    bridge: PygameSessionBridge,
) -> None:
    """Decision Legibility: only pieces in the named zone can satisfy the choice.

    The candidate is a piece too, and sits outside the packet. Offering it would
    invite a commit the backend must reject.
    """

    zone = uuid4()
    turn = _packet(bridge, zone, "passport")
    choice = Choice(
        edge_id=uuid4(),
        text="Inspect a document",
        accepts=PiecesAccepts(
            min=1, max=1, constraints=PieceConstraints(target_zone_ref=str(zone))
        ),
    )

    assert [piece.piece_id for piece in selectable_pieces(turn, choice)] == ["0:passport"]


def test_an_unconstrained_pieces_choice_offers_every_piece(
    bridge: PygameSessionBridge,
) -> None:
    turn = _packet(bridge, uuid4(), "passport")
    choice = Choice(edge_id=uuid4(), text="Point at something", accepts=PiecesAccepts())

    assert len(selectable_pieces(turn, choice)) == len(turn.pieces)


@pytest.mark.parametrize(
    ("accepts", "values", "expected"),
    [
        (None, (), {}),
        (PickAccepts(), (), {}),
        (PiecesAccepts(min=1, max=1), ("0:passport",), {"piece_ids": ["0:passport"]}),
        (
            PiecesAccepts(min=1, max=2),
            ("a", "b"),
            {"piece_ids": ["a", "b"]},
        ),
    ],
)
def test_commit_payload_matches_the_cli_shapes(accepts, values, expected) -> None:
    """§6.1.1: both ports must build the same payload for the same choice."""

    choice = Choice(edge_id=uuid4(), text="act", accepts=accepts)

    assert commit_payload(choice, values) == expected


@pytest.mark.parametrize(
    ("accepts", "values"),
    [
        (PickAccepts(), ("unexpected",)),
        (PiecesAccepts(min=2, max=2), ("only-one",)),
        (PiecesAccepts(min=1, max=1), ("one", "two")),
        (TextAccepts(), ()),
        (QuantityAccepts(), ()),
    ],
)
def test_commit_payload_refuses_what_it_cannot_build(accepts, values) -> None:
    """Refusing early keeps a doomed commit off the wire.

    The CLI refuses the same kinds unless handed an explicit payload; guessing a
    shape here would surface to the player as an opaque backend error instead.
    """

    choice = Choice(edge_id=uuid4(), text="act", accepts=accepts)

    with pytest.raises(UnsupportedAccepts):
        commit_payload(choice, values)


def test_remaining_pieces_drops_what_is_already_picked(
    bridge: PygameSessionBridge,
) -> None:
    zone = uuid4()
    turn = _packet(bridge, zone, "passport", "work permit")
    choice = Choice(
        edge_id=uuid4(),
        text="Inspect two",
        accepts=PiecesAccepts(
            min=2, max=2, constraints=PieceConstraints(target_zone_ref=str(zone))
        ),
    )
    pending = PendingSelection(choice=choice, picked=["0:passport"])

    assert [piece.piece_id for piece in remaining_pieces(turn, pending)] == [
        "0:work permit"
    ]


def test_kv_fragments_become_findings(bridge: PygameSessionBridge) -> None:
    """Findings keep the engine's own severity word; the client never re-derives it."""

    turn = bridge.build_turns([
        KvFragment(
            content=[
                KvRow(key="work permit", value="never sealed", emphasis="warn"),
                KvRow(key="packet consistency", value="does not satisfy", emphasis="danger"),
            ],
            step=1,
        )
    ])[0]

    assert [(f.key, f.emphasis) for f in turn.findings] == [
        ("work permit", "warn"),
        ("packet consistency", "danger"),
    ]


def test_an_unavailable_piece_is_never_offered(bridge: PygameSessionBridge) -> None:
    """A spent document stays visible but cannot satisfy the choice.

    Offering it would put a guaranteed backend rejection behind a row that looks
    perfectly selectable.
    """

    zone = uuid4()
    turn = bridge.build_turns([
        GroupFragment(uid=zone, group_type="zone", zone_role="packet", step=1),
        PieceFragment(
            piece_id="0:passport",
            piece_kind="id_card",
            content="crisp",
            zone_ref=zone,
            available=False,
            unavailable_reason="already inspected",
            hints=PresentationHints(label_text="passport"),
            step=1,
        ),
        PieceFragment(
            piece_id="0:permit",
            piece_kind="permit",
            content="unsealed",
            zone_ref=zone,
            hints=PresentationHints(label_text="work permit"),
            step=1,
        ),
    ])[0]
    choice = Choice(
        edge_id=uuid4(),
        text="Inspect a document",
        accepts=PiecesAccepts(
            min=1, max=1, constraints=PieceConstraints(target_zone_ref=str(zone))
        ),
    )

    assert [piece.piece_id for piece in turn.pieces] == ["0:passport", "0:permit"]
    assert [piece.piece_id for piece in selectable_pieces(turn, choice)] == ["0:permit"]
    assert turn.pieces[0].unavailable_reason == "already inspected"


# ── activation payloads and availability ─────────────────────────────────────


def test_an_authored_activation_payload_survives_a_pick() -> None:
    """The edge's own answer is not discarded by building a payload for it.

    Sending `{}` here dropped whatever the author put on the edge. That the CLI
    also drops it is a gap on that side, not a licence to regress this one.
    """

    choice = Choice(edge_id=uuid4(), text="Taunt", payload={"move": "taunt"})

    assert commit_payload(choice) == {"move": "taunt"}


def test_a_pick_without_an_authored_payload_sends_an_empty_object() -> None:
    assert commit_payload(Choice(edge_id=uuid4(), text="Go")) == {}


def test_a_non_mapping_activation_payload_travels_verbatim() -> None:
    choice = Choice(edge_id=uuid4(), text="Go", payload="north")

    assert commit_payload(choice) == "north"


def test_collected_values_are_merged_over_the_authored_payload() -> None:
    """Explicit precedence: authored keys are the base, collected keys win.

    The player's answer to `accepts` is what the choice asked for, so an author
    default cannot shadow it.
    """

    choice = Choice(
        edge_id=uuid4(),
        text="Inspect",
        payload={"style": "careful", "piece_ids": ["authored"]},
        accepts=PiecesAccepts(min=1, max=1),
    )

    assert commit_payload(choice, ["0:passport"]) == {
        "style": "careful",
        "piece_ids": ["0:passport"],
    }


def test_an_unconstrained_choice_still_refuses_unavailable_pieces(
    bridge: PygameSessionBridge,
) -> None:
    """Availability gates both paths, constrained and not.

    A choice with no zone constraint offered every piece, including ones the
    backend had already marked unselectable.
    """

    turn = bridge.build_turns([
        PieceFragment(piece_id="spent", piece_kind="id_card", content="x",
                      available=False, unavailable_reason="already inspected", step=1),
        PieceFragment(piece_id="live", piece_kind="id_card", content="y", step=1),
    ])[0]
    choice = Choice(edge_id=uuid4(), text="Point", accepts=PiecesAccepts())

    assert [piece.piece_id for piece in turn.pieces] == ["spent", "live"]
    assert [piece.piece_id for piece in selectable_pieces(turn, choice)] == ["live"]
