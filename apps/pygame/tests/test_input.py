"""Event-loop tests: real events through `main()`, asserting what got committed.

These drive the loop rather than probing the renderer. Events are queued before
`main()` runs, so the loop drains them in order and the trailing QUIT ends it.
"""

from __future__ import annotations

import os
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

pygame = pytest.importorskip("pygame", reason="pygame-ce is an optional client runtime")

from tangl.pygame_client import __main__ as client  # noqa: E402
from tangl.pygame_client.bridge import PygameSessionBridge  # noqa: E402
from tangl.pygame_client.models import Choice, Line, Turn  # noqa: E402
from tangl.pygame_client.stage import SCALE  # noqa: E402

WORLD = "repartee_loop"


@pytest.fixture
def committed(monkeypatch: pytest.MonkeyPatch) -> list[tuple[UUID, object]]:
    """Record every choice the loop commits, without changing behaviour."""

    seen: list[tuple[UUID, object]] = []

    def _record(self, edge_id, payload=None):
        # The frame is frozen to synthetic choices, so these edges are not in
        # the ledger. What is under test is the loop's dispatch, not traversal.
        seen.append((edge_id, payload))
        return SimpleNamespace(fragments=[], metadata={})

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
    gated: list[Choice], committed: list[tuple[UUID, object]]
) -> None:
    """Key 2 commits the second *displayed* choice, not the second available one."""

    _run([_key(pygame.K_2)])

    assert [edge for edge, _payload in committed] == [gated[1].edge_id]


def test_number_key_on_an_unavailable_choice_commits_nothing(
    gated: list[Choice], committed: list[tuple[UUID, object]]
) -> None:
    _run([_key(pygame.K_1)])

    assert committed == []


def test_quit_event_ends_the_loop(gated: list[Choice], committed: list[tuple[UUID, object]]) -> None:
    """A bare QUIT returns from main() without committing anything."""

    _run([])

    assert committed == []


def test_mouse_click_commits_the_choice_under_the_cursor(
    gated: list[Choice], committed: list[tuple[UUID, object]]
) -> None:
    pygame.init()
    from tangl.pygame_client.stage import Stage

    stage = Stage()
    stage.draw(Turn(step=1, choices=gated))
    rect, edge_id, _payload = stage.hitboxes[0]
    position = (rect.centerx * SCALE, rect.centery * SCALE)
    pygame.quit()

    _run([pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": position})])

    assert [edge for edge, _payload in committed] == [edge_id]
    assert edge_id == gated[1].edge_id, "only the available choice is clickable"


def test_scroll_keys_do_not_commit_a_choice(
    gated: list[Choice], committed: list[tuple[UUID, object]]
) -> None:
    _run([_key(pygame.K_DOWN), _key(pygame.K_UP), _key(pygame.K_PAGEDOWN)])

    assert committed == []
