"""Event-loop tests: real events through `main()`, asserting what got committed.

These drive the loop rather than probing the renderer. Events are queued before
`main()` runs, so the loop drains them in order and the trailing QUIT ends it.
"""

from __future__ import annotations

import os
from uuid import UUID, uuid4

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

pygame = pytest.importorskip("pygame", reason="pygame-ce is an optional client runtime")

from tangl.pygame_client import __main__ as client  # noqa: E402
from tangl.pygame_client.bridge import PygameSessionBridge  # noqa: E402
from tangl.journal.intent import (  # noqa: E402
    PieceConstraints,
    PiecesAccepts,
    TextAccepts,
)
from tangl.pygame_client.models import (  # noqa: E402
    Choice,
    Line,
    PendingSelection,
    Piece,
    PickPiece,
    Turn,
    Zone,
)
from tangl.pygame_client.stage import SCALE  # noqa: E402
from tangl.service import JsonValue, RuntimeEnvelope  # noqa: E402

WORLD = "repartee_loop"


@pytest.fixture
def committed(monkeypatch: pytest.MonkeyPatch) -> list[tuple[UUID, JsonValue | None]]:
    """Record every choice the loop commits, without changing behaviour."""

    seen: list[tuple[UUID, JsonValue | None]] = []

    def _record(
        _self: PygameSessionBridge,
        edge_id: UUID,
        payload: JsonValue | None = None,
    ) -> RuntimeEnvelope:
        # The frame is frozen to synthetic choices, so these edges are not in
        # the ledger. What is under test is the loop's dispatch, not traversal.
        seen.append((edge_id, payload))
        return RuntimeEnvelope()

    monkeypatch.setattr(PygameSessionBridge, "choose", _record)
    return seen


@pytest.fixture
def gated(monkeypatch: pytest.MonkeyPatch) -> list[Choice]:
    """Freeze the frame to one unavailable choice followed by an available one."""

    choices = [
        Choice(edge_id=uuid4(), text="Locked", available=False, unavailable_reason="not yet"),
        Choice(edge_id=uuid4(), text="Open"),
    ]
    frame = Turn(step=1, lines=[Line(text="hub")], choices=choices)
    monkeypatch.setattr(client, "_merge", lambda _turns: frame)
    monkeypatch.setattr(client, "_turns", lambda _bridge, _envelope: [frame])
    return choices


def _key(code: int) -> pygame.event.Event:
    return pygame.event.Event(pygame.KEYDOWN, {"key": code, "mod": 0, "unicode": ""})


def _run(events: list[pygame.event.Event]) -> None:
    pygame.init()
    for event in [*events, pygame.event.Event(pygame.QUIT)]:
        pygame.event.post(event)
    client.main(["--world", WORLD])


def test_number_key_uses_displayed_numbering(
    gated: list[Choice], committed: list[tuple[UUID, JsonValue | None]]
) -> None:
    """Key 2 commits the second *displayed* choice, not the second available one."""

    _run([_key(pygame.K_2)])

    assert [edge for edge, _payload in committed] == [gated[1].edge_id]


def test_number_key_on_an_unavailable_choice_commits_nothing(
    gated: list[Choice], committed: list[tuple[UUID, JsonValue | None]]
) -> None:
    _run([_key(pygame.K_1)])

    assert committed == []


def test_quit_event_ends_the_loop(
    gated: list[Choice], committed: list[tuple[UUID, JsonValue | None]]
) -> None:
    """A bare QUIT returns from main() without committing anything."""

    _run([])

    assert committed == []


def test_mouse_click_commits_the_choice_under_the_cursor(
    gated: list[Choice], committed: list[tuple[UUID, JsonValue | None]]
) -> None:
    pygame.init()
    from tangl.pygame_client.stage import Stage

    stage = Stage()
    stage.draw(Turn(step=1, choices=gated))
    rect, action = stage.hitboxes[0]
    position = (rect.centerx * SCALE, rect.centery * SCALE)
    pygame.quit()

    _run([pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": position})])

    assert [edge for edge, _payload in committed] == [action.edge_id]
    assert action.edge_id == gated[1].edge_id, "only the available choice is clickable"


def test_scroll_keys_move_the_view_without_committing(
    monkeypatch: pytest.MonkeyPatch,
    committed: list[tuple[UUID, JsonValue | None]],
) -> None:
    """Arrows scroll prose. They must move the view and commit nothing."""

    frame = Turn(
        step=1,
        lines=[Line(text=f"line {index}") for index in range(60)],
        choices=[Choice(edge_id=uuid4(), text="continue")],
    )
    monkeypatch.setattr(client, "_merge", lambda _turns: frame)
    monkeypatch.setattr(client, "_turns", lambda _bridge, _envelope: [frame])

    seen: list[int] = []
    from tangl.pygame_client.stage import Stage

    original = Stage.scroll_by

    def _record(self, delta: int) -> None:
        original(self, delta)
        seen.append(self.scroll)

    monkeypatch.setattr(Stage, "scroll_by", _record)
    _run([_key(pygame.K_UP), _key(pygame.K_UP), _key(pygame.K_PAGEDOWN)])

    assert seen, "scroll keys never reached the loop"
    assert seen[0] < seen[-1] or len(set(seen)) > 1, "the view never moved"
    assert committed == []


# ── typed accepts through the loop ───────────────────────────────────────────


ZONE = uuid4()


@pytest.fixture
def packet(monkeypatch: pytest.MonkeyPatch) -> Choice:
    """Freeze the frame to one `pieces` choice over a two-document packet."""

    choice = Choice(
        edge_id=uuid4(),
        text="Inspect a document",
        accepts=PiecesAccepts(
            min=1, max=1, constraints=PieceConstraints(target_zone_ref=str(ZONE))
        ),
    )
    frame = Turn(
        step=1,
        lines=[Line(text="Tomas Vey steps forward.")],
        choices=[choice],
        zones=[Zone(uid=ZONE, role="packet")],
        pieces=[
            Piece(piece_id="0:passport", kind="id_card", text="crisp", zone_ref=ZONE),
            Piece(piece_id="0:permit", kind="permit", text="unsealed", zone_ref=ZONE),
        ],
    )
    monkeypatch.setattr(client, "_merge", lambda _turns: frame)
    monkeypatch.setattr(client, "_turns", lambda _bridge, _envelope: [frame])
    return choice


def test_a_pieces_choice_needs_two_keys_and_commits_the_piece_payload(
    packet: Choice, committed: list[tuple[UUID, JsonValue | None]]
) -> None:
    """The first key opens the selection; the second names the piece.

    One key alone must not commit -- that is the whole difference between a
    `pick` and a typed choice.
    """

    _run([_key(pygame.K_1)])
    assert committed == [], "opening a selection commits nothing"

    committed.clear()
    _run([_key(pygame.K_1), _key(pygame.K_2)])

    assert committed == [(packet.edge_id, {"piece_ids": ["0:permit"]})]


def test_the_selection_list_is_numbered_independently_of_the_choices(
    packet: Choice, committed: list[tuple[UUID, JsonValue | None]]
) -> None:
    _run([_key(pygame.K_1), _key(pygame.K_1)])

    assert committed == [(packet.edge_id, {"piece_ids": ["0:passport"]})]


def test_escape_leaves_a_selection_without_leaving_the_game(
    packet: Choice, committed: list[tuple[UUID, JsonValue | None]]
) -> None:
    """Escape cancels the selection, then the choice is selectable again."""

    _run([_key(pygame.K_1), _key(pygame.K_ESCAPE), _key(pygame.K_1), _key(pygame.K_2)])

    assert committed == [(packet.edge_id, {"piece_ids": ["0:permit"]})]


def test_zero_cancels_a_selection(
    packet: Choice, committed: list[tuple[UUID, JsonValue | None]]
) -> None:
    _run([_key(pygame.K_1), _key(pygame.K_0)])

    assert committed == []


def test_a_click_on_a_piece_commits_what_its_number_commits(
    packet: Choice, committed: list[tuple[UUID, JsonValue | None]]
) -> None:
    """Input Parity: the hitbox and the key produce the same payload."""

    pygame.init()
    from tangl.pygame_client.stage import Stage

    stage = Stage()
    frame = client._merge([])
    pending = PendingSelection(choice=packet)
    stage.draw(frame, pending)
    rect, action = stage.hitboxes[0]
    position = (rect.centerx * SCALE, rect.centery * SCALE)
    pygame.quit()

    _run([_key(pygame.K_1), pygame.event.Event(
        pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": position}
    )])

    assert action == PickPiece(piece_id="0:passport")
    assert committed == [(packet.edge_id, {"piece_ids": ["0:passport"]})]


def test_a_choice_this_port_cannot_collect_renders_inert(
    monkeypatch: pytest.MonkeyPatch,
    committed: list[tuple[UUID, JsonValue | None]],
) -> None:
    """No guessed payload, no crash: the row is drawn and does nothing.

    The CLI refuses the same kinds unless handed an explicit `--payload`.
    """

    choice = Choice(edge_id=uuid4(), text="Say something", accepts=TextAccepts())
    frame = Turn(step=1, choices=[choice])
    monkeypatch.setattr(client, "_merge", lambda _turns: frame)
    monkeypatch.setattr(client, "_turns", lambda _bridge, _envelope: [frame])

    _run([_key(pygame.K_1)])

    assert committed == []
