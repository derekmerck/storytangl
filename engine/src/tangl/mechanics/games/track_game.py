"""
Cyclic-track race kernel.

This is the position rung of the game ladder: advantage is carried by *where*
tokens sit rather than how many you hold or which ones they are.

The interesting form is not a forced single-track race. It keeps a cyclic
index but gives each side several tokens in play and lets the player assign a
known roll to any one of their own tokens. Two rules supply the tension:

- a token finishes only by landing **exactly** on the finish distance, so
  overshooting wastes the move
- a token arriving on an occupied board index **evicts** the earlier occupant
  back to the pile

A no-choice race such as chutes and ladders is the degenerate configuration of
the same track: one token per side and no assignment decision, at which point
the outcome is fully determined by the roll sequence. Its characteristic
mechanic is not the lack of choice but the **redirection squares** — landing on
one moves the token somewhere else on the board, forward up a ladder or back
down a chute. That is the ``redirects`` map, and it applies to contested races
too: a square that flings you backward is far more interesting when a rival is
waiting to take your place.

No canonical redirect layout is baked in. Historical boards disagree, the
familiar commercial arrangement is one publisher's choice rather than a
standard, and the moral-instruction ancestors of the game used their own. The
layout is authored world data, not engine truth.

Opponent behavior is plugged in through the ordinary two-phase seam. The
pre-selected move is available before the player commits, so a world can
telegraph intent ("they will jump you if they can"), and a revision strategy
may overwrite that choice afterward to force a narrated outcome.

That second phase is not a cheat hatch bolted onto an honest simulation.
Fairness here is a *side effect* of applying a default ruleset consistently,
not the purpose of having rules. The ruleset exists to launder tension, failure,
and reward through mechanics the player finds plausible — the goal is
verisimilitude, not veracity. A game with no narrative pressure on it happens to
play fair; that is incidental. Revision strategies are therefore ordinary
storytelling instruments, and they are named and registered rather than hidden
so a world's authored bias stays legible to its author.
"""
from __future__ import annotations

from dataclasses import dataclass
import random
from typing import ClassVar

from pydantic import Field

from tangl.journal.fragments import ContentFragment
from tangl.vm.ctx import VmPhaseCtx

from .enums import RoundResult
from .game import Game
from .game_token import GameTokenType, discrete_token_class
from .handler import GameHandler
from .strategies import opponent_strategies

#: Sentinel token id meaning "no legal assignment; forfeit the roll".
FORFEIT_TOKEN = -1


@dataclass(frozen=True)
class TrackMove:
    """Assignment of this round's roll to one of the mover's own tokens."""

    token_id: int

    @property
    def is_forfeit(self) -> bool:
        """True when the roll cannot be legally assigned to any token."""

        return self.token_id == FORFEIT_TOKEN


class RacingPieceType(GameTokenType):
    """Frozen definition of a racing piece, plus its mutable per-piece state.

    Fields marked ``instance_var`` are materialized as writable fields on the
    token wrapper, so the definition stays shared and immutable while each
    piece carries its own seat, position, and status.

    ``position`` counts steps advanced from the start, so the board index is
    ``position % track_length`` and the exact-landing rule is a comparison
    against ``finish_distance``. ``None`` means the piece sits in the pile.
    """

    owner: str = Field("player", json_schema_extra={"instance_var": True})
    token_id: int = Field(0, json_schema_extra={"instance_var": True})
    position: int | None = Field(None, json_schema_extra={"instance_var": True})
    finished: bool = Field(False, json_schema_extra={"instance_var": True})


#: Default piece definition. Worlds may register their own — a lacquered
#: marble, a carved horse — and point ``TrackGame.piece_type`` at it.
DEFAULT_PIECE_LABEL = "racing_piece"


class TrackToken(discrete_token_class(RacingPieceType, "TrackToken")):
    """One racing piece: a graph-capable token over a shared definition."""

    @property
    def in_pile(self) -> bool:
        """True when this piece is waiting in the pile."""

        return self.position is None and not self.finished

    def board_index(self, track_length: int) -> int | None:
        """Return the cyclic board index, or None when off the track."""

        if self.position is None or self.finished:
            return None
        return self.position % track_length


def _ensure_default_piece_type() -> None:
    """Register the stock piece definition if a world has not supplied one."""

    if RacingPieceType.get_instance(DEFAULT_PIECE_LABEL) is None:
        RacingPieceType(label=DEFAULT_PIECE_LABEL, description="a racing piece")


class TrackGame(Game[TrackMove]):
    """State for a cyclic-track race with assignable rolls and eviction."""

    scoring_strategy: str = "single_round"
    opponent_strategy: str | None = "track_random"

    track_length: int = 12
    finish_distance: int = 24
    tokens_per_side: int = 3
    tokens_to_finish: int = 1

    #: Piece definition label. Worlds may register their own ``RacingPieceType``
    #: and name it here to give a table its own marbles.
    piece_type: str = DEFAULT_PIECE_LABEL

    #: Board-index redirections: landing on a key square moves the token to the
    #: value square. Ladders point forward, chutes point back. Applied once, so
    #: a redirect landing on another redirect does not chain.
    redirects: dict[int, int] = Field(default_factory=dict)

    min_roll: int = 1
    max_roll: int = 6
    #: Authored roll sequence, consumed in order. Falls back to seeded rolls.
    roll_sequence: list[int] = Field(default_factory=list)
    shuffle_seed: int | None = None

    tokens: list[TrackToken] = Field(
        default_factory=list,
        json_schema_extra={"reset_field": True},
    )
    roll_index: int = Field(
        default=0,
        json_schema_extra={"reset_field": True},
    )
    player_roll: int = Field(
        default=0,
        json_schema_extra={"reset_field": True},
    )
    opponent_roll: int = Field(
        default=0,
        json_schema_extra={"reset_field": True},
    )
    round_detail: dict[str, object] | None = Field(
        default=None,
        json_schema_extra={"reset_field": True},
    )

    # ─────────────────────────────────────────────────────────────────
    # Track queries
    # ─────────────────────────────────────────────────────────────────

    def owned_tokens(self, owner: str) -> list[TrackToken]:
        """Return one side's tokens in stable id order."""

        return [token for token in self.tokens if token.owner == owner]

    def get_token(self, owner: str, token_id: int) -> TrackToken | None:
        """Return one owned token by id."""

        for token in self.tokens:
            if token.owner == owner and token.token_id == token_id:
                return token
        return None

    def occupant_at(self, index: int) -> TrackToken | None:
        """Return the token currently resting on a board index, if any."""

        for token in self.tokens:
            if token.board_index(self.track_length) == index:
                return token
        return None

    def finished_count(self, owner: str) -> int:
        """Return how many of a side's tokens have finished the race."""

        return sum(1 for token in self.owned_tokens(owner) if token.finished)

    def target_position(self, token: TrackToken, roll: int) -> int:
        """Return the position this token would reach with the given roll."""

        return roll if token.position is None else token.position + roll

    def redirect_for(self, index: int) -> int | None:
        """Return the destination index for a redirect square, if it is one."""

        destination = self.redirects.get(index)
        if destination is None or destination == index:
            return None
        return destination

    def landing_from(self, position: int | None, roll: int) -> int:
        """Return the resting position reached from a raw position by a roll.

        This is the single implementation of the redirect rule, shared by move
        resolution and by board analysis. One redirect is applied if the arrival
        square carries one, as a same-lap displacement — so a chute on a later
        lap moves the token back by the same distance it would on the first —
        and a redirect never chains into a second one.

        A well-formed layout cannot produce a negative position; the clamp only
        guards authored destinations outside ``0..track_length - 1``.
        """

        target = roll if position is None else position + roll
        if target == self.finish_distance:
            return target
        index = target % self.track_length
        destination = self.redirect_for(index)
        if destination is None:
            return target
        landing = max(0, target + (destination - index))
        if landing > self.finish_distance:
            # A ladder may not overshoot the finish any more than a roll may.
            # Without this the token would be stranded past an unreachable
            # exact-landing square forever.
            return target
        return landing

    def resolve_landing(self, token: TrackToken, roll: int) -> int:
        """Return the position this token actually comes to rest on."""

        return self.landing_from(token.position, roll)

    def is_legal(self, token: TrackToken, roll: int) -> bool:
        """True when a roll may be assigned to this token without overshooting."""

        if token.finished:
            return False
        return self.target_position(token, roll) <= self.finish_distance

    def legal_token_ids(self, owner: str, roll: int) -> list[int]:
        """Return the ids of a side's tokens that may take this roll."""

        return [
            token.token_id
            for token in self.owned_tokens(owner)
            if self.is_legal(token, roll)
        ]

    def roll_for(self, owner: str) -> int:
        """Return the roll currently standing for one side."""

        return self.player_roll if owner == "player" else self.opponent_roll

    def next_roll(self) -> int:
        """Draw the next roll from the authored sequence or the seeded die."""

        if self.roll_sequence:
            value = self.roll_sequence[self.roll_index % len(self.roll_sequence)]
            self.roll_index += 1
            return value
        randomizer = random.Random(
            None if self.shuffle_seed is None else self.shuffle_seed + self.roll_index
        )
        self.roll_index += 1
        return randomizer.randint(self.min_roll, self.max_roll)

    def would_evict(self, owner: str, token_id: int, roll: int) -> TrackToken | None:
        """Return the token that this assignment would evict, if any."""

        token = self.get_token(owner, token_id)
        if token is None or not self.is_legal(token, roll):
            return None
        target = self.resolve_landing(token, roll)
        if target == self.finish_distance:
            return None
        resident = self.occupant_at(target % self.track_length)
        if resident is None or resident is token:
            return None
        return resident

    def to_namespace(self) -> dict[str, object]:
        namespace = super().to_namespace()
        opponent_next = self.opponent_next_move
        threatened = None
        if isinstance(opponent_next, TrackMove) and not opponent_next.is_forfeit:
            victim = self.would_evict("opponent", opponent_next.token_id, self.opponent_roll)
            threatened = None if victim is None else victim.owner
        namespace.update(
            {
                "track_length": self.track_length,
                "track_finish_distance": self.finish_distance,
                "track_redirects": dict(self.redirects),
                "track_player_roll": self.player_roll,
                "track_opponent_roll": self.opponent_roll,
                "track_player_positions": [
                    token.position for token in self.owned_tokens("player")
                ],
                "track_opponent_positions": [
                    token.position for token in self.owned_tokens("opponent")
                ],
                "track_player_finished": self.finished_count("player"),
                "track_opponent_finished": self.finished_count("opponent"),
                "track_opponent_next_token": (
                    opponent_next.token_id if isinstance(opponent_next, TrackMove) else None
                ),
                # Author hook for telegraphing intent before the player commits.
                "track_opponent_threatens": threatened == "player",
            }
        )
        return namespace


class TrackGameHandler(GameHandler[TrackGame]):
    """Handler for the cyclic-track race."""

    game_cls: ClassVar[type[Game]] = TrackGame

    def on_setup(self, game: TrackGame) -> None:
        if game.piece_type == DEFAULT_PIECE_LABEL:
            _ensure_default_piece_type()
        game.tokens = [
            TrackToken(
                token_from=game.piece_type,
                label=f"{owner}-{index}",
                owner=owner,
                token_id=index,
            )
            for owner in ("player", "opponent")
            for index in range(game.tokens_per_side)
        ]
        game.roll_index = 0
        game.player_roll = game.next_roll()
        game.opponent_roll = game.next_roll()
        game.round_detail = {
            "outcome": "opening",
            "player_roll": game.player_roll,
        }

    def get_available_moves(self, game: TrackGame) -> list[TrackMove]:
        legal = game.legal_token_ids("player", game.player_roll)
        if not legal:
            return [TrackMove(token_id=FORFEIT_TOKEN)]
        return [TrackMove(token_id=token_id) for token_id in legal]

    def get_move_label(self, game: TrackGame, move: TrackMove) -> str:
        if move.is_forfeit:
            return f"Forfeit the roll of {game.player_roll}"
        token = game.get_token("player", move.token_id)
        roll = game.player_roll
        if token is None:
            return f"Move token {move.token_id}"
        target = game.target_position(token, roll)
        if target == game.finish_distance:
            return f"Move token {move.token_id} home ({roll})"
        victim = game.would_evict("player", move.token_id, roll)
        where = "out of the pile" if token.in_pile else f"from {token.position}"
        landing = game.resolve_landing(token, roll)
        suffix = ""
        if landing != target:
            suffix = " up a ladder" if landing > target else " down a chute"
            if landing == game.finish_distance:
                return f"Move token {move.token_id} {where} ({roll}) and ride a ladder home"
        if victim is not None:
            return f"Move token {move.token_id} {where} to {landing} ({roll}){suffix}, evicting a rival"
        return f"Move token {move.token_id} {where} to {landing} ({roll}){suffix}"

    def resolve_round(
        self,
        game: TrackGame,
        player_move: TrackMove,
        opponent_move: TrackMove | None,
    ) -> RoundResult:
        detail: dict[str, object] = {
            "player_roll": game.player_roll,
            "opponent_roll": game.opponent_roll,
            "player_token": player_move.token_id,
        }

        self._apply_move(game, "player", player_move, game.player_roll, detail)
        if game.finished_count("player") >= game.tokens_to_finish:
            game.score["player"] = 1
            detail["outcome"] = "win"
            game.round_detail = detail
            return RoundResult.WIN

        if opponent_move is not None:
            detail["opponent_token"] = opponent_move.token_id
            self._apply_move(game, "opponent", opponent_move, game.opponent_roll, detail)
            if game.finished_count("opponent") >= game.tokens_to_finish:
                game.score["opponent"] = 1
                detail["outcome"] = "lose"
                game.round_detail = detail
                return RoundResult.LOSE

        game.player_roll = game.next_roll()
        game.opponent_roll = game.next_roll()
        detail["outcome"] = "continue"
        detail["next_player_roll"] = game.player_roll
        game.round_detail = detail
        return RoundResult.CONTINUE

    def _apply_move(
        self,
        game: TrackGame,
        owner: str,
        move: TrackMove,
        roll: int,
        detail: dict[str, object],
    ) -> None:
        """Advance one token, honoring exact-landing and eviction."""

        if move.is_forfeit:
            detail[f"{owner}_forfeited"] = True
            return

        token = game.get_token(owner, move.token_id)
        if token is None or not game.is_legal(token, roll):
            # An illegal assignment wastes the roll rather than corrupting state.
            detail[f"{owner}_forfeited"] = True
            return

        arrival = game.target_position(token, roll)
        if arrival == game.finish_distance:
            token.position = None
            token.finished = True
            detail[f"{owner}_finished_token"] = move.token_id
            return

        target = game.resolve_landing(token, roll)
        if target != arrival:
            detail[f"{owner}_redirected"] = {
                "from": arrival % game.track_length,
                "to": target % game.track_length,
                "kind": "ladder" if target > arrival else "chute",
            }
            if target == game.finish_distance:
                # A ladder may deliver a token home; the exact-landing rule
                # constrains the roll, not where the board then sends you.
                token.position = None
                token.finished = True
                detail[f"{owner}_finished_token"] = move.token_id
                return

        # Occupancy is judged where the token comes to rest, after any redirect.
        resident = game.occupant_at(target % game.track_length)
        if resident is not None and resident is not token:
            # The earlier occupant is the one sent back to the pile.
            resident.position = None
            detail[f"{owner}_evicted"] = {
                "owner": resident.owner,
                "token_id": resident.token_id,
            }
        token.position = target

    def build_round_notes(
        self,
        game: TrackGame,
        player_move: TrackMove,
        opponent_move: TrackMove | None,
        round_result: RoundResult,
    ) -> dict[str, object] | None:
        detail = dict(game.round_detail or {})
        detail["round_result"] = round_result.value
        detail["player_finished"] = game.finished_count("player")
        detail["opponent_finished"] = game.finished_count("opponent")
        detail["player_positions"] = [t.position for t in game.owned_tokens("player")]
        detail["opponent_positions"] = [t.position for t in game.owned_tokens("opponent")]
        return detail

    def get_journal_fragments(
        self,
        game: TrackGame,
        *,
        ctx: VmPhaseCtx | None = None,
    ) -> list[ContentFragment] | None:
        _ = ctx
        last_round = game.last_round
        if last_round is None:
            return []

        notes = last_round.notes or {}
        fragments: list[ContentFragment] = []

        if notes.get("player_forfeited"):
            fragments.append(
                ContentFragment(
                    content=f"Your roll of {notes.get('player_roll')} fits nowhere and is wasted."
                )
            )
        else:
            fragments.append(
                ContentFragment(
                    content=(
                        f"You move token {notes.get('player_token')} "
                        f"on a roll of {notes.get('player_roll')}."
                    )
                )
            )

        for actor in ("player", "opponent"):
            redirect = notes.get(f"{actor}_redirected")
            if redirect:
                who = "You are" if actor == "player" else "Your opponent is"
                if redirect["kind"] == "ladder":
                    line = f"{who} carried up a ladder from {redirect['from']} to {redirect['to']}."
                else:
                    line = f"{who} sent down a chute from {redirect['from']} to {redirect['to']}."
                fragments.append(ContentFragment(content=line))

            evicted = notes.get(f"{actor}_evicted")
            if not evicted:
                continue
            whose = "your" if evicted["owner"] == "player" else "a rival"
            mover = "You send" if actor == "player" else "Your opponent sends"
            fragments.append(
                ContentFragment(
                    content=f"{mover} {whose} token {evicted['token_id']} back to the pile."
                )
            )

        if notes.get("opponent_token") is not None and not notes.get("opponent_forfeited"):
            fragments.append(
                ContentFragment(
                    content=(
                        f"Your opponent moves token {notes.get('opponent_token')} "
                        f"on a roll of {notes.get('opponent_roll')}."
                    )
                )
            )

        end_line = {
            RoundResult.WIN: "Your token lands home exactly and the race is yours.",
            RoundResult.LOSE: "Their token lands home exactly and the race is lost.",
            RoundResult.DRAW: "The race resolves without a clear victor.",
        }.get(last_round.result)
        if end_line is not None:
            fragments.append(ContentFragment(content=end_line))
        return fragments


# ─────────────────────────────────────────────────────────────────────────────
# Opponent strategies
#
# These are ordinary registry entries: the kernel only asks for a move and does
# not care whether it came from a policy, an author-forced outcome, another
# node's strategy bank, or a second cursor playing the other side.
# ─────────────────────────────────────────────────────────────────────────────


def _threatened_indices(game: TrackGame, threatening_owner: str) -> set[int]:
    """Return board indices the threatening side could reach with its roll."""

    roll = game.roll_for(threatening_owner)
    indices: set[int] = set()
    for token in game.owned_tokens(threatening_owner):
        if not game.is_legal(token, roll):
            continue
        # Danger is where an attacker comes to rest, after any redirect, not
        # where it first arrives.
        target = game.resolve_landing(token, roll)
        if target != game.finish_distance:
            indices.add(target % game.track_length)
    return indices


def _score_candidate(game: TrackGame, owner: str, token_id: int) -> int:
    """Rank one assignment: finish > evict rival > escape danger > advance."""

    token = game.get_token(owner, token_id)
    roll = game.roll_for(owner)
    if token is None or not game.is_legal(token, roll):
        return -10_000

    if game.target_position(token, roll) == game.finish_distance:
        return 10_000

    target = game.resolve_landing(token, roll)
    if target == game.finish_distance:
        return 10_000

    score = target  # baseline: advance the token that is farthest along
    victim = game.would_evict(owner, token_id, roll)
    if victim is not None:
        score += 5_000 if victim.owner != owner else -4_000

    rival = "opponent" if owner == "player" else "player"
    danger = _threatened_indices(game, rival)
    current_index = token.board_index(game.track_length)
    if current_index in danger and (target % game.track_length) not in danger:
        score += 2_500
    return score


def _candidate_moves(game: TrackGame, owner: str) -> list[TrackMove]:
    legal = game.legal_token_ids(owner, game.roll_for(owner))
    if not legal:
        return [TrackMove(token_id=FORFEIT_TOKEN)]
    return [TrackMove(token_id=token_id) for token_id in legal]


@opponent_strategies.register("track_random")
def _track_random(game: TrackGame, **ctx) -> TrackMove:
    """Assign the roll to an arbitrary legal token."""

    randomizer = random.Random(
        None if game.shuffle_seed is None else game.shuffle_seed + game.round
    )
    return randomizer.choice(_candidate_moves(game, "opponent"))


@opponent_strategies.register("track_optimal")
def _track_optimal(game: TrackGame, **ctx) -> TrackMove:
    """Play the best available assignment under the standard priority order."""

    candidates = _candidate_moves(game, "opponent")
    return max(
        candidates,
        key=lambda move: _score_candidate(game, "opponent", move.token_id),
    )


@opponent_strategies.register("track_hapless")
def _track_hapless(game: TrackGame, **ctx) -> TrackMove:
    """Play the worst available assignment — a visibly incompetent rival."""

    candidates = _candidate_moves(game, "opponent")
    return min(
        candidates,
        key=lambda move: _score_candidate(game, "opponent", move.token_id),
    )


def _evicted_by_player(game: TrackGame, player_move: TrackMove | None) -> set[int]:
    """Return board indices the player's committed move will clear."""

    if player_move is None or player_move.is_forfeit:
        return set()
    token = game.get_token("player", player_move.token_id)
    if token is None or not game.is_legal(token, game.player_roll):
        return set()
    landing = game.resolve_landing(token, game.player_roll)
    if landing == game.finish_distance:
        return set()
    return {landing % game.track_length}


def _projected_player_squares(
    game: TrackGame,
    player_move: TrackMove | None,
) -> list[tuple[int, int]]:
    """Return the player's post-move (position, board index) pairs.

    Most advanced first, so a hunter goes after the leader. The token named by
    ``player_move`` is projected to where it will land; the rest stand still.
    """

    moved_id = None
    landing = None
    if player_move is not None and not player_move.is_forfeit:
        token = game.get_token("player", player_move.token_id)
        if token is not None and game.is_legal(token, game.player_roll):
            moved_id = player_move.token_id
            landing = game.resolve_landing(token, game.player_roll)

    squares: list[tuple[int, int]] = []
    for token in game.owned_tokens("player"):
        if token.finished:
            continue
        if token.token_id == moved_id:
            if landing == game.finish_distance:
                continue  # about to leave the board entirely
            position = landing
        elif token.position is None:
            continue
        else:
            position = token.position
        squares.append((position, position % game.track_length))

    squares.sort(key=lambda pair: pair[0], reverse=True)
    return squares


@opponent_strategies.register("track_force_capture")
def _track_force_capture(game: TrackGame, player_move: TrackMove | None = None, **ctx) -> TrackMove:
    """Revise after the player commits so the rival lands a capture if it can.

    This deliberately rewrites ``opponent_roll`` as well as the chosen token:
    it is the narrative ret-con seam, used when a world wants "they rolled
    exactly what they needed" rather than an honest policy. The player still
    experiences a consistent ruleset, which is the whole point — plausibility
    is the product, not fairness. Falls back to the standing pre-selection when
    no capture can be manufactured.
    """

    # Revision runs after the player commits but before the round resolves, so
    # hunt where the player's pieces will *be*, not where they are now.
    projected = _projected_player_squares(game, player_move)

    for _, victim_index in projected:
        for hunter in game.owned_tokens("opponent"):
            if hunter.finished:
                continue
            base = 0 if hunter.position is None else hunter.position
            if hunter.board_index(game.track_length) in _evicted_by_player(game, player_move):
                base = 0  # the player's move sends this hunter back to the pile
            for roll in range(game.min_roll, game.max_roll + 1):
                target = base + roll
                if target >= game.finish_distance:
                    continue
                if game.landing_from(base, roll) % game.track_length != victim_index:
                    continue
                game.opponent_roll = roll
                return TrackMove(token_id=hunter.token_id)

    standing = game.opponent_next_move
    if isinstance(standing, TrackMove):
        return standing
    return _track_optimal(game)
