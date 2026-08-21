"""Tests for the pure bounded call-response dominance composer."""

from __future__ import annotations

import pytest

from tangl.core import DispatchLayer, Priority, Selector
from tangl.mechanics.games import (
    CallResponseGame,
    CallResponseGameHandler,
    CallResponsePhrase,
    DominanceContribution,
    PhraseType,
    RoundResult,
    compose_dominance_schedule,
)


@pytest.fixture(autouse=True)
def reset_phrase_types() -> None:
    """Keep singleton definitions local to each pure-composition test."""

    PhraseType.clear_instances()
    yield
    PhraseType.clear_instances()


def phrase(
    label: str,
    *,
    roles: tuple[str, ...],
    tags: set[str] | None = None,
    contributions: tuple[DominanceContribution, ...] = (),
) -> PhraseType:
    """Create one phrase definition with optional immutable base relations."""

    return PhraseType(
        label=label,
        text=label.replace("_", " "),
        roles=roles,
        tags=tags or set(),
        base_contributions=contributions,
    )


def contribution(
    *,
    call: Selector,
    response: Selector,
    result: str,
    layer: DispatchLayer = DispatchLayer.AUTHOR,
    priority: Priority = Priority.NORMAL,
    source_id: str,
) -> DominanceContribution:
    """Build a contribution with explicit selector and ordering values."""

    return DominanceContribution(
        call_selector=call,
        response_selector=response,
        result=result,
        dispatch_layer=layer,
        priority=priority,
        source_id=source_id,
    )


def test_undeclared_pair_remains_absent_from_the_schedule() -> None:
    call = phrase("call", roles=("call",))
    response = phrase("response", roles=("response",))

    composition = compose_dominance_schedule([call], [response])

    assert composition.schedule == []
    assert composition.diagnostics == []


def test_base_contribution_uses_existing_identifier_and_tag_selectors() -> None:
    response = phrase("beaujolais", roles=("response",), tags={"reversal"})
    call = phrase(
        "dairy_farmer",
        roles=("call",),
        tags={"insult"},
        contributions=(
            contribution(
                call=Selector(has_tags={"insult"}),
                response=Selector(has_identifier="beaujolais"),
                result="match",
                source_id="dairy-farmer",
            ),
        ),
    )

    composition = compose_dominance_schedule([call], [response])

    assert composition.schedule[0].model_dump() == {
        "call_phrase_id": "dairy_farmer",
        "response_phrase_id": "beaujolais",
        "matched": True,
        "source_id": "dairy-farmer",
    }


def test_role_ineligible_and_unrelated_phrase_types_are_not_composed() -> None:
    call = phrase("call", roles=("call",))
    ineligible_response = phrase("not_response", roles=("call",))
    unrelated = phrase(
        "unrelated",
        roles=("call", "response"),
        contributions=(
            contribution(
                call=Selector(),
                response=Selector(),
                result="match",
                source_id="unrelated-rule",
            ),
        ),
    )

    composition = compose_dominance_schedule([call, unrelated], [ineligible_response])

    assert composition.schedule == []
    assert unrelated in PhraseType.all_instances()


def test_only_participating_phrase_definitions_supply_base_contributions() -> None:
    call = phrase("call", roles=("call",))
    response = phrase("response", roles=("response",))
    phrase(
        "unrelated",
        roles=("call", "response"),
        contributions=(
            contribution(
                call=Selector(),
                response=Selector(),
                result="match",
                source_id="global-looking-but-unrelated",
            ),
        ),
    )

    composition = compose_dominance_schedule([call], [response])

    assert composition.schedule == []


def test_local_contribution_overrides_lower_layer_base_rule() -> None:
    call = phrase(
        "dairy_farmer",
        roles=("call",),
        tags={"insult"},
        contributions=(
            contribution(
                call=Selector(has_tags={"insult"}),
                response=Selector(has_identifier="beaujolais"),
                result="miss",
                layer=DispatchLayer.APPLICATION,
                source_id="imported-base",
            ),
        ),
    )
    response = phrase("beaujolais", roles=("response",))
    local = contribution(
        call=Selector(has_tags={"insult"}),
        response=Selector(has_identifier="beaujolais"),
        result="match",
        layer=DispatchLayer.LOCAL,
        source_id="beaujolais",
    )

    composition = compose_dominance_schedule([call], [response], contributions=[local])

    assert composition.schedule[0].matched is True
    assert composition.schedule[0].source_id == "beaujolais"


def test_equal_tier_negative_wins_and_reports_a_deterministic_contradiction() -> None:
    call = phrase("call", roles=("call",))
    response = phrase("response", roles=("response",))
    positive = contribution(
        call=Selector(),
        response=Selector(),
        result="match",
        layer=DispatchLayer.LOCAL,
        priority=Priority.LATE,
        source_id="positive",
    )
    negative = contribution(
        call=Selector(),
        response=Selector(),
        result="miss",
        layer=DispatchLayer.LOCAL,
        priority=Priority.LATE,
        source_id="negative",
    )

    first = compose_dominance_schedule([call], [response], contributions=[positive, negative])
    second = compose_dominance_schedule([call], [response], contributions=[negative, positive])

    assert first == second
    assert first.schedule[0].matched is False
    assert first.schedule[0].source_id == "negative"
    assert first.diagnostics[0].model_dump() == {
        "call_phrase_id": "call",
        "response_phrase_id": "response",
        "dispatch_layer": DispatchLayer.LOCAL,
        "priority": Priority.LATE,
        "positive_source_ids": ("positive",),
        "negative_source_ids": ("negative",),
    }


def test_broken_selector_failure_is_not_converted_to_a_miss() -> None:
    call = phrase("call", roles=("call",))
    response = phrase("response", roles=("response",))
    broken = contribution(
        call=Selector(predicate=lambda _: (_ for _ in ()).throw(RuntimeError("broken rule"))),
        response=Selector(),
        result="match",
        source_id="broken",
    )

    with pytest.raises(RuntimeError, match="broken rule"):
        compose_dominance_schedule([call], [response], contributions=[broken])


def test_composed_schedule_drives_the_unchanged_fixed_game_kernel() -> None:
    call = phrase("call", roles=("call",))
    response = phrase("response", roles=("response",))
    composition = compose_dominance_schedule(
        [call],
        [response],
        contributions=[
            contribution(
                call=Selector(has_identifier="call"),
                response=Selector(has_identifier="response"),
                result="match",
                source_id="composed",
            ),
        ],
    )
    game = CallResponseGame(
        phrases={
            call.label: CallResponsePhrase(text=call.text, roles=list(call.roles)),
            response.label: CallResponsePhrase(
                text=response.text,
                roles=list(response.roles),
            ),
        },
        player_phrase_ids=[call.label],
        opponent_phrase_ids=[response.label],
        schedule=composition.schedule,
        scoring_n=1,
    )
    handler = CallResponseGameHandler()
    handler.setup(game)

    result = handler.receive_move(game, call.label)

    assert result is RoundResult.LOSE
    assert game.last_exchange is not None
    assert game.last_exchange.match_source_id == "composed"
