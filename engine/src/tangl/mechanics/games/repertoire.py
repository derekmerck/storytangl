"""Catalog definitions and graph-owned badge repertoires for call-response games."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Iterable, Literal

from pydantic import BaseModel, ConfigDict, Field

from tangl.core import DispatchLayer, Priority, Selector, Singleton, Token
from tangl.mechanics.assembly import ComponentManager, Slot

from .call_response_game import DominanceMatch, PhraseRole


KNOWN_PHRASES_SLOT = "known_phrases"

DominanceResult = Literal["match", "miss"]


class DominanceContribution(BaseModel):
    """One authored decision over an ordered call/response pairing.

    Why
    ---
    Phrase definitions, worlds, and later badge-local state need one common
    declaration shape before their contributions are folded into a game-local
    schedule.

    Key Features
    ------------
    - Uses ordinary :class:`Selector` values for call and response matching.
    - Reuses dispatch layer and priority for override ordering.
    - Keeps explicit ``match`` and ``miss`` decisions distinguishable from an
      undeclared default miss.

    API
    ---
    :func:`compose_dominance_schedule` folds bounded definitions and explicit
    extra contributions into :class:`DominanceMatch` values.

    Notes
    -----
    Contributions declare rules only. They neither discover authorities nor
    mutate graph or game state.
    """

    model_config = ConfigDict(frozen=True)

    call_selector: Selector
    response_selector: Selector
    result: DominanceResult
    dispatch_layer: DispatchLayer
    priority: Priority
    source_id: str


class DominanceContradiction(BaseModel):
    """An equal-tier positive and negative decision for one phrase pair.

    Why
    ---
    Equal-tier contradictions remain executable through negative precedence,
    but must be visible to an author rather than silently discarded.

    Key Features
    ------------
    - Names the bounded phrase pair and its decisive ordering tier.
    - Retains positive and negative source identifiers without rendered prose.

    API
    ---
    ``positive_source_ids`` and ``negative_source_ids`` identify the competing
    declarations in deterministic source-id order.

    Notes
    -----
    The composer settles a contradiction as an explicit miss; this value is
    diagnostic evidence, not an alternate resolution path.
    """

    model_config = ConfigDict(frozen=True)

    call_phrase_id: str
    response_phrase_id: str
    dispatch_layer: DispatchLayer
    priority: Priority
    positive_source_ids: tuple[str, ...]
    negative_source_ids: tuple[str, ...]


@dataclass(frozen=True)
class DominanceComposition:
    """Settled bounded schedule plus equal-tier contradiction diagnostics.

    Why
    ---
    The pure composer needs to return the game-ready schedule and the small
    authoring evidence required when negative precedence resolves a conflict.

    Key Features
    ------------
    - ``schedule`` is directly assignable to ``CallResponseGame.schedule``.
    - ``diagnostics`` contains only contradictory winning tiers.

    API
    ---
    :func:`compose_dominance_schedule` constructs this value from explicit
    bounded participants and contributions.

    Notes
    -----
    This is a transient composition result, not graph-owned game state.
    """

    schedule: list[DominanceMatch]
    diagnostics: list[DominanceContradiction]


class PhraseType(Singleton):
    """Immutable catalog definition for one call-response phrase.

    Why
    ---
    Phrase text and role capability are semantic catalog truth, while earned
    instances remain mutable graph-owned badges.

    Key Features
    ------------
    - Stores the phrase's display text and allowed call/response roles.
    - Retains the ordinary singleton tag surface for world-authored catalogs.

    API
    ---
    Use :class:`PhraseBadge` for a graph-owned earned instance.

    Notes
    -----
    A selected :class:`~tangl.core.TokenCatalog` bounds a world's available
    definitions; this class does not enumerate or own a catalog.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str
    roles: tuple[PhraseRole, ...]
    base_contributions: tuple[DominanceContribution, ...] = Field(default_factory=tuple)


PhraseBadge = Token._create_wrapper_cls(PhraseType, "PhraseBadge")


class RepertoireManager(ComponentManager[PhraseBadge]):
    """Owner-bound collection of earned phrase badges.

    Why
    ---
    Reuses ordinary component ownership and transfer semantics rather than
    making learned phrases a special inventory or registry.

    Key Features
    ------------
    - Persists badge membership by graph UUID through ``ComponentManager``.
    - Exposes one large ``known_phrases`` slot for later contest snapshots.

    API
    ---
    :meth:`badges`, :meth:`phrase_ids`, and :meth:`has_phrase` expose the
    small read surface needed by the following composition slice.
    """

    slots: ClassVar[dict[str, Slot]] = {
        KNOWN_PHRASES_SLOT: Slot.for_type(
            KNOWN_PHRASES_SLOT,
            PhraseBadge,
            max_count=1000,
        ),
    }

    def badges(self) -> list[PhraseBadge]:
        """Return known badges in stable definition/id order."""

        return sorted(
            self.get_slot(KNOWN_PHRASES_SLOT),
            key=lambda badge: (badge.token_from, str(badge.uid)),
        )

    def phrase_ids(self) -> list[str]:
        """Return known phrase-definition identifiers in badge order."""

        return [badge.token_from for badge in self.badges()]

    def has_phrase(self, phrase_id: str) -> bool:
        """Return whether this repertoire currently owns a matching badge."""

        return phrase_id in self.phrase_ids()


def compose_dominance_schedule(
    call_phrases: Iterable[PhraseType],
    response_phrases: Iterable[PhraseType],
    *,
    contributions: Iterable[DominanceContribution] = (),
) -> DominanceComposition:
    """Fold bounded phrase definitions and layered decisions into a schedule.

    Undeclared pairs remain absent so the fixed call-response kernel retains its
    ordinary default-miss behavior. Explicit negative decisions remain schedule
    entries to preserve their authored source.
    """

    calls = _role_capable_phrases(call_phrases, "call")
    responses = _role_capable_phrases(response_phrases, "response")
    participants = {phrase.label: phrase for phrase in [*calls, *responses]}
    declared = [
        contribution
        for phrase in sorted(participants.values(), key=lambda phrase: phrase.label)
        for contribution in phrase.base_contributions
    ]
    declared.extend(contributions)

    schedule: list[DominanceMatch] = []
    diagnostics: list[DominanceContradiction] = []
    for call_phrase in calls:
        for response_phrase in responses:
            matched = [
                contribution
                for contribution in declared
                if contribution.call_selector.matches(call_phrase)
                and contribution.response_selector.matches(response_phrase)
            ]
            if not matched:
                continue

            winning_layer = max(contribution.dispatch_layer for contribution in matched)
            layered = [
                contribution
                for contribution in matched
                if contribution.dispatch_layer == winning_layer
            ]
            winning_priority = max(contribution.priority for contribution in layered)
            tier = [
                contribution
                for contribution in layered
                if contribution.priority == winning_priority
            ]
            positive = sorted(
                (contribution for contribution in tier if contribution.result == "match"),
                key=lambda contribution: contribution.source_id,
            )
            negative = sorted(
                (contribution for contribution in tier if contribution.result == "miss"),
                key=lambda contribution: contribution.source_id,
            )
            if positive and negative:
                diagnostics.append(
                    DominanceContradiction(
                        call_phrase_id=call_phrase.label,
                        response_phrase_id=response_phrase.label,
                        dispatch_layer=winning_layer,
                        priority=winning_priority,
                        positive_source_ids=tuple(
                            contribution.source_id for contribution in positive
                        ),
                        negative_source_ids=tuple(
                            contribution.source_id for contribution in negative
                        ),
                    )
                )

            winner = negative[0] if negative else positive[0]
            schedule.append(
                DominanceMatch(
                    call_phrase_id=call_phrase.label,
                    response_phrase_id=response_phrase.label,
                    matched=winner.result == "match",
                    source_id=winner.source_id,
                )
            )

    return DominanceComposition(schedule=schedule, diagnostics=diagnostics)


def _role_capable_phrases(
    phrases: Iterable[PhraseType],
    role: PhraseRole,
) -> list[PhraseType]:
    """Return unique role-capable phrases in stable identifier order."""

    by_label = {phrase.label: phrase for phrase in phrases if role in phrase.roles}
    return [by_label[label] for label in sorted(by_label)]
