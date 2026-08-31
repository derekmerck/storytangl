"""Renderer tests. Headless via the dummy SDL driver; no display required."""

from __future__ import annotations

import os
from uuid import uuid4

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

pygame = pytest.importorskip("pygame", reason="pygame-ce is an optional client runtime")

from tangl.pygame_client.models import Choice, Line, Turn  # noqa: E402
from tangl.pygame_client.stage import LOGICAL_SIZE, SCALE, Stage  # noqa: E402


@pytest.fixture
def stage() -> Stage:
    made = Stage()
    yield made
    pygame.quit()


def _turn(line_count: int, choice_count: int) -> Turn:
    return Turn(
        step=1,
        lines=[
            Line(text=f"A line of narration number {index} " * 3, speaker="Dockhand", manner="calls")
            for index in range(line_count)
        ],
        choices=[
            Choice(edge_id=uuid4(), text=f"choice {index}") for index in range(choice_count)
        ],
    )


@pytest.mark.parametrize("line_count", [1, 5, 20])
def test_choices_stay_on_the_logical_surface(stage: Stage, line_count: int) -> None:
    """A long exchange must never push the only way to continue off-screen.

    The dockhand contest alone merges five lines with the aftermath content.
    """

    stage.draw(_turn(line_count, choice_count=3))

    assert len(stage.hitboxes) == 3
    for rect, _edge_id, _payload in stage.hitboxes:
        assert rect.bottom <= LOGICAL_SIZE[1]
        assert rect.top >= 0


def test_every_available_choice_is_clickable(stage: Stage) -> None:
    stage.draw(_turn(12, choice_count=3))

    for rect, edge_id, _payload in stage.hitboxes:
        centre = (rect.centerx * SCALE, rect.centery * SCALE)
        assert stage.hit(centre) is not None
        assert stage.hit(centre)[0] == edge_id


def test_unavailable_choices_are_shown_but_not_clickable(stage: Stage) -> None:
    """Decision Legibility: dimmed with a reason, not hidden."""

    turn = Turn(
        step=1,
        choices=[
            Choice(
                edge_id=uuid4(),
                text="Challenge the salon master",
                available=False,
                unavailable_reason="You have no reply yet.",
            ),
            Choice(edge_id=uuid4(), text="Challenge the dockhand"),
        ],
    )
    stage.draw(turn)

    assert len(stage.hitboxes) == 1
    assert stage.hitboxes[0][1] == turn.choices[1].edge_id
