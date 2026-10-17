"""Offer authority, pure validation, and parameter completion before traversal."""

from __future__ import annotations

import random
from typing import ClassVar

import pytest
from pydantic import Field

from tangl.core import Graph
from tangl.mechanics.games import (
    Game, GameHandler, GamePhase, HasGame, NimGame, NimGameHandler, NimMove, RoundRecord, RoundResult,
)
from tangl.mechanics.games.rps_game import RpsGame, RpsGameHandler, RpsMove
from tangl.persistence.serializers import JsonSerializationHandler as Json
from tangl.story import Action, Block
from tangl.vm import Frame, ResolutionPhase
from tangl.vm.dispatch import do_validate


class BoundRpsBlock(HasGame, Block):
    _game_class = RpsGame
    _game_handler_class = RpsGameHandler


class StableNimHandler(NimGameHandler):
    dynamic_move_projection = False


class SoloSelectorNimGame(NimGame):
    opponent_strategy: str | None = None
    opening_heaps: dict[str, int] = {"heap": 20, "other": 10}


class SelectorNimBlock(HasGame, Block):
    _game_class = SoloSelectorNimGame
    _game_handler_class = StableNimHandler


class SymbolGame(Game[str]):
    opponent_strategy: str | None = None
    history: list[RoundRecord[str]] = Field(
        default_factory=list, json_schema_extra={"include": True},
    )


class SymbolHandler(GameHandler[SymbolGame]):
    game_cls: ClassVar[type[Game]] = SymbolGame
    move_cls: ClassVar[type] = str
    dynamic_move_projection = False

    def get_available_moves(self, game: SymbolGame) -> list[str]:
        return ["rock", "paper", "scissors"]

    def resolve_move_payload(
        self, game: SymbolGame, move: str, payload: dict[str, object], *,
        offered_payload: dict[str, object],
    ) -> str:
        if move != "choose_symbol":
            return super().resolve_move_payload(
                game, move, payload, offered_payload=offered_payload,
            )
        self.check_move_payload(
            payload, offered_payload=offered_payload, input_fields=frozenset({"move"}),
        )
        return self.reconstruct_move(payload["move"])

    def resolve_round(
        self, game: SymbolGame, player_move: str, opponent_move: str | None,
    ) -> RoundResult:
        return RoundResult.DRAW


class SymbolBlock(HasGame, Block):
    _game_class = SymbolGame
    _game_handler_class = SymbolHandler


def _frame(
    block_class: type[BoundRpsBlock | SelectorNimBlock | SymbolBlock],
    offer: dict[str, object], *, setup: bool = True,
) -> tuple[Frame, Action]:
    graph = Graph()
    host = graph.add_node(kind=block_class, label="host")
    if setup:
        host.game_handler.setup(host.game)
    edge = Action(graph=graph, predecessor_id=host.uid, successor_id=host.uid, payload=offer)
    # Both the authoritative offer and game state cross actual JSON text.
    restored = Graph.structure(Json.deserialize(Json.serialize(graph.unstructure())))
    return Frame(graph=restored, cursor=restored.get(host.uid)), restored.get(edge.uid)


def _snapshot(frame: Frame) -> tuple:
    return (Json.serialize(frame.graph.unstructure()), frame.cursor_id, frame.cursor_steps,
            tuple(frame.cursor_trace), random.getstate())


@pytest.mark.parametrize("payload", [
    {"move": "paper"}, {"move": "not_a_symbol"}, {"move": {}},
    {"move": "rock", "quantity": 1}, {"move": "rock", "unknown": True}, [],
])
def test_bound_move_rejection_does_not_advance_or_mutate(payload: object) -> None:
    frame, edge = _frame(BoundRpsBlock, {"move": RpsMove.ROCK})
    before = _snapshot(frame)
    with pytest.raises(ValueError):
        frame.resolve_choice(edge, choice_payload=payload)
    assert _snapshot(frame) == before


@pytest.mark.parametrize("payload", [None, {"move": "rock"}])
def test_bound_move_accepts_omission_and_unchanged_json_echo(payload: dict | None) -> None:
    frame, edge = _frame(BoundRpsBlock, {"move": RpsMove.ROCK})
    frame.resolve_choice(edge, choice_payload=payload)
    assert frame.cursor.game.history[-1].player_move is RpsMove.ROCK


def test_repeated_validation_is_pure_and_nim_selector_completes_before_legality() -> None:
    frame, edge = _frame(SelectorNimBlock, {"move": NimMove("heap", 0)})
    ctx = frame._make_ctx(incoming_edge=edge, incoming_payload={**edge.payload, "quantity": 1})
    ctx.current_phase = ResolutionPhase.VALIDATE
    before = _snapshot(frame)
    for _ in range(3):
        assert do_validate(edge, ctx=ctx)
    assert _snapshot(frame) == before
    frame.resolve_choice(edge, choice_payload={"quantity": 1})
    assert frame.cursor.game.history[-1].player_move == NimMove("heap", 1)
    frame.resolve_choice(edge, choice_payload={"move": edge.payload["move"], "quantity": 2})
    assert frame.cursor.game.history[-1].player_move == NimMove("heap", 2)
    assert list(frame.cursor.edges_out()) == [edge]


@pytest.mark.parametrize("quantity", [0, -1, 4, "2", True, None])
def test_nim_bad_quantity_rejects_before_any_mutation(quantity: object) -> None:
    frame, edge = _frame(SelectorNimBlock, {"move": NimMove("heap", 0)})
    before = _snapshot(frame)
    with pytest.raises(ValueError):
        frame.resolve_choice(edge, choice_payload={"quantity": quantity})
    assert _snapshot(frame) == before


@pytest.mark.parametrize("move", [
    {"pile": "other", "count": 0},
    {"pile": "heap", "count": 0, "unknown": "not part of this move"},
    {"pile": "heap", "count": []},
])
def test_nim_rejects_changed_heap_and_malformed_structured_echo(move: dict[str, object]) -> None:
    frame, edge = _frame(SelectorNimBlock, {"move": NimMove("heap", 0)})
    before = _snapshot(frame)
    with pytest.raises(ValueError):
        frame.resolve_choice(edge, choice_payload={"move": move, "quantity": 1})
    assert _snapshot(frame) == before


def test_native_dataclass_offer_accepts_unchanged_json_echo() -> None:
    game = NimGame()
    handler = NimGameHandler()
    handler.setup(game)
    move = handler.resolve_selected_move(
        game, offered_payload={"move": NimMove("heap", 0)},
        payload={"move": {"pile": "heap", "count": 0}, "quantity": 2},
    )
    assert move == NimMove("heap", 2)


def test_one_symbol_offer_accepts_multiple_legal_move_values() -> None:
    frame, edge = _frame(SymbolBlock, {"move": "choose_symbol"})
    for symbol in ("rock", "paper"):
        wire = Json.deserialize(Json.serialize({"move": symbol}))
        frame.resolve_choice(edge, choice_payload=wire)
    assert [record.player_move for record in frame.cursor.game.history] == ["rock", "paper"]
    assert list(frame.cursor.edges_out()) == [edge]
    before = _snapshot(frame)
    with pytest.raises(ValueError):
        frame.resolve_choice(edge, choice_payload={"move": "water"})
    assert _snapshot(frame) == before


@pytest.mark.parametrize("state_exists", [False, True])
def test_validation_does_not_initialize_pending_game(state_exists: bool) -> None:
    frame, edge = _frame(BoundRpsBlock, {"move": RpsMove.ROCK}, setup=False)
    if state_exists:
        assert frame.cursor.game.phase is GamePhase.PENDING
    before = _snapshot(frame)
    reason = "READY game" if state_exists else "initialized game state"
    with pytest.raises(ValueError, match=reason):
        frame.resolve_choice(edge)
    assert _snapshot(frame) == before


def test_receive_move_rejects_illegal_move_before_round_phase_and_opponent_changes() -> None:
    game = NimGame()
    handler = NimGameHandler()
    handler.setup(game)
    before = Json.serialize(game.unstructure()), random.getstate()
    with pytest.raises(ValueError, match="Invalid move"):
        handler.receive_move(game, NimMove("heap", 99))
    assert (Json.serialize(game.unstructure()), random.getstate()) == before


def test_non_game_action_keeps_normal_payload_merge() -> None:
    graph = Graph()
    host = graph.add_node(kind=Block)
    edge = Action(graph=graph, predecessor_id=host.uid, successor_id=host.uid,
                  payload={"move": "authored", "fixed": 1})
    frame = Frame(graph=graph, cursor=host)
    frame.resolve_choice(edge, choice_payload={"move": "client", "extra": 2})
    assert frame.selected_payload == {"move": "client", "fixed": 1, "extra": 2}
    assert edge.payload == {"move": "authored", "fixed": 1}
