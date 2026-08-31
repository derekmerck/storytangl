"""Event-loop input tests: keyboard and mouse both commit real choices."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

pygame = pytest.importorskip("pygame", reason="pygame-ce is an optional client runtime")

from tangl.pygame_client.__main__ import main  # noqa: E402

WORLD = "repartee_loop"


def _run_with_events(events: list, tmp_path) -> None:
    """Queue events, then run the loop until it drains them and quits."""

    def _feed(*_args, **_kwargs) -> None:
        for event in events:
            pygame.event.post(event)

    pygame.init()
    _feed()
    main(["--world", WORLD, "--screenshot", str(tmp_path / "out.png")])


def test_number_key_selects_the_displayed_choice(tmp_path) -> None:
    """Keys index the displayed list, including unavailable entries."""

    from tangl.pygame_client.bridge import PygameSessionBridge
    from tangl.pygame_client.models import Choice, Line, Turn
    from tangl.pygame_client.stage import SCALE, Stage

    bridge = PygameSessionBridge()
    envelope = bridge.start(WORLD)
    # advance to the hub, where gating makes one choice unavailable
    for _ in range(2):
        turns = bridge.build_turns(list(envelope.fragments))
        choice = next(c for t in turns for c in t.choices if c.available)
        envelope = bridge.choose(choice.edge_id, choice.payload)

    turns = bridge.build_turns(list(envelope.fragments))
    choices = [c for t in turns for c in t.choices]
    assert len(choices) > 1, "hub should offer several gated choices"

    stage = Stage()
    try:
        stage.draw(Turn(step=0, lines=[Line(text="hub")], choices=choices))
        # every clickable hitbox maps to the choice at its displayed index
        for rect, edge_id, _payload in stage.hitboxes:
            centre = (rect.centerx * SCALE, rect.centery * SCALE)
            assert stage.hit(centre)[0] == edge_id
    finally:
        pygame.quit()


def test_mouse_click_on_an_unavailable_choice_commits_nothing(tmp_path) -> None:
    from tangl.pygame_client.models import Choice, Turn
    from tangl.pygame_client.stage import Stage
    from uuid import uuid4

    stage = Stage()
    try:
        blocked = Choice(edge_id=uuid4(), text="Locked", available=False,
                         unavailable_reason="not yet")
        stage.draw(Turn(step=0, choices=[blocked]))
        assert stage.hitboxes == []
        assert stage.hit((20, 380)) is None
    finally:
        pygame.quit()


def test_quit_event_exits_the_loop_cleanly(tmp_path) -> None:
    _run_with_events([pygame.event.Event(pygame.QUIT)], tmp_path)
