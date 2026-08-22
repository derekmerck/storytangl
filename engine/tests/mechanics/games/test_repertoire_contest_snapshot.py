"""Accepted-entry repertoire snapshots for a world-owned call-response contest."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import ClassVar, Self
from uuid import UUID

import pytest
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
from tangl.core.runtime_op import Predicate
from tangl.journal.fragments import ChoiceFragment, ContentFragment
from tangl.mechanics.assembly import ComponentManager, Slot
from tangl.mechanics.games import (
    KNOWN_PHRASES_SLOT,
    CallResponseGame,
    CallResponseExchange,
    CallResponseGameHandler,
    CallResponsePhrase,
    DominanceComposition,
    DominanceContribution,
    DominanceContradiction,
    DominanceMatch,
    GamePhase,
    GameResult,
    HasGame,
    PhraseBadge,
    PhraseType,
    RepertoireManager,
    compose_dominance_schedule,
)
from tangl.mechanics.transaction import (
    AssetMoveCommitment,
    CatalogAssetCommitment,
    ComponentSlotAssetHolder,
    TransactionOffer,
)
from tangl.story import Action, Block, StoryGraph
from tangl.story.concepts.asset import AssetType
from tangl.vm import Ledger, ResolutionPhase as P, TraversableEdge, VmPhaseCtx, on_update


KNOWN_PRIZES_SLOT = "known_prizes"


class PrizeType(AssetType):
    """Test-world catalog definition for a win reward distinct from phrases."""


PrizeToken = Token._create_wrapper_cls(PrizeType, "RepertoirePrizeToken")


class PrizeManager(ComponentManager[PrizeToken]):
    """Test-world persistent collection for independently typed prize tokens."""

    slots: ClassVar[dict[str, Slot]] = {
        KNOWN_PRIZES_SLOT: Slot.for_type(
            KNOWN_PRIZES_SLOT,
            PrizeToken,
            max_count=1000,
        ),
    }
    granted_prize_ids: set[str] = Field(
        default_factory=set,
        json_schema_extra={"include": True},
    )

    def prizes(self) -> list[PrizeToken]:
        """Return awarded prizes in stable definition/id order."""

        return sorted(
            self.get_slot(KNOWN_PRIZES_SLOT),
            key=lambda prize: (prize.token_from, str(prize.uid)),
        )

    def prize_ids(self) -> list[str]:
        """Return granted prize-definition identifiers."""

        return [prize.token_from for prize in self.prizes()]

    def has_prize(self, prize_id: str) -> bool:
        """Return whether this owner currently holds a prize definition."""

        return prize_id in self.prize_ids()

    def has_received_prize(self, prize_id: str) -> bool:
        """Return whether this world has granted the definition to this owner."""

        return prize_id in self.granted_prize_ids


@pytest.fixture(autouse=True)
def reset_phrase_types() -> Iterator[None]:
    """Keep the test-world catalog available for graph restoration only."""

    PhraseType.clear_instances()
    PrizeType.clear_instances()
    yield
    PhraseType.clear_instances()
    PrizeType.clear_instances()


class RepertoireParticipant(Node):
    """Test-world graph owner with one ordinary phrase repertoire."""

    repertoire: RepertoireManager = Field(
        default_factory=RepertoireManager,
        json_schema_extra={"include": True, "unstructurable": True},
    )
    prizes: PrizeManager = Field(
        default_factory=PrizeManager,
        json_schema_extra={"include": True, "unstructurable": True},
    )

    @model_validator(mode="after")
    def _bind_repertoire_owner(self) -> Self:
        self.repertoire.bind_owner(self)
        self.prizes.bind_owner(self)
        return self


class OpportunityHubBlock(Block):
    """Test-world stable-choice hub exposing one participant's live holdings."""

    player_id: UUID

    @contribute_ns
    def provide_opportunity_symbols(
        self,
    ) -> dict[str, RepertoireManager | PrizeManager]:
        """Publish the participant's current ownership managers for predicates."""

        player = self.graph.get(self.player_id)
        assert isinstance(player, RepertoireParticipant)
        return {
            "repertoire": player.repertoire,
            "prizes": player.prizes,
        }


class SnapshotContestBlock(HasGame, Block):
    """Test-world contest that snapshots participant repertoires on entry."""

    _game_class = CallResponseGame
    _game_handler_class = CallResponseGameHandler

    player_id: UUID
    opponent_id: UUID
    scenario_contributions: tuple[DominanceContribution, ...] = Field(
        default_factory=tuple,
    )
    composition_diagnostics: list[DominanceContradiction] = Field(
        default_factory=list,
        json_schema_extra={"include": True},
    )

    def prepare_game(self, *, ctx: VmPhaseCtx) -> None:
        """Freeze live repertoire definitions immediately before game setup."""

        player = ctx.graph.get(self.player_id)
        opponent = ctx.graph.get(self.opponent_id)
        assert isinstance(player, RepertoireParticipant)
        assert isinstance(opponent, RepertoireParticipant)

        player_phrases = _definitions_from_repertoire(player.repertoire)
        opponent_phrases = _definitions_from_repertoire(opponent.repertoire)
        forward = compose_dominance_schedule(
            player_phrases,
            opponent_phrases,
            contributions=self.scenario_contributions,
        )
        reverse = compose_dominance_schedule(
            opponent_phrases,
            player_phrases,
            contributions=self.scenario_contributions,
        )
        composition = _combine_compositions(forward, reverse)

        definitions = {phrase.label: phrase for phrase in [*player_phrases, *opponent_phrases]}
        self.game.phrases = {
            phrase_id: CallResponsePhrase(
                text=definition.text,
                roles=list(definition.roles),
            )
            for phrase_id, definition in sorted(definitions.items())
        }
        self.game.player_phrase_ids = [phrase.label for phrase in player_phrases]
        self.game.opponent_phrase_ids = [phrase.label for phrase in opponent_phrases]
        self.game.schedule = composition.schedule
        self.composition_diagnostics = composition.diagnostics


class RepertoireAftermathBlock(Block):
    """Test-world outcome block that awards one phrase after a player loss."""

    player_id: UUID
    contest_id: UUID


class PrizeAftermathBlock(Block):
    """Test-world outcome block that awards one authored prize after a win."""

    player_id: UUID
    contest_id: UUID
    prize_definition_id: str


@on_update(
    wants_caller_kind=RepertoireAftermathBlock,
    wants_exact_kind=False,
    priority=Priority.NORMAL,
)
def apply_repertoire_loss_aftermath(
    *,
    caller: RepertoireAftermathBlock,
    ctx: VmPhaseCtx,
    **_kw: object,
) -> None:
    """Mint the opponent's deployed phrase through the ordinary transaction path."""

    if caller.locals.get("aftermath_applied"):
        return

    player = ctx.graph.get(caller.player_id)
    contest = ctx.graph.get(caller.contest_id)
    assert isinstance(player, RepertoireParticipant)
    assert isinstance(contest, SnapshotContestBlock)
    last_round = contest.game.last_round
    if last_round is None:
        raise ValueError("Repertoire aftermath requires one resolved exchange")

    exchange = CallResponseExchange.model_validate(last_round.notes)
    caller.locals["awarded_phrase_ids"] = []
    if contest.game.result is GameResult.LOSE:
        phrase_id = (
            exchange.response_phrase_id
            if exchange.initiative_before
            else exchange.call_phrase_id
        )
        definition = PhraseType.get_instance(phrase_id)
        if definition is None:
            raise ValueError(f"No live phrase definition for award: {phrase_id}")
        if not player.repertoire.has_phrase(phrase_id):
            offer = TransactionOffer(
                label=f"learn phrase: {phrase_id}",
                commitments=[
                    CatalogAssetCommitment(
                        ComponentSlotAssetHolder(
                            player.repertoire,
                            KNOWN_PHRASES_SLOT,
                        ),
                        supplier=lambda: PhraseBadge(
                            label=f"{caller.label}-{phrase_id}",
                            token_from=definition.label,
                        ),
                        registry=ctx.graph,
                    ),
                ],
            )
            offer.accept()
            caller.locals["awarded_phrase_ids"] = [phrase_id]
    caller.locals["aftermath_applied"] = True
    ctx.invalidate_namespaces()


@on_update(
    wants_caller_kind=PrizeAftermathBlock,
    wants_exact_kind=False,
    priority=Priority.NORMAL,
)
def apply_prize_win_aftermath(
    *,
    caller: PrizeAftermathBlock,
    ctx: VmPhaseCtx,
    **_kw: object,
) -> None:
    """Mint one catalog-bound prize through the ordinary transaction path."""

    if caller.locals.get("aftermath_applied"):
        return

    player = ctx.graph.get(caller.player_id)
    contest = ctx.graph.get(caller.contest_id)
    assert isinstance(player, RepertoireParticipant)
    assert isinstance(contest, SnapshotContestBlock)
    caller.locals["awarded_prize_ids"] = []
    if contest.game.result is GameResult.WIN:
        definition = next(
            _prize_catalog().find_all(Selector(label=caller.prize_definition_id)),
            None,
        )
        if definition is None:
            raise ValueError(f"No catalog prize definition: {caller.prize_definition_id}")
        if not player.prizes.has_received_prize(definition.label):
            offer = TransactionOffer(
                label=f"award prize: {definition.label}",
                commitments=[
                    CatalogAssetCommitment(
                        ComponentSlotAssetHolder(player.prizes, KNOWN_PRIZES_SLOT),
                        supplier=lambda: PrizeToken(
                            label=f"{caller.label}-{definition.label}",
                            token_from=definition.label,
                        ),
                        registry=ctx.graph,
                    ),
                ],
            )
            offer.accept()
            player.prizes.granted_prize_ids.add(definition.label)
            caller.locals["awarded_prize_ids"] = [definition.label]
    caller.locals["aftermath_applied"] = True
    ctx.invalidate_namespaces()


def _definitions_from_repertoire(repertoire: RepertoireManager) -> list[PhraseType]:
    """Project one owner's live badge definitions into a stable contest input."""

    definitions = {
        badge.token_from: badge.reference_singleton
        for badge in repertoire.badges()
    }
    return [definitions[phrase_id] for phrase_id in sorted(definitions)]


def _combine_compositions(*compositions: DominanceComposition) -> DominanceComposition:
    """Merge orientation schedules, rejecting non-identical duplicate pairs."""

    matches: dict[tuple[str, str], DominanceMatch] = {}
    diagnostics: list[DominanceContradiction] = []
    for composition in compositions:
        diagnostics.extend(composition.diagnostics)
        for match in composition.schedule:
            pair = (match.call_phrase_id, match.response_phrase_id)
            existing = matches.get(pair)
            if existing is not None and existing != match:
                raise ValueError(f"Conflicting composed dominance match for {pair}")
            matches[pair] = match
    return DominanceComposition(
        schedule=[matches[pair] for pair in sorted(matches)],
        diagnostics=diagnostics,
    )


def _contribution(
    *,
    call: str,
    response: str,
    result: str,
    layer: DispatchLayer,
    source_id: str,
) -> DominanceContribution:
    """Build one exact-id contribution for the test-world contest."""

    return DominanceContribution(
        call_selector=Selector(has_identifier=call),
        response_selector=Selector(has_identifier=response),
        result=result,
        dispatch_layer=layer,
        priority=Priority.NORMAL,
        source_id=source_id,
    )


def _add_badge(
    graph: Graph,
    owner: RepertoireParticipant,
    definition: PhraseType,
) -> PhraseBadge:
    """Add one graph-owned badge to an owner's ordinary repertoire slot."""

    badge = graph.add_node(
        kind=PhraseBadge,
        label=f"{owner.label}-{definition.label}",
        token_from=definition.label,
    )
    owner.repertoire.assign(KNOWN_PHRASES_SLOT, badge)
    return badge


def _snapshot_graph(
    *,
    initial_player_has_initiative: bool = True,
    graph_class: type[Graph] = Graph,
    configure_current_frontier: Callable[
        [Graph, RepertoireParticipant, Block],
        None,
    ]
    | None = None,
) -> tuple[
    Graph,
    Ledger,
    RepertoireParticipant,
    RepertoireParticipant,
    SnapshotContestBlock,
    PhraseBadge,
    TraversableEdge,
]:
    """Build foyer/current/contest topology with one badge moved before entry."""

    definitions = _install_phrase_types()
    taunt = definitions["taunt"]
    reply = definitions["reply"]
    late_reply = definitions["late_reply"]

    graph = graph_class(label="repertoire-snapshot")
    foyer = graph.add_node(kind=Block, label="foyer")
    current = graph.add_node(kind=Block, label="current")
    player = graph.add_node(kind=RepertoireParticipant, label="player")
    opponent = graph.add_node(kind=RepertoireParticipant, label="opponent")
    contest = graph.add_node(
        kind=SnapshotContestBlock,
        label="contest",
        player_id=player.uid,
        opponent_id=opponent.uid,
        game_state=CallResponseGame(
            scoring_n=1,
            initial_player_has_initiative=initial_player_has_initiative,
        ),
        scenario_contributions=(
            _contribution(
                call="taunt",
                response="reply",
                result="match",
                layer=DispatchLayer.LOCAL,
                source_id="scenario-override",
            ),
        ),
    )
    _add_badge(graph, player, taunt)
    _add_badge(graph, opponent, reply)
    late_badge = _add_badge(graph, opponent, late_reply)
    foyer_current = TraversableEdge(
        graph=graph,
        predecessor_id=foyer.uid,
        successor_id=current.uid,
        label="Approach the contest",
    )
    current_contest = TraversableEdge(
        graph=graph,
        predecessor_id=current.uid,
        successor_id=contest.uid,
        label="Begin the contest",
    )
    if configure_current_frontier is not None:
        configure_current_frontier(graph, player, current)
    ledger = Ledger.from_graph(graph=graph, entry_id=foyer.uid)

    ledger.resolve_choice(foyer_current.uid)

    assert contest.game.phase is GamePhase.PENDING
    assert contest.game.phrases == {}
    assert late_badge in opponent.repertoire.badges()
    return graph, ledger, player, opponent, contest, late_badge, current_contest


def _add_opportunity_hub(
    graph: Graph,
    *,
    player: RepertoireParticipant,
    current: Block,
) -> tuple[OpportunityHubBlock, TraversableEdge, Action, Action]:
    """Add stable phrase- and prize-gated choices to the current frontier."""

    hub = graph.add_node(
        kind=OpportunityHubBlock,
        label="opportunity hub",
        player_id=player.uid,
    )
    challenge = graph.add_node(kind=Block, label="learned phrase challenge")
    prize_location = graph.add_node(kind=Block, label="trophy location")
    enter_hub = TraversableEdge(
        graph=graph,
        predecessor_id=current.uid,
        successor_id=hub.uid,
        label="Return to the hub",
    )
    phrase_action = Action(
        predecessor_id=hub.uid,
        successor_id=challenge.uid,
        text="Challenge the stronger opponent",
        availability=[Predicate(expr="repertoire.has_phrase('reply')")],
    )
    prize_action = Action(
        predecessor_id=hub.uid,
        successor_id=prize_location.uid,
        text="Enter the trophy chamber",
        availability=[Predicate(expr="prizes.has_prize('golden_trophy')")],
    )
    graph.add(phrase_action)
    graph.add(prize_action)
    return hub, enter_hub, phrase_action, prize_action


def _latest_choice(ledger: Ledger, edge: Action) -> ChoiceFragment:
    """Return the newest journaled availability projection for one stable action."""

    return next(
        fragment
        for fragment in reversed(ledger.get_journal())
        if isinstance(fragment, ChoiceFragment) and fragment.edge_id == edge.uid
    )


def _add_loss_aftermath(
    graph: Graph,
    *,
    player: RepertoireParticipant,
    contest: SnapshotContestBlock,
) -> RepertoireAftermathBlock:
    """Wire one stable terminal-loss continuation to a world-owned aftermath."""

    aftermath = graph.add_node(
        kind=RepertoireAftermathBlock,
        label="learn from defeat",
        player_id=player.uid,
        contest_id=contest.uid,
    )
    TraversableEdge(
        graph=graph,
        predecessor_id=contest.uid,
        successor_id=aftermath.uid,
        label="Learn from the exchange",
        trigger_phase=P.POSTREQS,
        predicate="game_lost",
    )
    return aftermath


def _play_terminal_loss(
    *,
    initial_player_has_initiative: bool,
) -> tuple[
    Graph,
    Ledger,
    RepertoireParticipant,
    RepertoireParticipant,
    SnapshotContestBlock,
    RepertoireAftermathBlock,
]:
    """Run one loss through contest UPDATE, POSTREQS, and aftermath UPDATE."""

    graph, ledger, player, opponent, contest, _late_badge, current_contest = _snapshot_graph(
        initial_player_has_initiative=initial_player_has_initiative,
    )
    aftermath = _add_loss_aftermath(graph, player=player, contest=contest)
    ledger.resolve_choice(current_contest.uid)
    action = next(
        edge
        for edge in contest.edges_out(Selector(has_kind=Action))
        if edge.payload == {"move": "taunt"}
    )

    ledger.resolve_choice(action.uid, choice_payload=action.payload)

    assert contest.game.phase is GamePhase.TERMINAL
    assert contest.game.result is GameResult.LOSE
    assert ledger.cursor_id == aftermath.uid
    return graph, ledger, player, opponent, contest, aftermath


def _install_phrase_types() -> dict[str, PhraseType]:
    """Install the deterministic test-world catalog needed for restoration."""

    taunt = PhraseType(
        label="taunt",
        text="You fight like a dairy farmer.",
        roles=("call", "response"),
        base_contributions=(
            _contribution(
                call="taunt",
                response="reply",
                result="miss",
                layer=DispatchLayer.APPLICATION,
                source_id="catalog-miss",
            ),
        ),
    )
    reply = PhraseType(
        label="reply",
        text="How appropriate. You fight like a cow.",
        roles=("call", "response"),
        base_contributions=(
            _contribution(
                call="reply",
                response="late_reply",
                result="match",
                layer=DispatchLayer.AUTHOR,
                source_id="reply-base",
            ),
        ),
    )
    late_reply = PhraseType(
        label="late_reply",
        text="That is the second-best thing about your mother.",
        roles=("call", "response"),
    )
    return {phrase.label: phrase for phrase in (taunt, reply, late_reply)}


def _install_sword_master_phrase_type() -> PhraseType:
    """Install one later call whose immutable relation recognizes ``reply``."""

    return PhraseType(
        label="sword_master_oblique_call",
        text="My name is Guybrush Threepwood. Prepare to die.",
        roles=("call",),
        base_contributions=(
            _contribution(
                call="sword_master_oblique_call",
                response="reply",
                result="match",
                layer=DispatchLayer.APPLICATION,
                source_id="sword-master-catalog",
            ),
        ),
    )


def _build_sword_master_contest(
    graph: Graph,
    *,
    player: RepertoireParticipant,
) -> tuple[Ledger, RepertoireParticipant, SnapshotContestBlock, TraversableEdge]:
    """Build one fresh frontier for an opponent holding only the later call."""

    sword_master_call = _install_sword_master_phrase_type()
    foyer = graph.add_node(kind=Block, label="sword master foyer")
    current = graph.add_node(kind=Block, label="sword master current")
    opponent = graph.add_node(kind=RepertoireParticipant, label="sword master")
    contest = graph.add_node(
        kind=SnapshotContestBlock,
        label="sword master contest",
        player_id=player.uid,
        opponent_id=opponent.uid,
        game_state=CallResponseGame(
            scoring_n=1,
            initial_player_has_initiative=False,
        ),
    )
    _add_badge(graph, opponent, sword_master_call)
    foyer_current = TraversableEdge(
        graph=graph,
        predecessor_id=foyer.uid,
        successor_id=current.uid,
        label="Approach the Sword Master",
    )
    current_contest = TraversableEdge(
        graph=graph,
        predecessor_id=current.uid,
        successor_id=contest.uid,
        label="Answer the Sword Master",
    )
    ledger = Ledger.from_graph(graph=graph, entry_id=foyer.uid)
    ledger.resolve_choice(foyer_current.uid)

    assert contest.game.phase is GamePhase.PENDING
    return ledger, opponent, contest, current_contest


def _install_prize_types() -> dict[str, PrizeType]:
    """Install the bounded test-world prize catalog for awards and restoration."""

    golden_trophy = PrizeType(
        label="golden_trophy",
        description="a golden trophy",
    )
    unoffered_trinket = PrizeType(
        label="unoffered_trinket",
        description="an unoffered trinket",
    )
    return {
        prize.label: prize
        for prize in (golden_trophy, unoffered_trinket)
    }


def _prize_catalog() -> TokenCatalog[PrizeType]:
    """Return the explicit bounded catalog selected by this test world."""

    golden_trophy = PrizeType.get_instance("golden_trophy")
    if golden_trophy is None:
        raise ValueError("Test-world prize catalog is not installed")
    return TokenCatalog(
        PrizeType,
        members=(golden_trophy,),
        label="reference-prizes",
    )


def _add_prize_aftermath(
    graph: Graph,
    *,
    player: RepertoireParticipant,
    contest: SnapshotContestBlock,
    predicate: str,
    label: str = "claim the trophy",
) -> PrizeAftermathBlock:
    """Wire one stable terminal continuation to the prize policy block."""

    aftermath = graph.add_node(
        kind=PrizeAftermathBlock,
        label=label,
        player_id=player.uid,
        contest_id=contest.uid,
        prize_definition_id="golden_trophy",
    )
    TraversableEdge(
        graph=graph,
        predecessor_id=contest.uid,
        successor_id=aftermath.uid,
        label="Resolve the prize",
        trigger_phase=P.POSTREQS,
        predicate=predicate,
    )
    return aftermath


def _play_terminal_win() -> tuple[
    Graph,
    Ledger,
    RepertoireParticipant,
    RepertoireParticipant,
    SnapshotContestBlock,
    PrizeAftermathBlock,
]:
    """Run one win through contest UPDATE, POSTREQS, and prize aftermath UPDATE."""

    _install_prize_types()
    graph, ledger, player, opponent, contest, _late_badge, current_contest = _snapshot_graph()
    contest.scenario_contributions = ()
    aftermath = _add_prize_aftermath(
        graph,
        player=player,
        contest=contest,
        predicate="game_won",
    )
    ledger.resolve_choice(current_contest.uid)
    action = next(
        edge
        for edge in contest.edges_out(Selector(has_kind=Action))
        if edge.payload == {"move": "taunt"}
    )
    ledger.resolve_choice(action.uid, choice_payload=action.payload)

    assert contest.game.phase is GamePhase.TERMINAL
    assert contest.game.result is GameResult.WIN
    assert ledger.cursor_id == aftermath.uid
    return graph, ledger, player, opponent, contest, aftermath


def test_accepted_entry_snapshots_live_repertoires_after_frontier_provisioning() -> None:
    graph, ledger, player, opponent, contest, late_badge, current_contest = _snapshot_graph()

    opponent.repertoire.unassign(KNOWN_PHRASES_SLOT, late_badge)
    player.repertoire.assign(KNOWN_PHRASES_SLOT, late_badge)

    ledger.resolve_choice(current_contest.uid)

    assert contest.game.phase is GamePhase.READY
    assert contest.game.player_phrase_ids == ["late_reply", "taunt"]
    assert contest.game.opponent_phrase_ids == ["reply"]
    assert {
        (match.call_phrase_id, match.response_phrase_id, match.matched, match.source_id)
        for match in contest.game.schedule
    } == {
        ("reply", "late_reply", True, "reply-base"),
        ("taunt", "reply", True, "scenario-override"),
    }
    assert contest.composition_diagnostics == []
    action_moves = {
        edge.payload["move"]
        for edge in contest.edges_out(Selector(has_kind=Action))
        if edge.payload is not None
    }
    assert action_moves == {"late_reply", "taunt"}

    player.repertoire.unassign(KNOWN_PHRASES_SLOT, late_badge)
    opponent.repertoire.assign(KNOWN_PHRASES_SLOT, late_badge)

    assert contest.game.player_phrase_ids == ["late_reply", "taunt"]
    assert contest.game.opponent_phrase_ids == ["reply"]
    assert any(
        match.response_phrase_id == "late_reply"
        for match in contest.game.schedule
    )

    taunt_action = next(
        edge
        for edge in contest.edges_out(Selector(has_kind=Action))
        if edge.payload == {"move": "taunt"}
    )
    ledger.resolve_choice(taunt_action.uid, choice_payload=taunt_action.payload)

    assert contest.game.phase is GamePhase.TERMINAL
    assert contest.game.last_exchange is not None
    assert contest.game.last_exchange.match_source_id == "scenario-override"
    assert graph.get(contest.uid) is contest


def test_prepared_contest_snapshot_survives_graph_roundtrip() -> None:
    _, ledger, player, opponent, contest, late_badge, current_contest = _snapshot_graph()
    opponent.repertoire.unassign(KNOWN_PHRASES_SLOT, late_badge)
    player.repertoire.assign(KNOWN_PHRASES_SLOT, late_badge)
    ledger.resolve_choice(current_contest.uid)

    payload = ledger.graph.unstructure()
    PhraseType.clear_instances()
    definitions = _install_phrase_types()
    restored = Graph.structure(payload)
    restored_contest = restored.get(contest.uid)
    restored_player = restored.get(player.uid)
    restored_opponent = restored.get(opponent.uid)

    assert isinstance(restored_contest, SnapshotContestBlock)
    assert isinstance(restored_player, RepertoireParticipant)
    assert isinstance(restored_opponent, RepertoireParticipant)
    assert restored_contest.game.phase is GamePhase.READY
    assert restored_contest.game.player_phrase_ids == ["late_reply", "taunt"]
    assert restored_contest.game.opponent_phrase_ids == ["reply"]
    assert restored_contest.game.schedule == contest.game.schedule
    assert restored_player.repertoire.owner is restored_player
    assert restored_opponent.repertoire.owner is restored_opponent
    assert restored_player.repertoire.phrase_ids() == ["late_reply", "taunt"]
    assert restored_opponent.repertoire.phrase_ids() == ["reply"]
    restored_badges = [
        *restored_player.repertoire.badges(),
        *restored_opponent.repertoire.badges(),
    ]
    assert {
        badge.reference_singleton.label: badge.reference_singleton
        for badge in restored_badges
    } == definitions


@pytest.mark.parametrize(
    ("initial_player_has_initiative", "awarded_phrase_id"),
    [(True, "reply"), (False, "late_reply")],
)
def test_loss_aftermath_awards_the_opponent_deployed_phrase(
    initial_player_has_initiative: bool,
    awarded_phrase_id: str,
) -> None:
    graph, _ledger, player, opponent, contest, aftermath = _play_terminal_loss(
        initial_player_has_initiative=initial_player_has_initiative,
    )

    exchange = CallResponseExchange.model_validate(contest.game.last_round.notes)
    assert aftermath.locals["awarded_phrase_ids"] == [awarded_phrase_id]
    assert player.repertoire.has_phrase(awarded_phrase_id)
    opponent_badge = next(
        badge
        for badge in opponent.repertoire.badges()
        if badge.token_from == awarded_phrase_id
    )
    learned_badge = next(
        badge
        for badge in player.repertoire.badges()
        if badge.token_from == awarded_phrase_id
    )
    assert learned_badge.uid != opponent_badge.uid
    assert learned_badge.reference_singleton is opponent_badge.reference_singleton
    assert learned_badge.reference_singleton.label == awarded_phrase_id
    assert exchange.initiative_before is initial_player_has_initiative
    assert graph.get(learned_badge.uid) is learned_badge


def test_later_call_definition_answers_an_earned_response_in_a_fresh_contest() -> None:
    """A bounded fresh snapshot composes a later call against an old earned badge."""

    graph, _ledger, player, _opponent, first_contest, first_aftermath = _play_terminal_loss(
        initial_player_has_initiative=True,
    )
    reply = PhraseType.get_instance("reply")
    assert reply is not None
    assert first_contest.game.player_phrase_ids == ["taunt"]
    assert first_aftermath.locals["awarded_phrase_ids"] == ["reply"]
    earned_reply = next(
        badge for badge in player.repertoire.badges() if badge.token_from == "reply"
    )
    first_phrases = dict(first_contest.game.phrases)
    first_schedule = list(first_contest.game.schedule)

    sword_ledger, sword_master, sword_contest, current_contest = _build_sword_master_contest(
        graph,
        player=player,
    )

    assert all(
        contribution.call_selector.has_identifier != "sword_master_oblique_call"
        and contribution.response_selector.has_identifier != "sword_master_oblique_call"
        for contribution in reply.base_contributions
    )
    assert earned_reply in player.repertoire.badges()
    assert player.repertoire.has_phrase("sword_master_oblique_call") is False
    assert sword_master.repertoire.phrase_ids() == ["sword_master_oblique_call"]
    assert sword_contest.game.phase is GamePhase.PENDING

    sword_ledger.resolve_choice(current_contest.uid)

    assert sword_contest.game.phase is GamePhase.READY
    assert sword_contest.game.player_phrase_ids == ["reply", "taunt"]
    assert sword_contest.game.opponent_phrase_ids == ["sword_master_oblique_call"]
    assert sword_contest.scenario_contributions == ()
    assert sword_contest.game.schedule == [
        DominanceMatch(
            call_phrase_id="sword_master_oblique_call",
            response_phrase_id="reply",
            matched=True,
            source_id="sword-master-catalog",
        ),
    ]
    response = next(
        edge
        for edge in sword_contest.edges_out(Selector(has_kind=Action))
        if edge.payload == {"move": "reply"}
    )

    sword_ledger.resolve_choice(response.uid, choice_payload=response.payload)

    exchange = sword_contest.game.last_exchange
    assert exchange is not None
    assert exchange.call_phrase_id == "sword_master_oblique_call"
    assert exchange.response_phrase_id == "reply"
    assert exchange.matched is True
    assert exchange.match_source_id == "sword-master-catalog"
    assert exchange.initiative_before is False
    assert exchange.initiative_after is True
    assert sword_contest.game.result is GameResult.WIN
    assert any(
        isinstance(fragment, ContentFragment)
        and fragment.content == "Call: My name is Guybrush Threepwood. Prepare to die."
        for fragment in sword_ledger.get_journal()
    )
    assert any(
        isinstance(fragment, ContentFragment)
        and fragment.content
        == "Response: How appropriate. You fight like a cow. answers the call."
        for fragment in sword_ledger.get_journal()
    )
    assert first_contest.game.phrases == first_phrases
    assert first_contest.game.schedule == first_schedule
    assert "sword_master_oblique_call" not in first_contest.game.phrases


def test_aftermath_does_not_award_after_a_player_win() -> None:
    graph, ledger, player, _opponent, contest, _late_badge, current_contest = _snapshot_graph()
    contest.scenario_contributions = ()
    aftermath = graph.add_node(
        kind=RepertoireAftermathBlock,
        label="no award after victory",
        player_id=player.uid,
        contest_id=contest.uid,
    )
    TraversableEdge(
        graph=graph,
        predecessor_id=contest.uid,
        successor_id=aftermath.uid,
        label="Leave after victory",
        trigger_phase=P.POSTREQS,
        predicate="game_won",
    )

    ledger.resolve_choice(current_contest.uid)
    action = next(
        edge
        for edge in contest.edges_out(Selector(has_kind=Action))
        if edge.payload == {"move": "taunt"}
    )
    ledger.resolve_choice(action.uid, choice_payload=action.payload)

    assert contest.game.result is GameResult.WIN
    assert ledger.cursor_id == aftermath.uid
    assert aftermath.locals["aftermath_applied"] is True
    assert aftermath.locals["awarded_phrase_ids"] == []
    assert player.repertoire.phrase_ids() == ["taunt"]


def test_loss_aftermath_is_idempotent_and_learned_phrase_reaches_next_contest() -> None:
    graph, ledger, player, _opponent, contest, aftermath = _play_terminal_loss(
        initial_player_has_initiative=True,
    )
    learned_badge = next(
        badge for badge in player.repertoire.badges() if badge.token_from == "reply"
    )
    badge_ids_before = {
        badge.uid
        for badge in graph.find_nodes(Selector(has_kind=PhraseBadge))
    }
    reenter = TraversableEdge(
        graph=graph,
        predecessor_id=aftermath.uid,
        successor_id=aftermath.uid,
        label="Reflect again",
    )
    duplicate = graph.add_node(
        kind=RepertoireAftermathBlock,
        label="duplicate award attempt",
        player_id=player.uid,
        contest_id=contest.uid,
    )
    duplicate_edge = TraversableEdge(
        graph=graph,
        predecessor_id=aftermath.uid,
        successor_id=duplicate.uid,
        label="Try to learn again",
    )
    next_contest = graph.add_node(
        kind=SnapshotContestBlock,
        label="next contest",
        player_id=player.uid,
        opponent_id=contest.opponent_id,
        game_state=CallResponseGame(scoring_n=1),
        scenario_contributions=contest.scenario_contributions,
    )
    next_edge = TraversableEdge(
        graph=graph,
        predecessor_id=duplicate.uid,
        successor_id=next_contest.uid,
        label="Use the learned phrase",
    )

    ledger.resolve_choice(reenter.uid)
    ledger.resolve_choice(duplicate_edge.uid)

    assert aftermath.locals["awarded_phrase_ids"] == ["reply"]
    assert duplicate.locals["awarded_phrase_ids"] == []
    assert {
        badge.uid
        for badge in graph.find_nodes(Selector(has_kind=PhraseBadge))
    } == badge_ids_before
    assert player.repertoire.badges().count(learned_badge) == 1
    assert next_contest.game.phase is GamePhase.PENDING

    ledger.resolve_choice(next_edge.uid)

    assert next_contest.game.phase is GamePhase.READY
    assert "reply" in next_contest.game.player_phrase_ids
    assert {
        edge.payload["move"]
        for edge in next_contest.edges_out(Selector(has_kind=Action))
        if edge.payload is not None
    } == {"reply", "taunt"}


def test_awarded_badge_survives_fresh_catalog_graph_roundtrip() -> None:
    _graph, ledger, player, _opponent, _contest, _aftermath = _play_terminal_loss(
        initial_player_has_initiative=True,
    )
    learned_badge = next(
        badge for badge in player.repertoire.badges() if badge.token_from == "reply"
    )
    payload = ledger.graph.unstructure()

    PhraseType.clear_instances()
    definitions = _install_phrase_types()
    restored = Graph.structure(payload)
    restored_player = restored.get(player.uid)
    restored_badge = restored.get(learned_badge.uid)

    assert isinstance(restored_player, RepertoireParticipant)
    assert isinstance(restored_badge, PhraseBadge)
    assert restored_player.repertoire.owner is restored_player
    assert restored_badge.uid == learned_badge.uid
    assert restored_badge in restored_player.repertoire.badges()
    assert restored_badge.reference_singleton is definitions["reply"]


def test_win_aftermath_awards_a_separate_catalog_prize() -> None:
    graph, _ledger, player, _opponent, _contest, aftermath = _play_terminal_win()
    prize = player.prizes.prizes()[0]
    holder = ComponentSlotAssetHolder(player.prizes, KNOWN_PRIZES_SLOT)

    assert aftermath.locals["awarded_prize_ids"] == ["golden_trophy"]
    assert player.prizes.prize_ids() == ["golden_trophy"]
    assert player.prizes.has_received_prize("golden_trophy")
    assert prize in graph.find_nodes(Selector(has_kind=PrizeToken))
    assert [definition.label for definition in _prize_catalog().find_all()] == [
        "golden_trophy",
    ]
    assert prize.reference_singleton in list(_prize_catalog().find_all())
    assert holder.get_asset("golden_trophy") is prize
    assert holder.get_asset(prize.label) is prize
    assert holder.get_asset_key(prize) == prize.label
    assert player.repertoire.phrase_ids() == ["taunt"]
    assert {
        badge.token_from
        for badge in graph.find_nodes(Selector(has_kind=PhraseBadge))
    } == {"taunt", "reply", "late_reply"}


def test_prize_aftermath_does_not_award_after_a_player_loss() -> None:
    _install_prize_types()
    graph, ledger, player, _opponent, contest, _late_badge, current_contest = _snapshot_graph()
    aftermath = _add_prize_aftermath(
        graph,
        player=player,
        contest=contest,
        predicate="game_lost",
        label="no trophy after defeat",
    )
    ledger.resolve_choice(current_contest.uid)
    action = next(
        edge
        for edge in contest.edges_out(Selector(has_kind=Action))
        if edge.payload == {"move": "taunt"}
    )
    ledger.resolve_choice(action.uid, choice_payload=action.payload)

    assert contest.game.result is GameResult.LOSE
    assert ledger.cursor_id == aftermath.uid
    assert aftermath.locals["awarded_prize_ids"] == []
    assert player.prizes.prizes() == []


def test_prize_aftermath_is_idempotent_across_award_attempts() -> None:
    graph, ledger, player, _opponent, contest, aftermath = _play_terminal_win()
    prize = player.prizes.prizes()[0]
    prize_ids_before = {
        token.uid
        for token in graph.find_nodes(Selector(has_kind=PrizeToken))
    }
    reenter = TraversableEdge(
        graph=graph,
        predecessor_id=aftermath.uid,
        successor_id=aftermath.uid,
        label="Reflect on the prize",
    )
    duplicate = _add_prize_aftermath(
        graph,
        player=player,
        contest=contest,
        predicate="game_won",
        label="duplicate trophy attempt",
    )
    duplicate_edge = TraversableEdge(
        graph=graph,
        predecessor_id=aftermath.uid,
        successor_id=duplicate.uid,
        label="Try to claim another trophy",
    )

    ledger.resolve_choice(reenter.uid)
    ledger.resolve_choice(duplicate_edge.uid)

    assert aftermath.locals["awarded_prize_ids"] == ["golden_trophy"]
    assert duplicate.locals["awarded_prize_ids"] == []
    assert {
        token.uid
        for token in graph.find_nodes(Selector(has_kind=PrizeToken))
    } == prize_ids_before
    assert player.prizes.prizes() == [prize]


def test_prize_grant_history_survives_transfer_and_blocks_a_second_award() -> None:
    graph, ledger, player, opponent, contest, aftermath = _play_terminal_win()
    prize = player.prizes.prizes()[0]
    receipt = TransactionOffer(
        label="trade the trophy",
        commitments=[
            AssetMoveCommitment(
                ComponentSlotAssetHolder(player.prizes, KNOWN_PRIZES_SLOT),
                ComponentSlotAssetHolder(opponent.prizes, KNOWN_PRIZES_SLOT),
                prize,
            ),
        ],
    ).accept()
    prize_ids_before = {
        token.uid
        for token in graph.find_nodes(Selector(has_kind=PrizeToken))
    }
    another_aftermath = graph.add_node(
        kind=PrizeAftermathBlock,
        label="second trophy attempt",
        player_id=player.uid,
        contest_id=contest.uid,
        prize_definition_id="golden_trophy",
    )
    retry_edge = TraversableEdge(
        graph=graph,
        predecessor_id=aftermath.uid,
        successor_id=another_aftermath.uid,
        label="Seek another trophy",
    )

    ledger.resolve_choice(retry_edge.uid)

    assert receipt.commitment_labels == ["move asset"]
    assert player.prizes.prizes() == []
    assert player.prizes.granted_prize_ids == {"golden_trophy"}
    assert opponent.prizes.prizes() == [prize]
    assert prize.uid in opponent.prizes.assignment_ids[KNOWN_PRIZES_SLOT]
    assert another_aftermath.locals["awarded_prize_ids"] == []
    assert {
        token.uid
        for token in graph.find_nodes(Selector(has_kind=PrizeToken))
    } == prize_ids_before


def test_awarded_prize_survives_fresh_catalog_graph_roundtrip() -> None:
    _graph, ledger, player, _opponent, _contest, _aftermath = _play_terminal_win()
    prize = player.prizes.prizes()[0]
    payload = ledger.graph.unstructure()

    PhraseType.clear_instances()
    PrizeType.clear_instances()
    _install_phrase_types()
    prize_definitions = _install_prize_types()
    restored = Graph.structure(payload)
    restored_player = restored.get(player.uid)
    restored_prize = restored.get(prize.uid)

    assert isinstance(restored_player, RepertoireParticipant)
    assert isinstance(restored_prize, PrizeToken)
    assert isinstance(restored_player.prizes, PrizeManager)
    assert restored_player.repertoire.owner is restored_player
    assert restored_player.prizes.owner is restored_player
    assert restored_player.prizes.granted_prize_ids == {"golden_trophy"}
    assert restored_prize.uid == prize.uid
    assert restored_prize in restored_player.prizes.prizes()
    assert restored_prize.reference_singleton is prize_definitions["golden_trophy"]


def test_stable_hub_choices_react_to_a_learned_phrase_after_loss() -> None:
    """Loss acquisition opens its existing phrase gate without rebuilding the hub."""

    opportunity: tuple[OpportunityHubBlock, TraversableEdge, Action, Action] | None = None

    def configure_hub(
        graph: Graph,
        player: RepertoireParticipant,
        current: Block,
    ) -> None:
        nonlocal opportunity
        opportunity = _add_opportunity_hub(graph, player=player, current=current)

    graph, ledger, player, _opponent, contest, _late_badge, current_contest = _snapshot_graph(
        graph_class=StoryGraph,
        configure_current_frontier=configure_hub,
    )
    assert opportunity is not None
    hub, enter_hub, phrase_action, prize_action = opportunity
    current = graph.get(ledger.cursor_id)
    assert isinstance(current, Block)
    return_to_current = TraversableEdge(
        graph=graph,
        predecessor_id=hub.uid,
        successor_id=current.uid,
        label="Return to the contest",
    )
    aftermath = _add_loss_aftermath(graph, player=player, contest=contest)
    return_aftermath = TraversableEdge(
        graph=graph,
        predecessor_id=aftermath.uid,
        successor_id=hub.uid,
        label="Return with what you learned",
    )

    ledger.resolve_choice(enter_hub.uid)

    assert _latest_choice(ledger, phrase_action).available is False
    assert _latest_choice(ledger, prize_action).available is False

    ledger.resolve_choice(return_to_current.uid)
    ledger.resolve_choice(current_contest.uid)
    taunt = next(
        edge
        for edge in contest.edges_out(Selector(has_kind=Action))
        if edge.payload == {"move": "taunt"}
    )
    ledger.resolve_choice(taunt.uid, choice_payload=taunt.payload)
    assert ledger.cursor_id == aftermath.uid

    ledger.resolve_choice(return_aftermath.uid)

    assert player.repertoire.has_phrase("reply")
    assert _latest_choice(ledger, phrase_action).available is True
    assert _latest_choice(ledger, prize_action).available is False


def test_stable_hub_prize_choice_requires_current_possession() -> None:
    """A transferred prize closes its existing gate despite durable grant history."""

    _install_prize_types()
    opportunity: tuple[OpportunityHubBlock, TraversableEdge, Action, Action] | None = None

    def configure_hub(
        graph: Graph,
        player: RepertoireParticipant,
        current: Block,
    ) -> None:
        nonlocal opportunity
        opportunity = _add_opportunity_hub(graph, player=player, current=current)

    graph, ledger, player, opponent, contest, _late_badge, current_contest = _snapshot_graph(
        graph_class=StoryGraph,
        configure_current_frontier=configure_hub,
    )
    contest.scenario_contributions = ()
    assert opportunity is not None
    hub, enter_hub, phrase_action, prize_action = opportunity
    current = graph.get(ledger.cursor_id)
    assert isinstance(current, Block)
    return_to_current = TraversableEdge(
        graph=graph,
        predecessor_id=hub.uid,
        successor_id=current.uid,
        label="Return to the contest",
    )
    aftermath = _add_prize_aftermath(
        graph,
        player=player,
        contest=contest,
        predicate="game_won",
    )
    return_aftermath = TraversableEdge(
        graph=graph,
        predecessor_id=aftermath.uid,
        successor_id=hub.uid,
        label="Return with the trophy",
    )
    refresh_hub = TraversableEdge(
        graph=graph,
        predecessor_id=hub.uid,
        successor_id=hub.uid,
        label="Look around again",
    )

    ledger.resolve_choice(enter_hub.uid)
    assert _latest_choice(ledger, phrase_action).available is False
    assert _latest_choice(ledger, prize_action).available is False

    ledger.resolve_choice(return_to_current.uid)
    ledger.resolve_choice(current_contest.uid)
    taunt = next(
        edge
        for edge in contest.edges_out(Selector(has_kind=Action))
        if edge.payload == {"move": "taunt"}
    )
    ledger.resolve_choice(taunt.uid, choice_payload=taunt.payload)
    assert ledger.cursor_id == aftermath.uid

    ledger.resolve_choice(return_aftermath.uid)
    prize = player.prizes.prizes()[0]

    assert player.repertoire.phrase_ids() == ["taunt"]
    assert _latest_choice(ledger, phrase_action).available is False
    assert _latest_choice(ledger, prize_action).available is True

    TransactionOffer(
        label="trade the trophy",
        commitments=[
            AssetMoveCommitment(
                ComponentSlotAssetHolder(player.prizes, KNOWN_PRIZES_SLOT),
                ComponentSlotAssetHolder(opponent.prizes, KNOWN_PRIZES_SLOT),
                prize,
            ),
        ],
    ).accept()
    ledger.resolve_choice(refresh_hub.uid)

    assert player.prizes.has_received_prize("golden_trophy")
    assert player.prizes.has_prize("golden_trophy") is False
    assert opponent.prizes.prizes() == [prize]
    assert _latest_choice(ledger, prize_action).available is False
