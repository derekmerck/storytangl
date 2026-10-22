"""Bounded text views preserve all wording, actions, and independent positions."""

from __future__ import annotations

import os
from uuid import uuid4

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
pygame = pytest.importorskip("pygame")

from tangl.presentation.intent import TextAccepts  # noqa: E402
from tangl.pygame_client.models import Choice, Commit, Line, ScrollText, Turn  # noqa: E402
from tangl.pygame_client.stage import Stage  # noqa: E402


@pytest.fixture(params=[(320, 200), (640, 400)])
def stage(request) -> Stage:
    made = Stage(logical_size=request.param, display_scale=1)
    yield made
    pygame.quit()


def crowded() -> Turn:
    return Turn(
        step=1,
        lines=[Line(text=f"Prose row {index:03}") for index in range(112)],
        choices=[
            Choice(
                edge_id=uuid4(),
                text=f"Choice {index:02}: " + "full wording remains readable " * 4,
                available=index % 4 != 1,
                unavailable_reason="Requires the complete unabridged explanation " * 3
                if index % 4 == 1 else None,
                accepts=TextAccepts() if index % 4 == 2 else None,
                payload={"index": index},
            )
            for index in range(65)
        ],
    )


def test_every_prose_and_choice_row_is_reachable_independently(
    stage: Stage, monkeypatch: pytest.MonkeyPatch,
) -> None:
    turn = crowded()
    painted_prose = []
    draw_rows = stage._draw_rows

    def record(rows, **layout):
        painted_prose.extend(row.text for row in rows)
        draw_rows(rows, **layout)

    monkeypatch.setattr(stage, "_draw_rows", record)
    stage.draw(turn)
    assert painted_prose[0] == "Prose row 000"
    assert stage.scroll == stage.choice_scroll == 0
    assert stage.prose_rect.bottom <= stage.choice_rect.top
    assert stage.choice_rect.bottom <= stage.logical_size[1]
    assert stage.prose_capacity > 0 and stage.choice_capacity > 0

    prose_seen: set[int] = set()
    while True:
        prose_seen.update(range(stage.scroll, stage.scroll + stage.prose_capacity))
        if stage.scroll == stage.max_scroll:
            break
        previous = stage.scroll
        stage.scroll_text(ScrollText("prose", 1, page=True))
        assert stage.scroll == min(previous + stage.prose_capacity, stage.max_scroll)
        stage.draw(turn)
        assert stage.choice_scroll == 0
    assert prose_seen == set(range(112))
    assert set(painted_prose) == {line.text for line in turn.lines}

    rows = stage._choice_rows(turn)
    seen: set[int] = set()
    clickable = set()
    while True:
        seen.update(range(stage.choice_scroll, stage.choice_scroll + stage.choice_capacity))
        for rect, action in stage.hitboxes:
            assert stage.surface.get_rect().contains(rect)
            if isinstance(action, Commit):
                assert stage.choice_rect.contains(rect)
                assert stage.hit(rect.center) == action
                clickable.add(action.edge_id)
                choice = next(c for c in turn.choices if c.edge_id == action.edge_id)
                assert action.payload == choice.payload
        if stage.choice_scroll == stage.max_choice_scroll:
            break
        stage.scroll_text(ScrollText("choices", 1, page=True))
        stage.draw(turn)
        assert stage.scroll == stage.max_scroll
    assert seen == set(range(len(rows)))
    assert clickable == {c.edge_id for c in turn.choices if c.available and c.accepts is None}

    for choice in turn.choices:
        wording = " ".join(row.text.split(" ", 1)[1] for row in rows if row.choice is choice)
        wording = " ".join(wording.split())
        assert " ".join(choice.text.split()) in wording
        if choice.unavailable_reason:
            assert " ".join(choice.unavailable_reason.split()) in wording


def test_long_tokens_and_single_oversized_choice_do_not_lose_text(stage: Stage) -> None:
    token = "abcdefghij" * 300
    choice = Choice(edge_id=uuid4(), text=token)
    turn = Turn(step=1, lines=[Line(text=token)], choices=[choice])
    stage.draw(turn)
    assert "".join(row.text for row in stage._rows(turn, [], pixel_width=stage.prose_rect.width - 18 * stage.density)) == token
    rows = stage._choice_rows(turn)
    assert "".join(row.text[3:] for row in rows) == token
    assert len(rows) > stage.choice_capacity
    assert all(stage.font.size(row.text)[0] <= stage.logical_size[0] - 2 * stage.row_text_left for row in rows)
    stage.scroll_text(ScrollText("choices", 10000))
    stage.draw(turn)
    assert stage.choice_scroll == stage.max_choice_scroll
    assert any(isinstance(action, Commit) and action.edge_id == choice.edge_id for _, action in stage.hitboxes)


def test_redraw_keeps_positions_new_turn_resets_and_reflow_clamps(stage: Stage) -> None:
    turn = crowded()
    stage.draw(turn)
    stage.scroll_text(ScrollText("prose", 2))
    stage.scroll_text(ScrollText("choices", 3))
    stage.draw(turn)
    assert (stage.scroll, stage.choice_scroll) == (2, 3)
    stage.choice_fraction = 0.6
    stage.draw(turn)
    assert (stage.scroll, stage.choice_scroll) == (2, 3)
    stage.draw(Turn(step=2, lines=[Line(text="new opening")], choices=turn.choices))
    assert (stage.scroll, stage.choice_scroll) == (0, 0)
    stage.draw(Turn(step=3))
    assert stage.max_scroll == stage.max_choice_scroll == 0


def test_pointer_controls_and_wheel_target_only_their_region(stage: Stage) -> None:
    turn = crowded()
    stage.draw(turn)
    for region, rect in [("prose", stage.prose_rect), ("choices", stage.choice_rect)]:
        assert stage.wheel(rect.center, 1) == ScrollText(region, 1)
        controls = [(box, action) for box, action in stage.hitboxes if isinstance(action, ScrollText) and action.region == region]
        assert len(controls) == 1
        box, action = controls[0]
        assert stage.hit(box.center) == action
        stage.scroll_text(action)
        assert (stage.scroll if region == "prose" else stage.choice_scroll) == (stage.prose_capacity if region == "prose" else stage.choice_capacity)
    assert stage.wheel((0, 0), 1) is None


@pytest.mark.parametrize("fraction", [0.2, 0.6])
def test_configured_allocations_leave_both_views_usable(stage: Stage, fraction: float) -> None:
    stage.choice_fraction = fraction
    stage.draw(crowded())
    assert stage.prose_capacity >= 1 and stage.choice_capacity >= 1
    assert stage.prose_rect.bottom <= stage.choice_rect.top
    assert stage.surface.get_rect().contains(stage.choice_rect)


def test_overflow_headers_keep_the_rows_margins_and_the_scene_beneath(
    stage: Stage, monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A header is washed like the rows it pages, inside the frame's margins
    # rather than edge to edge. Over choices it leaves the scene showing
    # beneath it, as the choices do between themselves.
    washed: list[pygame.Rect] = []
    wash = stage._wash

    def record(rect: pygame.Rect, colour: tuple[int, int, int]) -> None:
        washed.append(rect)
        wash(rect, colour)

    monkeypatch.setattr(stage, "_wash", record)
    stage.draw(crowded())
    above_choices = stage.choice_rect.top - stage.choice_pitch
    headers = [rect for rect in washed if rect.top in (stage.prose_top, above_choices)]
    assert len(headers) == 2
    assert all(0 < rect.left and rect.right < stage.logical_size[0] for rect in headers)
    assert max(rect.bottom for rect in headers if rect.top == above_choices) < stage.choice_rect.top


def test_short_turn_has_no_overflow_controls(stage: Stage) -> None:
    stage.draw(Turn(step=1, lines=[Line(text="A short turn.")],
                    choices=[Choice(edge_id=uuid4(), text="Continue")]))
    assert stage.max_scroll == stage.max_choice_scroll == 0
    assert not any(isinstance(action, ScrollText) for _, action in stage.hitboxes)
