"""Tests for the shared game-token substrate."""

from __future__ import annotations

from tangl.core import Token
from tangl.story.concepts.asset import AssetType, AssetWallet, CountableAsset
from tangl.mechanics.games import (
    DEFAULT_PIECE_LABEL,
    FungibleGameToken,
    GameTokenType,
    RacingPieceType,
    TrackGame,
    TrackGameHandler,
    TrackMove,
    TrackToken,
    dominant_affiliation,
    value_by_affiliation,
)


class TestSubstrateShape:
    """Game tokens are assets, not a parallel species."""

    def test_fungible_tokens_are_countable_assets(self) -> None:
        assert issubclass(FungibleGameToken, CountableAsset)

    def test_piece_definitions_are_asset_types(self) -> None:
        assert issubclass(GameTokenType, AssetType)

    def test_racing_pieces_are_canonical_tokens(self) -> None:
        assert issubclass(TrackToken, Token)


class TestWalletHelpers:
    """The token rung groups fungible markers by affiliation."""

    def _wallet(self) -> AssetWallet:
        for label, affiliation, value in [
            ("gt_brute", "rock", 1),
            ("gt_heavy_brute", "rock", 3),
            ("gt_fast", "paper", 1),
        ]:
            if FungibleGameToken.get_instance(label) is None:
                FungibleGameToken(label=label, affiliation=affiliation, value=value)
        return AssetWallet(amounts={"gt_brute": 2, "gt_heavy_brute": 1, "gt_fast": 4})

    def test_value_is_weighted_by_definition(self) -> None:
        totals = value_by_affiliation(self._wallet())

        assert totals["rock"] == 5.0     # 2x1 plus 1x3
        assert totals["paper"] == 4.0

    def test_dominant_affiliation_uses_weight_not_count(self) -> None:
        # paper has more markers; rock has more force
        assert dominant_affiliation(self._wallet()) == "rock"

    def test_empty_wallet_has_no_dominant_affiliation(self) -> None:
        assert dominant_affiliation(AssetWallet()) is None

    def test_unknown_labels_are_ignored(self) -> None:
        wallet = AssetWallet(amounts={"not_a_registered_token": 5})

        assert value_by_affiliation(wallet) == {}


class TestPiecesAsGraphCapableTokens:
    """What the canonical substrate buys the board rung."""

    def _game(self) -> tuple[TrackGame, TrackGameHandler]:
        game = TrackGame(
            track_length=8,
            finish_distance=10,
            tokens_per_side=2,
            roll_sequence=[2],
            opponent_strategy=None,
        )
        handler = TrackGameHandler()
        handler.setup(game)
        return game, handler

    def test_pieces_delegate_to_a_frozen_definition(self) -> None:
        game, _ = self._game()
        piece = game.tokens[0]

        assert piece.token_from == DEFAULT_PIECE_LABEL
        assert piece.get_label() == DEFAULT_PIECE_LABEL
        # Definition state is shared and untouched by per-piece mutation.
        piece.position = 4
        assert RacingPieceType.get_instance(DEFAULT_PIECE_LABEL).position is None

    def test_a_world_may_supply_its_own_piece_definition(self) -> None:
        if RacingPieceType.get_instance("oak_marble") is None:
            RacingPieceType(
                label="oak_marble",
                affiliation="marble",
                description="a hand-drilled oak marble",
            )
        game = TrackGame(piece_type="oak_marble", tokens_per_side=1, roll_sequence=[2])
        TrackGameHandler().setup(game)

        assert all(piece.token_from == "oak_marble" for piece in game.tokens)
        assert game.tokens[0].affiliation == "marble"

    def test_a_piece_can_be_moved_from_outside_the_game(self) -> None:
        game, handler = self._game()
        piece = game.get_token("player", 0)

        # Reach in and place it, the way a world event might.
        piece.position = 7

        assert game.occupant_at(7) is piece
        moves = handler.get_available_moves(game)
        assert TrackMove(token_id=0) in moves

    def test_pieces_survive_a_round_trip_through_the_game_state(self) -> None:
        game, handler = self._game()
        handler.receive_move(game, TrackMove(token_id=0))

        dumped = game.model_dump()
        restored = TrackGame.model_validate(dumped)

        assert [piece.position for piece in restored.tokens] == [
            piece.position for piece in game.tokens
        ]
        assert all(isinstance(piece, TrackToken) for piece in restored.tokens)
