"""Tests for blackjack contest mechanics."""

from __future__ import annotations

from tangl.core import Graph, Token
from tangl.mechanics.games import HasGame
from tangl.mechanics.games.blackjack_game import (
    BlackjackGame,
    BlackjackGameHandler,
    BlackjackMove,
    PlayingCard,
    PlayingCardType,
)
from tangl.mechanics.games.handlers import inject_game_context, provision_game_moves
from tangl.story import Action, Block
from tangl.vm import Frame, Ledger, TraversableEdge as ChoiceEdge


def _card(rank: int, suit: str) -> PlayingCard:
    return PlayingCard.of(rank, suit)


def _make_ledger(graph: Graph, start_node: Block) -> Ledger:
    return Ledger.from_graph(graph=graph, entry_id=start_node.uid)


def _single_choice_action(ledger: Ledger) -> Action:
    actions = [edge for edge in ledger.cursor.edges_out() if isinstance(edge, Action)]
    assert len(actions) == 1
    return actions[0]


class BlackjackBlock(HasGame, Block):
    """Test block embedding a blackjack game."""

    _game_class = BlackjackGame
    _game_handler_class = BlackjackGameHandler


class TestBlackjackCore:
    """Core blackjack state and resolution tests."""

    def test_setup_deals_two_cards_to_each_side(self) -> None:
        game = BlackjackGame(deal_bias="dramatic")
        handler = BlackjackGameHandler()

        handler.setup(game)

        assert len(game.player_hand) == 2
        assert len(game.dealer_hand) == 2
        assert len(game.visible_dealer_hand) == 1

    def test_stand_resolves_showdown(self) -> None:
        game = BlackjackGame()
        handler = BlackjackGameHandler()
        handler.setup(game)

        game.player_hand = [_card(10, "h"), _card(8, "s")]
        game.dealer_hand = [_card(9, "d"), _card(7, "c")]
        game.card_deck = [_card(10, "c")]

        result = handler.receive_move(game, BlackjackMove.STAND)

        assert result.name == "WIN"
        assert game.result.name == "WIN"
        assert game.dealer_total > 21

    def test_hit_can_continue_without_terminal_result(self) -> None:
        game = BlackjackGame()
        handler = BlackjackGameHandler()
        handler.setup(game)

        game.player_hand = [_card(7, "h"), _card(8, "s")]
        game.dealer_hand = [_card(6, "d"), _card(10, "c")]
        game.card_deck = [_card(2, "c"), _card(10, "d")]

        result = handler.receive_move(game, BlackjackMove.HIT)

        assert result.name == "CONTINUE"
        assert game.result.name == "IN_PROCESS"
        assert game.player_total == 17
        assert game.last_round is not None
        assert game.last_round.notes["player_drew"] == "2C"

    def test_player_advantage_bias_stacks_opening_deal(self) -> None:
        game = BlackjackGame(deal_bias="player_advantage")
        handler = BlackjackGameHandler()

        handler.setup(game)

        assert game.player_total == 19
        assert game.visible_dealer_hand[0].short_name == "6C"

    def test_namespace_hides_dealer_total_until_terminal(self) -> None:
        game = BlackjackGame(deal_bias="player_advantage", reveal_policy="upcard")
        handler = BlackjackGameHandler()
        handler.setup(game)

        ns = game.to_namespace()

        assert ns["blackjack_player_total"] == 19
        assert ns["blackjack_dealer_total"] is None
        assert ns["blackjack_dealer_upcard"] == "6C"


class TestBlackjackIntegration:
    """VM and HasGame integration tests for blackjack."""

    def test_move_provision_uses_readable_labels(self) -> None:
        graph = Graph(label="blackjack_labels")
        block = graph.add_node(kind=BlackjackBlock, label="table")
        block.game_handler.setup(block.game)
        block.game.player_hand = [_card(7, "h"), _card(8, "s")]
        block.game.dealer_hand = [_card(6, "d"), _card(10, "c")]
        block.game.card_deck = [_card(2, "c"), _card(10, "d")]
        block.game.player_stood = False

        frame = Frame(graph=graph, cursor=block)
        ctx = frame._make_ctx()
        object.__setattr__(ctx, "_frame", frame)

        actions = provision_game_moves(block, ctx=ctx)

        assert [action.label for action in actions] == ["Hit", "Stand"]

    def test_blackjack_routes_to_victory_with_stacked_opening_hand(self) -> None:
        graph = Graph(label="blackjack_flow")
        intro = graph.add_node(kind=Block, label="intro")
        victory = graph.add_node(kind=Block, label="victory")
        defeat = graph.add_node(kind=Block, label="defeat")

        block = BlackjackBlock.create_game_block(
            graph=graph,
            game_class=BlackjackGame,
            handler_class=BlackjackGameHandler,
            victory_dest=victory,
            defeat_dest=defeat,
            label="table",
        )
        block.game.deal_bias = "player_advantage"
        block.game_handler.setup(block.game)
        block.game.card_deck = [_card(10, "c")]

        intro_to_table = ChoiceEdge(
            graph=graph,
            predecessor_id=intro.uid,
            successor_id=block.uid,
            label="Take a seat",
        )

        ledger = _make_ledger(graph, intro)
        ledger.resolve_choice(intro_to_table.uid)

        actions = [edge for edge in ledger.cursor.edges_out() if isinstance(edge, Action)]
        stand = next(action for action in actions if action.label == "Stand")
        ledger.resolve_choice(stand.uid, choice_payload=stand.payload)

        assert ledger.cursor_id == victory.uid
        fragments = ledger.get_journal()
        content = " ".join(getattr(fragment, "content", "") for fragment in fragments)
        assert "dealer reveals" in content.lower()

    def test_context_exports_blackjack_pressure_signals(self) -> None:
        graph = Graph(label="blackjack_context")
        block = graph.add_node(kind=BlackjackBlock, label="table")
        block.game_handler.setup(block.game)

        frame = Frame(graph=graph, cursor=block)
        ctx = frame._make_ctx()
        object.__setattr__(ctx, "_frame", frame)

        namespace = inject_game_context(block, ctx=ctx)

        assert namespace["blackjack_player_total"] >= 0
        assert namespace["blackjack_dealer_visible_hand"]


class TestCardsAsTokens:
    """Cards are tokens over a shared deck definition."""

    def test_a_card_is_a_canonical_token(self) -> None:
        assert issubclass(PlayingCard, Token)

    def test_rank_and_suit_come_from_the_frozen_definition(self) -> None:
        card = PlayingCard.of(12, "d")

        assert card.short_name == "QD"
        assert (card.rank, card.suit) == (12, "d")
        assert card.token_from == "QD"

    def test_suit_doubles_as_the_affiliation(self) -> None:
        # which is what gives suit-sensitive card games the shared helpers
        assert PlayingCard.of(7, "h").affiliation == "h"

    def test_two_dealt_cards_share_one_definition(self) -> None:
        first = PlayingCard.of(1, "s")
        second = PlayingCard.of(1, "s")

        assert first.uid != second.uid
        assert first.token_from == second.token_from

    def test_face_up_is_per_card_not_per_definition(self) -> None:
        card = PlayingCard.of(1, "s")
        card.face_up = False

        assert PlayingCardType.get_instance("AS").face_up is True
        assert PlayingCard.of(1, "s").face_up is True

    def test_a_fresh_deck_holds_fifty_two_distinct_cards(self) -> None:
        deck = PlayingCard.fresh_deck(seed=3)

        assert len(deck) == 52
        assert len({card.short_name for card in deck}) == 52


class TestHoleCard:
    """The dealer's hole card is face down rather than positionally hidden."""

    def test_the_second_dealer_card_is_dealt_face_down(self) -> None:
        game = BlackjackGame(shuffle_seed=5)
        BlackjackGameHandler().setup(game)

        assert [card.face_up for card in game.dealer_hand] == [True, False]
        assert len(game.visible_dealer_hand) == 1

    def test_turning_the_hole_card_over_reveals_it(self) -> None:
        game = BlackjackGame(shuffle_seed=5)
        BlackjackGameHandler().setup(game)

        game.dealer_hand[1].face_up = True

        assert len(game.visible_dealer_hand) == 2
        assert game.to_namespace()["blackjack_dealer_visible_total"] == game.dealer_total

    def test_a_terminal_hand_shows_everything(self) -> None:
        game = BlackjackGame(shuffle_seed=5)
        handler = BlackjackGameHandler()
        handler.setup(game)

        while handler.get_available_moves(game):
            handler.receive_move(game, BlackjackMove.STAND)

        assert game.result.is_terminal
        assert len(game.visible_dealer_hand) == len(game.dealer_hand)
