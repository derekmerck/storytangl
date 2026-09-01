"""World-local composition for the compact repartee reference loop."""

from __future__ import annotations

from typing import ClassVar, Self

from pydantic import Field, model_validator

from tangl.core import (
    DispatchLayer,
    Graph,
    Node,
    Priority,
    Selector,
    Token,
    TokenCatalog,
    contribute_ns,
)
from tangl.mechanics.assembly import ComponentManager, Slot
from tangl.mechanics.games import (
    KNOWN_PHRASES_SLOT,
    CallResponseExchange,
    CallResponseGame,
    CallResponseGameHandler,
    CallResponsePhrase,
    DominanceContribution,
    DominanceMatch,
    GameResult,
    HasGame,
    PhraseBadge,
    PhraseType,
    RepertoireManager,
    compose_dominance_schedule,
)
from tangl.mechanics.transaction import (
    CatalogAssetCommitment,
    ComponentSlotAssetHolder,
    TransactionOffer,
)
from tangl.story import Block
from tangl.story.concepts.asset import AssetType
from tangl.vm import VmPhaseCtx, on_update


KNOWN_PRIZES_SLOT = "known_prizes"


def _relation(
    *,
    call: str,
    response: str,
    source_id: str,
) -> DominanceContribution:
    """Declare one immutable positive catalog relation."""

    return DominanceContribution(
        call_selector=Selector(has_identifier=call),
        response_selector=Selector(has_identifier=response),
        result="match",
        dispatch_layer=DispatchLayer.APPLICATION,
        source_id=source_id,
    )


STARTER_CALL = PhraseType(
    label="repartee_starter_call",
    text="Your argument arrives wearing borrowed boots.",
    roles=("call",),
    base_contributions=(
        _relation(
            call="repartee_starter_call",
            response="repartee_reply",
            source_id="repartee-dockhand-catalog",
        ),
    ),
)
REPLY = PhraseType(
    label="repartee_reply",
    text="Then it has walked farther than yours.",
    roles=("response",),
)
MASTER_CALL = PhraseType(
    label="repartee_master_call",
    text="A clever echo is still only an echo.",
    roles=("call",),
    base_contributions=(
        _relation(
            call="repartee_master_call",
            response="repartee_reply",
            source_id="repartee-master-catalog",
        ),
    ),
)
PHRASE_CATALOG = TokenCatalog(
    PhraseType,
    members=(STARTER_CALL, REPLY, MASTER_CALL),
    label="repartee-loop-phrases",
)


class ReparteePrizeType(AssetType):
    """World-local durable prize definition for the reference finish gate."""


SALON_TOKEN = ReparteePrizeType(
    label="repartee_salon_token",
    description="a brass salon token",
)
PRIZE_CATALOG = TokenCatalog(
    ReparteePrizeType,
    members=(SALON_TOKEN,),
    label="repartee-loop-prizes",
)
ReparteePrizeToken = Token._create_wrapper_cls(ReparteePrizeType, "ReparteePrizeToken")


class ReparteePrizeManager(ComponentManager[ReparteePrizeToken]):
    """World-local persistent possession collection for the one salon token."""

    slots: ClassVar[dict[str, Slot]] = {
        KNOWN_PRIZES_SLOT: Slot.for_type(
            KNOWN_PRIZES_SLOT,
            ReparteePrizeToken,
            max_count=1,
        ),
    }
    granted_prize_ids: set[str] = Field(
        default_factory=set,
        json_schema_extra={"include": True},
    )

    def prize_ids(self) -> list[str]:
        """Return currently held prize definition identifiers."""

        return sorted(token.token_from for token in self.get_slot(KNOWN_PRIZES_SLOT))

    def has_prize(self, prize_id: str) -> bool:
        """Return current possession, not historical award status."""

        return prize_id in self.prize_ids()


class ReparteeParticipant(Node):
    """Graph-owned player or opponent with bounded phrase and prize holdings."""

    repertoire: RepertoireManager = Field(
        default_factory=RepertoireManager,
        json_schema_extra={"include": True, "unstructurable": True},
    )
    prizes: ReparteePrizeManager = Field(
        default_factory=ReparteePrizeManager,
        json_schema_extra={"include": True, "unstructurable": True},
    )

    @model_validator(mode="after")
    def _bind_holdings(self) -> Self:
        self.repertoire.bind_owner(self)
        self.prizes.bind_owner(self)
        return self


class ReparteeSetupBlock(Block):
    """Dedicated UPDATE boundary that seeds the player's initial call badge."""


class ReparteeHubBlock(Block):
    """Stable choice hub that publishes the player's current holdings."""

    @contribute_ns
    def provide_repartee_symbols(self) -> dict[str, RepertoireManager | ReparteePrizeManager]:
        """Expose manager interfaces for authored opportunity predicates."""

        player = _participant(self.graph, "player")
        return {"repertoire": player.repertoire, "prizes": player.prizes}


class DockhandGame(CallResponseGame):
    """One-exchange opening contest where the player calls and loses."""

    scoring_n: int = 1
    initial_player_has_initiative: bool = True
    opponent_label: str = "Dockhand"


class MasterGame(CallResponseGame):
    """One-exchange later contest where the player answers and wins."""

    scoring_n: int = 1
    initial_player_has_initiative: bool = False
    opponent_label: str = "Salon Master"


class DockhandContestBlock(HasGame, Block):
    """Opening contest against the reply-holding dockhand."""

    _game_class = DockhandGame
    _game_handler_class = CallResponseGameHandler

    def prepare_game(self, *, ctx: VmPhaseCtx) -> None:
        """Freeze the current player and dockhand repertoires on accepted entry."""

        _prepare_contest(
            self.game,
            player=_participant(ctx.graph, "player"),
            opponent=_participant(ctx.graph, "dockhand"),
        )


class MasterContestBlock(HasGame, Block):
    """Later contest against the master and its unfamiliar call."""

    _game_class = MasterGame
    _game_handler_class = CallResponseGameHandler

    def prepare_game(self, *, ctx: VmPhaseCtx) -> None:
        """Freeze the current player and master repertoires on accepted entry."""

        _prepare_contest(
            self.game,
            player=_participant(ctx.graph, "player"),
            opponent=_participant(ctx.graph, "master"),
        )


class ReparteeLossAftermathBlock(Block):
    """World-owned UPDATE aftermath awarding the deployed dockhand response."""


class ReparteePrizeAftermathBlock(Block):
    """World-owned UPDATE aftermath awarding the separately typed salon token."""


def _participant(graph: Graph, label: str) -> ReparteeParticipant:
    participant = graph.find_one(Selector(label=label))
    assert isinstance(participant, ReparteeParticipant)
    return participant


def _phrase(phrase_id: str) -> PhraseType:
    """Resolve one phrase through the world-selected catalog."""

    definition = next(PHRASE_CATALOG.find_all(Selector(label=phrase_id)), None)
    if definition is None:
        raise ValueError(f"No repartee phrase definition: {phrase_id}")
    return definition


def _definitions(manager: RepertoireManager) -> list[PhraseType]:
    """Resolve one manager's current badges through the bounded phrase catalog."""

    definitions = {badge.token_from for badge in manager.badges()}
    return [_phrase(phrase_id) for phrase_id in sorted(definitions)]


def _prepare_contest(
    game: CallResponseGame,
    *,
    player: ReparteeParticipant,
    opponent: ReparteeParticipant,
) -> None:
    """Compose both legal initiative orientations into fixed game input."""

    player_definitions = _definitions(player.repertoire)
    opponent_definitions = _definitions(opponent.repertoire)
    forward = compose_dominance_schedule(player_definitions, opponent_definitions)
    reverse = compose_dominance_schedule(opponent_definitions, player_definitions)
    matches = {
        (match.call_phrase_id, match.response_phrase_id): match
        for match in [*forward.schedule, *reverse.schedule]
    }
    definitions = {
        definition.label: definition
        for definition in [*player_definitions, *opponent_definitions]
    }
    game.phrases = {
        phrase_id: CallResponsePhrase(text=definition.text, roles=list(definition.roles))
        for phrase_id, definition in sorted(definitions.items())
    }
    game.player_phrase_ids = [definition.label for definition in player_definitions]
    game.opponent_phrase_ids = [definition.label for definition in opponent_definitions]
    game.schedule = [matches[pair] for pair in sorted(matches)]


def _prize(prize_id: str) -> ReparteePrizeType:
    """Resolve one authored prize through the bounded world catalog."""

    definition = next(PRIZE_CATALOG.find_all(Selector(label=prize_id)), None)
    if definition is None:
        raise ValueError(f"No repartee prize definition: {prize_id}")
    return definition


@on_update(
    wants_caller_kind=ReparteeSetupBlock,
    wants_exact_kind=False,
    priority=Priority.NORMAL,
)
def seed_repartee_player(*, caller: ReparteeSetupBlock, ctx: VmPhaseCtx, **_kw: object) -> None:
    """Provision the three authored starting badges through catalog commitments."""

    if caller.locals.get("setup_applied"):
        return
    commitments: list[CatalogAssetCommitment] = []
    for participant_label, definition in (
        ("player", STARTER_CALL),
        ("dockhand", REPLY),
        ("master", MASTER_CALL),
    ):
        participant = _participant(ctx.graph, participant_label)
        if participant.repertoire.has_phrase(definition.label):
            continue
        commitments.append(
            CatalogAssetCommitment(
                ComponentSlotAssetHolder(participant.repertoire, KNOWN_PHRASES_SLOT),
                supplier=(
                    lambda definition=definition, participant_label=participant_label: PhraseBadge(
                        label=f"{participant_label}-{definition.label}",
                        token_from=definition.label,
                    )
                ),
                registry=ctx.graph,
            )
        )
    if commitments:
        TransactionOffer(
            label="seed repartee phrases",
            commitments=commitments,
        ).accept()
    caller.locals["setup_applied"] = True
    ctx.invalidate_namespaces()


@on_update(
    wants_caller_kind=ReparteeLossAftermathBlock,
    wants_exact_kind=False,
    priority=Priority.NORMAL,
)
def award_dockhand_reply(
    *,
    caller: ReparteeLossAftermathBlock,
    ctx: VmPhaseCtx,
    **_kw: object,
) -> None:
    """Award the actual opponent-deployed phrase after the opening loss."""

    if caller.locals.get("aftermath_applied"):
        return
    player = _participant(ctx.graph, "player")
    contest = ctx.graph.find_one(Selector(has_kind=DockhandContestBlock))
    assert isinstance(contest, DockhandContestBlock)
    round_record = contest.game.last_round
    if round_record is None:
        raise ValueError("Dockhand aftermath requires one completed exchange")
    exchange = CallResponseExchange.model_validate(round_record.notes)
    phrase_id = (
        exchange.response_phrase_id
        if exchange.initiative_before
        else exchange.call_phrase_id
    )
    caller.locals["awarded_phrase_ids"] = []
    if contest.game.result is GameResult.LOSE and not player.repertoire.has_phrase(phrase_id):
        definition = _phrase(phrase_id)
        TransactionOffer(
            label=f"learn phrase: {phrase_id}",
            commitments=[
                CatalogAssetCommitment(
                    ComponentSlotAssetHolder(player.repertoire, KNOWN_PHRASES_SLOT),
                    supplier=lambda: PhraseBadge(
                        label=f"player-{phrase_id}",
                        token_from=definition.label,
                    ),
                    registry=ctx.graph,
                ),
            ],
        ).accept()
        caller.locals["awarded_phrase_ids"] = [phrase_id]
    caller.locals["aftermath_applied"] = True
    ctx.invalidate_namespaces()


@on_update(
    wants_caller_kind=ReparteePrizeAftermathBlock,
    wants_exact_kind=False,
    priority=Priority.NORMAL,
)
def award_salon_token(
    *,
    caller: ReparteePrizeAftermathBlock,
    ctx: VmPhaseCtx,
    **_kw: object,
) -> None:
    """Award the one catalog-bound prize after the master contest victory."""

    if caller.locals.get("aftermath_applied"):
        return
    player = _participant(ctx.graph, "player")
    contest = ctx.graph.find_one(Selector(has_kind=MasterContestBlock))
    assert isinstance(contest, MasterContestBlock)
    caller.locals["awarded_prize_ids"] = []
    if (
        contest.game.result is GameResult.WIN
        and SALON_TOKEN.label not in player.prizes.granted_prize_ids
    ):
        definition = _prize(SALON_TOKEN.label)
        TransactionOffer(
            label="award salon token",
            commitments=[
                CatalogAssetCommitment(
                    ComponentSlotAssetHolder(player.prizes, KNOWN_PRIZES_SLOT),
                    supplier=lambda: ReparteePrizeToken(
                        label=f"player-{definition.label}",
                        token_from=definition.label,
                    ),
                    registry=ctx.graph,
                ),
            ],
        ).accept()
        player.prizes.granted_prize_ids.add(definition.label)
        caller.locals["awarded_prize_ids"] = [definition.label]
    caller.locals["aftermath_applied"] = True
    ctx.invalidate_namespaces()
