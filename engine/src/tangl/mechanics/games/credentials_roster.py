"""
Roster sampling and lazy offer materialization (Phase A.3, compact).

A shift is authored as a :class:`ShiftSpec` (rules + an origin distribution + a
disposition-class distribution + a few pinned encounters). :func:`generate_roster`
does all the sampling once and returns a list of :class:`ScenarioOffer` -- a
*promise* of an encounter (origin, purpose, target disposition, and the verified
failure mode that realizes it). The concrete candidate packet is built only when
the encounter arrives, via :func:`materialize`.

This is the compact exercise of the legacy procedural-candidate strategy: sample
by origin / pace, pick an appropriate failure mode per sample, and don't
materialize until called. Multi-day shifts and live roster editing are just
repeated generation and ordinary list edits on the offers; no extra machinery.
"""
from __future__ import annotations

import random
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from pydantic import Field

from tangl.core.bases import Unstructurable

from .credentials_enums import (
    FailureClass,
    FailureMode,
    IndicationId,
    OriginId,
    Indication,
    Region,
    PURPOSES,
    RestrictionLevel,
    Restrictions,
)
from .credentials_factory import applicable_modes, build_valid, degrade, render_narrative
from .credentials_game import (
    CredentialCase,
    CredentialDisposition,
    CredentialsGame,
    derive_disposition,
)

# A target disposition is just a CredentialDisposition: PASS = allow,
# DENY = invalid-but-mitigatable, ARREST = invalid-illegal.
_DEFAULT_DISPOSITIONS = {
    CredentialDisposition.PASS: 0.4,
    CredentialDisposition.DENY: 0.3,
    CredentialDisposition.ARREST: 0.3,
}


class ScenarioOffer(Unstructurable):
    """A promised encounter -- enough to materialize a candidate on arrival.

    Sampling (origin / disposition / failure mode) happens once at roster
    generation; the packet is built lazily by :func:`materialize`. A ``pinned_case``
    is a fully-authored Tier 1 candidate that materializes verbatim.
    """

    target_disposition: CredentialDisposition = CredentialDisposition.PASS
    region: OriginId = Region.LOCAL
    purpose: IndicationId = Indication.TRAVEL
    candidate_name: str = "Traveler"
    contraband: list[IndicationId] = Field(default_factory=list)
    failure_modes: list[FailureMode] = Field(default_factory=list)
    whitelist: bool = False
    blacklist: bool = False
    pinned_case: CredentialCase | None = Field(
        default=None,
        json_schema_extra={"include": True, "unstructurable": True},
    )


@dataclass(frozen=True)
class ShiftSpec:
    """Generation-time recipe for one shift's roster (not persisted game state)."""

    rules: Restrictions
    encounters: int = 5
    origin_distribution: dict[OriginId, float] = field(
        default_factory=lambda: {Region.LOCAL: 1.0}
    )
    disposition_distribution: dict[CredentialDisposition, float] = field(
        default_factory=lambda: dict(_DEFAULT_DISPOSITIONS)
    )
    purpose_pool: Sequence[IndicationId] = tuple(sorted(PURPOSES))
    allowed_failure_modes: Sequence[FailureMode] | None = None
    pinned: Sequence[ScenarioOffer] = ()
    seed: int | None = None


def _weighted_choice(distribution: dict, rng: random.Random):
    return rng.choices(list(distribution.keys()), weights=list(distribution.values()), k=1)[0]


def _verified_offer(
    region: OriginId,
    purpose: IndicationId,
    target: CredentialDisposition,
    rules: Restrictions,
    rng: random.Random,
    allowed_failure_modes: Sequence[FailureMode] | None = None,
) -> ScenarioOffer | None:
    """Build an offer for ``(region, purpose)`` that derives to ``target``, or None.

    Returns None when the combination cannot reach the target -- e.g. PASS for a
    purpose that is FORBIDDEN in this region (an inherent infraction no packet can
    clear). Verifies against :func:`derive_disposition`, so the linchpin invariant
    holds by construction.
    """

    base = build_valid(region, purpose, rules)
    base_disposition = derive_disposition(base, rules)

    if target is base_disposition:
        # Already at the target with no failure (e.g. a forbidden purpose -> deny).
        return ScenarioOffer(target_disposition=target, region=region, purpose=purpose)
    if target is CredentialDisposition.PASS:
        return None

    failure_class = (
        FailureClass.MITIGATABLE if target is CredentialDisposition.DENY else FailureClass.CRIME
    )
    candidates = applicable_modes(base, failure_class)
    if allowed_failure_modes is not None:
        candidates = [mode for mode in candidates if mode in allowed_failure_modes]
    rng.shuffle(candidates)
    for mode in candidates:
        trial = degrade(build_valid(region, purpose, rules), [mode])
        if derive_disposition(trial, rules) is target:
            return ScenarioOffer(
                target_disposition=target,
                region=region,
                purpose=purpose,
                failure_modes=[mode],
            )
    return None


def make_offer(
    region: OriginId,
    purpose: IndicationId,
    target: CredentialDisposition,
    rules: Restrictions,
    rng: random.Random | None = None,
) -> ScenarioOffer:
    """A verified offer for ``target``, or a best-effort offer at this purpose's
    inherent disposition if ``target`` is unreachable here."""

    rng = rng or random.Random()
    offer = _verified_offer(region, purpose, target, rules, rng)
    if offer is not None:
        return offer
    base = build_valid(region, purpose, rules)
    return ScenarioOffer(
        target_disposition=derive_disposition(base, rules), region=region, purpose=purpose
    )


def generate_roster(spec: ShiftSpec, rng: random.Random | None = None) -> list[ScenarioOffer]:
    """Sample a shift's worth of offers, inserting pinned encounters at random spots.

    For each slot: sample an origin and a target disposition, then pick the first
    purpose (shuffled) that can actually reach that target in that region.
    """

    rng = rng or random.Random(spec.seed)
    pinned = list(spec.pinned)
    sampled_count = max(spec.encounters - len(pinned), 0)

    roster: list[ScenarioOffer] = []
    for _ in range(sampled_count):
        region = _weighted_choice(spec.origin_distribution, rng)
        target = _weighted_choice(spec.disposition_distribution, rng)
        purposes = list(spec.purpose_pool)
        rng.shuffle(purposes)

        offer = None
        for purpose in purposes:
            offer = _verified_offer(
                region,
                purpose,
                target,
                spec.rules,
                rng,
                spec.allowed_failure_modes,
            )
            if offer is not None:
                break
        roster.append(offer or make_offer(region, purposes[0], target, spec.rules, rng))

    for offer in pinned:
        roster.insert(rng.randint(0, len(roster)), offer)
    return roster


def materialize(
    offer: ScenarioOffer,
    rules: Restrictions,
    *,
    narrative_renderer: Callable[[CredentialCase], CredentialCase] | None = None,
) -> CredentialCase:
    """Build the concrete candidate for ``offer`` (deterministic).

    Replays the offer's verified failure modes onto a fresh valid packet, so the
    materialized case derives to the offer's ``target_disposition`` (context
    overrides like whitelist are applied for the game's ``expected_disposition``).
    """

    if offer.pinned_case is not None:
        return offer.pinned_case

    case = build_valid(
        offer.region,
        offer.purpose,
        rules,
        candidate_name=offer.candidate_name,
        contraband=list(offer.contraband),
    )
    degrade(case, offer.failure_modes)
    (narrative_renderer or render_narrative)(case)
    case.whitelist = offer.whitelist
    case.blacklist = offer.blacklist
    return case


# Resolve the ``offers: list["ScenarioOffer"]`` forward reference on the game now
# that ScenarioOffer exists. credentials_game cannot import this module at load
# time (it would cycle through derive_disposition), so the rebuild lives here.
CredentialsGame.model_rebuild(_types_namespace={"ScenarioOffer": ScenarioOffer})
