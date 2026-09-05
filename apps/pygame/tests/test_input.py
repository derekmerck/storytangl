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
    CancelSelection,
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


# ── variable-size selections, paging, and --advance ──────────────────────────


def _packet_frame(monkeypatch, accepts, count: int = 2) -> Choice:
    choice = Choice(edge_id=uuid4(), text="Inspect", accepts=accepts)
    frame = Turn(
        step=1,
        choices=[choice],
        zones=[Zone(uid=ZONE, role="packet")],
        pieces=[
            Piece(piece_id=f"0:doc{n}", kind="id_card", text="x",
                  label=f"doc {n}", zone_ref=ZONE)
            for n in range(count)
        ],
    )
    monkeypatch.setattr(client, "_merge", lambda _turns: frame)
    monkeypatch.setattr(client, "_turns", lambda _bridge, _envelope: [frame])
    return choice


def test_a_range_selection_waits_for_confirmation(
    monkeypatch: pytest.MonkeyPatch, committed: list[tuple[UUID, JsonValue | None]]
) -> None:
    """min=1 max=2 must not commit on the first pick.

    Between the minimum and the maximum there is no moment the client can infer,
    so the player says when they are done.
    """

    choice = _packet_frame(monkeypatch, PiecesAccepts(min=1, max=2))

    _run([_key(pygame.K_1), _key(pygame.K_1)])
    assert committed == [], "one of a possible two must not auto-commit"

    committed.clear()
    _run([_key(pygame.K_1), _key(pygame.K_1), _key(pygame.K_8)])

    assert committed == [(choice.edge_id, {"piece_ids": ["0:doc0"]})]


def test_a_range_selection_commits_itself_at_the_maximum(
    monkeypatch: pytest.MonkeyPatch, committed: list[tuple[UUID, JsonValue | None]]
) -> None:
    """At max there is nothing left to decide, so no confirmation is required."""

    choice = _packet_frame(monkeypatch, PiecesAccepts(min=1, max=2))

    _run([_key(pygame.K_1), _key(pygame.K_1), _key(pygame.K_1)])

    assert committed == [(choice.edge_id, {"piece_ids": ["0:doc0", "0:doc1"]})]


def test_an_optional_selection_can_be_submitted_empty(
    monkeypatch: pytest.MonkeyPatch, committed: list[tuple[UUID, JsonValue | None]]
) -> None:
    """min=0 is satisfied before anything is picked."""

    choice = _packet_frame(monkeypatch, PiecesAccepts(min=0, max=2))

    _run([_key(pygame.K_1), _key(pygame.K_8)])

    assert committed == [(choice.edge_id, {"piece_ids": []})]


def test_confirm_does_nothing_below_the_minimum(
    monkeypatch: pytest.MonkeyPatch, committed: list[tuple[UUID, JsonValue | None]]
) -> None:
    _packet_frame(monkeypatch, PiecesAccepts(min=2, max=2))

    _run([_key(pygame.K_1), _key(pygame.K_8)])

    assert committed == []


def test_a_long_candidate_list_pages_and_the_numbers_follow(
    monkeypatch: pytest.MonkeyPatch, committed: list[tuple[UUID, JsonValue | None]]
) -> None:
    """Twenty documents must stay on screen and stay selectable.

    Laying them all out put the first rows above the top of the surface, where
    they were neither readable nor clickable.
    """

    choice = _packet_frame(monkeypatch, PiecesAccepts(min=1, max=1), count=20)

    # Page once, then take the first row of page two.
    _run([_key(pygame.K_1), _key(pygame.K_9), _key(pygame.K_1)])

    assert committed == [(choice.edge_id, {"piece_ids": ["0:doc7"]})]


def test_the_last_candidate_on_a_page_is_reachable_by_key(
    monkeypatch: pytest.MonkeyPatch, committed: list[tuple[UUID, JsonValue | None]]
) -> None:
    """The bottom row of a full page must not collide with a control key.

    Drawing eight candidates while reserving 8 for Confirm made the last row
    clickable but unreachable by keyboard -- and once the minimum was met, that
    key committed instead of picking the row under it.
    """

    choice = _packet_frame(monkeypatch, PiecesAccepts(min=1, max=1), count=20)

    _run([_key(pygame.K_1), _key(pygame.K_7)])
    assert committed == [(choice.edge_id, {"piece_ids": ["0:doc6"]})]

    committed.clear()
    _run([_key(pygame.K_1), _key(pygame.K_9), _key(pygame.K_7)])

    assert committed == [(choice.edge_id, {"piece_ids": ["0:doc13"]})]


def test_paging_keeps_cycling_past_the_first_wrap(
    monkeypatch: pytest.MonkeyPatch, committed: list[tuple[UUID, JsonValue | None]]
) -> None:
    """Repeated paging returns to page one and keeps going.

    The label wrapped with modulo while the slice clamped separately, so twenty
    candidates walked 0, 7, 14 and then stuck on the first page while the label
    carried on counting.
    """

    choice = _packet_frame(monkeypatch, PiecesAccepts(min=1, max=1), count=20)
    page = [_key(pygame.K_9)]

    # Three pages, so four advances wrap back onto page two.
    _run([_key(pygame.K_1), *page * 4, _key(pygame.K_1)])

    assert committed == [(choice.edge_id, {"piece_ids": ["0:doc7"]})]


def test_advance_refuses_a_choice_it_cannot_supply_a_value_for(
    capsys: pytest.CaptureFixture[str], tmp_path
) -> None:
    """`--advance` must not send a typed choice's bare activation payload.

    credential_gate's second turn is a `pieces` choice, so a headless walk has
    to stop and say so rather than commit a move the backend will reject.
    """

    client.main(["--world", "credential_gate", "--advance", "4",
                 "--screenshot", str(tmp_path / "frame.png")])
    message = capsys.readouterr().err

    assert "--advance stopped" in message
    assert "Inspect a document" in message


def test_the_cancel_row_stays_on_the_surface_below_the_minimum(
    monkeypatch: pytest.MonkeyPatch, committed: list[tuple[UUID, JsonValue | None]]
) -> None:
    """The hint row is drawn whether or not the minimum is met, so it is reserved.

    Counting Confirm only when satisfied left the unsatisfied layout one row
    short, pushing Cancel to y=196 where it clipped off the bottom.
    """

    pygame.init()
    from tangl.pygame_client.stage import LOGICAL_SIZE, Stage

    choice = _packet_frame(monkeypatch, PiecesAccepts(min=2, max=2), count=7)
    frame = client._merge([])
    stage = Stage()

    for picked in ([], ["0:doc0"], ["0:doc0", "0:doc1"]):
        stage.hitboxes.clear()
        pending = PendingSelection(choice=choice, picked=list(picked))
        stage.draw(frame, pending)
        cancels = [
            rect
            for rect, action in stage.hitboxes
            if isinstance(action, CancelSelection)
        ]
        assert cancels, f"cancel must be actionable with {len(picked)} picked"
        assert cancels[0].bottom <= LOGICAL_SIZE[1], (
            f"cancel clipped off the surface with {len(picked)} picked"
        )
    pygame.quit()


def test_every_panel_page_is_reachable_from_the_keyboard(
    monkeypatch: pytest.MonkeyPatch, committed: list[tuple[UUID, JsonValue | None]]
) -> None:
    """The panel advertises a tab binding; it has to actually be bound.

    `PagePanel` was emitted only by the pager hitbox, so the state a mouse could
    reach was unreachable by keyboard.
    """

    frame = Turn(
        step=1,
        choices=[Choice(edge_id=uuid4(), text="wait")],
        zones=[Zone(uid=ZONE, role="packet")],
        pieces=[
            Piece(piece_id=f"0:doc{n}", kind="id_card", text="x",
                  label=f"a rather long document name {n}", zone_ref=ZONE)
            for n in range(10)
        ],
    )
    monkeypatch.setattr(client, "_merge", lambda _turns: frame)
    monkeypatch.setattr(client, "_turns", lambda _bridge, _envelope: [frame])

    seen: list[int] = []
    original = client.Stage.draw

    def record(self, turn, pending=None):
        seen.append(self.panel_scroll)
        return original(self, turn, pending)

    monkeypatch.setattr(client.Stage, "draw", record)

    _run([_key(pygame.K_TAB), _key(pygame.K_TAB)])

    assert seen[-1] > seen[0], "tab must advance the panel page"
    assert committed == [], "paging the panel commits nothing"


def test_advance_does_not_blame_an_unavailable_choice(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path
) -> None:
    """An unavailable choice is not what stopped `--advance`.

    `A and B or C` binds as `(A and B) or C`, so an unavailable `pieces` choice
    was reported as needing a value it was never going to be asked for.
    """

    frame = Turn(
        step=1,
        choices=[
            Choice(
                edge_id=uuid4(),
                text="Inspect a document",
                available=False,
                unavailable_reason="the counter is closed",
                accepts=PiecesAccepts(min=1, max=1),
            )
        ],
    )
    monkeypatch.setattr(client, "_merge", lambda _turns: frame)
    monkeypatch.setattr(client, "_turns", lambda _bridge, _envelope: [frame])

    client.main(["--world", WORLD, "--advance", "2",
                 "--screenshot", str(tmp_path / "frame.png")])

    assert "Inspect a document" not in capsys.readouterr().err
