"""Tests for the shared picking kernel."""

from __future__ import annotations

from tangl.mechanics.games import PickingGame, PickingGameHandler, PickingMove, RoundResult


class SamplePickingGame(PickingGame):
    """Minimal picking game for kernel tests."""

    visible_items: list[str] = ["ledger", "seal"]
    inspectable_targets: list[str] = ["seal", "stamp"]
    hidden_facts: dict[str, str] = {
        "seal": "The wax has cracked around the wrong crest.",
    }
    decision_options: list[str] = ["allow", "deny"]
    correct_decision: str = "deny"


class SamplePickingHandler(PickingGameHandler[SamplePickingGame]):
    """Simple kernel consumer for shared behavior tests."""

    def resolve_inspection(
        self,
        game: SamplePickingGame,
        target: str,
        detail: dict[str, object],
    ) -> RoundResult:
        finding = game.hidden_facts.get(target, "Nothing unusual turns up.")
        if target in game.hidden_facts:
            game.revealed_findings[target] = finding
        detail["finding"] = finding
        detail["outcome"] = "continue"
        return RoundResult.CONTINUE

    def resolve_decision(
        self,
        game: SamplePickingGame,
        target: str,
        detail: dict[str, object],
    ) -> RoundResult:
        if target == game.correct_decision:
            game.score["player"] = 1
            detail["outcome"] = "correct"
            return RoundResult.WIN

        game.score["opponent"] = 1
        detail["outcome"] = "wrong"
        return RoundResult.LOSE


class TestPickingKernel:
    """Core tests for the shared picking base classes."""

    def test_inspect_and_decide_moves_use_structured_move_type(self) -> None:
        game = SamplePickingGame()
        handler = SamplePickingHandler()
        handler.setup(game)

        moves = handler.get_available_moves(game)

        assert PickingMove(kind="inspect", target="seal") in moves
        assert PickingMove(kind="decide", target="deny") in moves

    def test_inspection_updates_revealed_findings(self) -> None:
        game = SamplePickingGame()
        handler = SamplePickingHandler()
        handler.setup(game)

        result = handler.receive_move(game, PickingMove(kind="inspect", target="seal"))

        assert result == RoundResult.CONTINUE
        assert game.inspected_targets == ["seal"]
        assert "seal" in game.revealed_findings
        assert game.last_round is not None
        assert game.last_round.notes["revealed_findings"]["seal"].startswith("The wax")

    def test_namespace_exports_generic_picking_state(self) -> None:
        game = SamplePickingGame()
        handler = SamplePickingHandler()
        handler.setup(game)
        handler.receive_move(game, PickingMove(kind="inspect", target="seal"))

        namespace = game.to_namespace()

        assert namespace["picking_visible_items"] == ["ledger", "seal"]
        assert namespace["picking_inspected_targets"] == ["seal"]
        assert namespace["picking_num_findings"] == 1
