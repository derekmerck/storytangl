"""Pure directed call-response contest kernel."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import BaseModel, Field

from tangl.journal.fragments import ContentFragment
from tangl.vm.ctx import VmPhaseCtx

from .enums import RoundResult
from .game import Game
from .handler import GameHandler

PhraseRole = Literal["call", "response"]


class CallResponsePhrase(BaseModel):
    """One fixed phrase's display text and available exchange roles.

    Why
    ---
    The kernel needs a small, portable value for fixed phrase-id sets before a
    catalog-backed phrase type exists.

    API
    ---
    ``text`` is the CLI-facing phrase; ``roles`` permits ``call``,
    ``response``, or both.
    """

    text: str
    roles: list[PhraseRole]


class DominanceMatch(BaseModel):
    """An authored result for one ordered ``(call_id, response_id)`` pair.

    Why
    ---
    Directed pair values make matches explainable and remain portable without
    tuple-keyed mappings.

    API
    ---
    ``matched`` distinguishes a positive response from an explicit negative
    decision; absent pairs are ordinary default misses.
    """

    call_phrase_id: str
    response_phrase_id: str
    matched: bool
    source_id: str


class CallResponseExchange(BaseModel):
    """Typed, durable evidence of one resolved call-response exchange.

    Why
    ---
    The acquisition shell must consume the exact deployed phrases and result
    without reading rendered journal prose.

    API
    ---
    The game retains this value for its latest exchange; its plain mapping is
    copied into :class:`RoundRecord.notes` for durable round history.
    """

    call_phrase_id: str
    response_phrase_id: str
    matched: bool
    match_source_id: str | None
    additional_exposed_phrase_ids: list[str]
    initiative_before: bool
    initiative_after: bool


class CallResponseGame(Game[str]):
    """Persistent state for a fixed-list directed call-response contest.

    Why
    ---
    Models an ordered exchange where initiative determines whether each side
    calls or answers, while all mutable score and history state stays on the
    ordinary :class:`Game` instance.

    Key Features
    ------------
    - fixed player and opponent phrase-id sets;
    - portable directed dominance schedule with authored source ids;
    - initiative that flips only when a response matches a call.

    API
    ---
    Configure ``phrases``, phrase-id sets, and ``schedule`` before the normal
    :class:`CallResponseGameHandler` accepted-entry setup.

    Notes
    -----
    Catalogs, badges, and repertoire ownership deliberately belong to the next
    layer; this game carries only its settled fixed inputs.
    """

    phrases: dict[str, CallResponsePhrase] = Field(default_factory=dict)
    player_phrase_ids: list[str] = Field(default_factory=list)
    opponent_phrase_ids: list[str] = Field(default_factory=list)
    schedule: list[DominanceMatch] = Field(default_factory=list)
    initial_player_has_initiative: bool = True
    player_has_initiative: bool = Field(
        default=True,
        json_schema_extra={"reset_field": True},
    )
    last_exchange: CallResponseExchange | None = Field(
        default=None,
        json_schema_extra={"reset_field": True},
    )
    opponent_strategy: str | None = None

    def to_namespace(self) -> dict[str, Any]:
        """Expose the current role while retaining the base game aliases."""

        namespace = super().to_namespace()
        namespace["call_response_player_has_initiative"] = self.player_has_initiative
        return namespace


class CallResponseGameHandler(GameHandler[CallResponseGame]):
    """Resolve fixed directed phrase exchanges through the ordinary game loop.

    Why
    ---
    Keeps role-sensitive move selection, deterministic opponent choices, score,
    initiative, and JOURNAL projection in the existing stateless handler seam.

    Key Features
    ------------
    - positive ordered schedule pairs answer calls;
    - opponent calls are preselected and responses are selected after a call;
    - every exchange writes stable evidence into :class:`RoundRecord.notes`.

    API
    ---
    Use :meth:`get_available_moves` and :meth:`receive_move` exactly as for
    other :class:`GameHandler` implementations.

    Notes
    -----
    Missing role-capable phrases are invalid fixed contest data, not a kernel
    fallback case. The fixed kernel deterministically selects the first legal
    opponent call, or the first positively matching response when one exists.
    """

    game_cls: ClassVar[type[Game]] = CallResponseGame

    def on_setup(self, game: CallResponseGame) -> None:
        """Validate fixed data and initialize the authored initiative."""

        self._validate_configuration(game)
        game.player_has_initiative = game.initial_player_has_initiative

    def get_available_moves(self, game: CallResponseGame) -> list[str]:
        """Return the player's phrase ids for their current exchange role."""

        role: PhraseRole = "call" if game.player_has_initiative else "response"
        return self._phrases_for_role(game, game.player_phrase_ids, role, side="player")

    def get_move_label(self, game: CallResponseGame, move: str) -> str:
        """Describe whether the selectable phrase is a call or response."""

        prefix = "Call with" if game.player_has_initiative else "Answer with"
        return f"{prefix} {game.phrases[move].text}"

    def resolve_round(
        self,
        game: CallResponseGame,
        player_move: str,
        opponent_move: str | None,
    ) -> RoundResult:
        """Resolve one ordered call/response pair and update score/initiative."""

        if player_move not in self.get_available_moves(game):
            raise ValueError(f"Player phrase is not available for this role: {player_move}")
        if opponent_move is None:
            raise RuntimeError("Call-response contests require an opponent phrase")

        initiative_before = game.player_has_initiative
        if initiative_before:
            call_phrase_id, response_phrase_id = player_move, opponent_move
        else:
            call_phrase_id, response_phrase_id = opponent_move, player_move

        match = self._schedule_match(game, call_phrase_id, response_phrase_id)
        matched = match.matched if match is not None else False
        initiative_after = not initiative_before if matched else initiative_before
        player_won = initiative_before != matched
        game.player_has_initiative = initiative_after

        if player_won:
            game.score["player"] += 1
            round_result = RoundResult.WIN
        else:
            game.score["opponent"] += 1
            round_result = RoundResult.LOSE

        game.last_exchange = CallResponseExchange(
            call_phrase_id=call_phrase_id,
            response_phrase_id=response_phrase_id,
            matched=matched,
            match_source_id=match.source_id if match is not None else None,
            additional_exposed_phrase_ids=[],
            initiative_before=initiative_before,
            initiative_after=initiative_after,
        )
        return round_result

    def build_round_notes(
        self,
        game: CallResponseGame,
        player_move: str,
        opponent_move: str | None,
        round_result: RoundResult,
    ) -> dict[str, Any]:
        """Copy the exchange evidence into the immutable round record."""

        _ = player_move, opponent_move, round_result
        if game.last_exchange is None:
            raise RuntimeError("Call-response round resolved without exchange evidence")
        return game.last_exchange.model_dump()

    def get_journal_fragments(
        self,
        game: CallResponseGame,
        *,
        ctx: VmPhaseCtx | None = None,
    ) -> list[ContentFragment] | None:
        """Render the latest exchange as a complete text presentation floor."""

        _ = ctx
        last_round = game.last_round
        if last_round is None:
            return []

        exchange = CallResponseExchange.model_validate(last_round.notes)
        response_outcome = "answers" if exchange.matched else "does not answer"
        winner = "You win" if last_round.result is RoundResult.WIN else "Opponent wins"
        initiative = "you" if exchange.initiative_after else "the opponent"
        return [
            ContentFragment(content=f"Call: {game.phrases[exchange.call_phrase_id].text}"),
            ContentFragment(
                content=(
                    f"Response: {game.phrases[exchange.response_phrase_id].text} "
                    f"{response_outcome} the call."
                )
            ),
            ContentFragment(
                content=(
                    f"{winner} the exchange. Score: you {game.score['player']}, "
                    f"opponent {game.score['opponent']}. Initiative: {initiative}."
                )
            ),
        ]

    def _preselect_opponent_move(self, game: CallResponseGame) -> None:
        if game.player_has_initiative:
            game.opponent_next_move = None
            return
        game.opponent_next_move = self._choose_opponent_phrase(game, "call")

    def _finalize_opponent_move(
        self,
        game: CallResponseGame,
        player_move: str,
    ) -> str | None:
        if not game.player_has_initiative:
            return game.opponent_next_move
        return self._choose_opponent_phrase(game, "response", call_phrase_id=player_move)

    def _choose_opponent_phrase(
        self,
        game: CallResponseGame,
        role: PhraseRole,
        *,
        call_phrase_id: str | None = None,
    ) -> str:
        choices = self._phrases_for_role(game, game.opponent_phrase_ids, role, side="opponent")
        if call_phrase_id is not None:
            for phrase_id in choices:
                match = self._schedule_match(game, call_phrase_id, phrase_id)
                if match is not None and match.matched:
                    return phrase_id
        return choices[0]

    @staticmethod
    def _schedule_match(
        game: CallResponseGame,
        call_phrase_id: str,
        response_phrase_id: str,
    ) -> DominanceMatch | None:
        return next(
            (
                match
                for match in game.schedule
                if match.call_phrase_id == call_phrase_id
                and match.response_phrase_id == response_phrase_id
            ),
            None,
        )

    @staticmethod
    def _phrases_for_role(
        game: CallResponseGame,
        phrase_ids: list[str],
        role: PhraseRole,
        *,
        side: str,
    ) -> list[str]:
        choices = [phrase_id for phrase_id in phrase_ids if role in game.phrases[phrase_id].roles]
        if not choices:
            raise ValueError(f"No {role}-capable phrases configured for {side}")
        return choices

    @staticmethod
    def _validate_configuration(game: CallResponseGame) -> None:
        phrase_ids = [*game.player_phrase_ids, *game.opponent_phrase_ids]
        for phrase_id in phrase_ids:
            if phrase_id not in game.phrases:
                raise ValueError(f"Unknown configured phrase id: {phrase_id}")

        pairs: set[tuple[str, str]] = set()
        for match in game.schedule:
            if match.call_phrase_id not in game.phrases:
                raise ValueError(f"Unknown schedule call phrase: {match.call_phrase_id}")
            if match.response_phrase_id not in game.phrases:
                raise ValueError(f"Unknown schedule response phrase: {match.response_phrase_id}")
            if "call" not in game.phrases[match.call_phrase_id].roles:
                raise ValueError(f"Schedule call phrase lacks call role: {match.call_phrase_id}")
            if "response" not in game.phrases[match.response_phrase_id].roles:
                raise ValueError(
                    f"Schedule response phrase lacks response role: {match.response_phrase_id}"
                )
            pair = (match.call_phrase_id, match.response_phrase_id)
            if pair in pairs:
                raise ValueError(f"Duplicate schedule pair: {pair}")
            pairs.add(pair)
