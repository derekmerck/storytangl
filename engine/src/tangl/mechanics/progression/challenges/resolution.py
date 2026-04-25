from __future__ import annotations

from collections.abc import Iterable, Mapping

from ..definition.stat_system import StatSystemDefinition
from ..effects import (
    EffectDonor,
    SituationalEffect,
    TagDonor,
    gather_donor_effects,
    gather_donor_tags,
)
from ..entity.has_stats import HasStats
from ..growth import GrowthHandler
from ..handlers import ProbitStatHandler, StatHandler, get_handler_cls
from ..tasks import inspect_resolution, resolve_task
from ..tasks.resolution import HasWalletLike
from .challenge import StatChallenge
from .result import ChallengeResult


def _resolve_handler(
    entity: HasStats,
    *,
    system: StatSystemDefinition,
    domain: str | None,
) -> type[StatHandler]:
    if domain and domain in entity.stats:
        return entity.stats[domain].handler
    return get_handler_cls(system.handler)


def _tag_eligible_effects(
    effects: Iterable[SituationalEffect],
    *,
    tags: set[str],
) -> list[SituationalEffect]:
    return [effect for effect in effects if effect.applies(tags=tags, stat_name=None)]


def _derive_effective_domain(
    challenge: StatChallenge,
    *,
    system: StatSystemDefinition,
    effects: Iterable[SituationalEffect],
    tags: set[str],
) -> str | None:
    base_domain = challenge.domain
    if base_domain is None and isinstance(challenge.difficulty, Mapping) and challenge.difficulty:
        base_domain = next(iter(challenge.difficulty.keys()))
    if base_domain is None:
        base_domain = system.default_domain

    effective_domain = base_domain
    for effect in _tag_eligible_effects(effects, tags=tags):
        if effect.domain_override:
            effective_domain = effect.domain_override
    return effective_domain


def _remap_wallet(
    wallet_map: Mapping[str, int],
    remap_chain: Iterable[Mapping[str, str]],
) -> dict[str, int]:
    remapped = dict(wallet_map)
    for remap in remap_chain:
        next_map: dict[str, int] = {}
        for currency, amount in remapped.items():
            target = remap.get(currency, currency)
            next_map[target] = next_map.get(target, 0) + amount
        remapped = next_map
    return remapped


def resolve_challenge(
    challenge: StatChallenge,
    entity: HasStats,
    *,
    system: StatSystemDefinition | None = None,
    wallet: HasWalletLike | None = None,
    effects: Iterable[SituationalEffect] = (),
    context_tags: Iterable[str] | None = None,
    effect_donors: Iterable[EffectDonor] = (),
    tag_donors: Iterable[TagDonor] = (),
    defender: HasStats | None = None,
    roll: float | None = None,
    growth_handler: GrowthHandler | None = None,
    apply_growth: bool = True,
) -> ChallengeResult:
    """Resolve one authored stat challenge end to end."""
    system = system or entity.stat_system

    donor_effects = gather_donor_effects(effect_donors)
    donor_tags = gather_donor_tags(tag_donors)
    effective_tags = set(challenge.tags)
    effective_tags.update(context_tags or ())
    effective_tags.update(donor_tags)

    all_effects = [*effects, *donor_effects]
    effective_domain = _derive_effective_domain(
        challenge,
        system=system,
        effects=all_effects,
        tags=effective_tags,
    )
    handler = _resolve_handler(entity, system=system, domain=effective_domain)

    unmet = challenge.unmet_requirements(entity, handler=handler)
    if unmet:
        raise ValueError(f"Challenge requirements not satisfied: {sorted(unmet)}")

    tag_effects = _tag_eligible_effects(all_effects, tags=effective_tags)
    cost_remaps = [effect.cost_currency_remap for effect in tag_effects if effect.cost_currency_remap]
    reward_remaps = [
        effect.reward_currency_remap
        for effect in tag_effects
        if effect.reward_currency_remap
    ]

    effective_cost = _remap_wallet(challenge.cost, cost_remaps)

    if effective_cost and wallet is None:
        raise ValueError("Challenge cost requires a wallet-like target")

    difficulty = challenge.normalized_difficulty(handler=handler, domain=effective_domain)
    if defender is not None:
        defender_domain = challenge.opposed_domain or effective_domain
        difficulty = {effective_domain or defender_domain or "opposed": defender.compute_competency(defender_domain)}

    task = challenge.to_task(
        handler=handler,
        domain=effective_domain,
        difficulty=difficulty,
        cost=effective_cost,
        tags=effective_tags,
    )

    snapshot = inspect_resolution(
        task,
        entity,
        system=system,
        effects=all_effects,
        context_tags=effective_tags,
        handler=handler,
    )
    outcome = resolve_task(
        task,
        entity,
        system=system,
        effects=all_effects,
        context_tags=effective_tags,
        handler=handler,
        wallet=wallet,
        auto_spend=True,
        auto_reward=False,
        roll=roll,
    )

    payout = _remap_wallet(challenge.payout.reward_for(outcome), reward_remaps)
    if wallet is not None and payout:
        wallet.earn(payout)

    active_effects: list[SituationalEffect] = []
    seen_effects: set[int] = set()
    for effect in [*tag_effects, *snapshot.modifier_totals.active_effects]:
        effect_id = id(effect)
        if effect_id in seen_effects:
            continue
        seen_effects.add(effect_id)
        active_effects.append(effect)

    result = ChallengeResult(
        challenge_name=challenge.name,
        domain=effective_domain,
        effective_competency=snapshot.effective_competency,
        effective_difficulty=snapshot.effective_difficulty,
        delta=snapshot.delta,
        success_likelihood=snapshot.handler.likelihood(snapshot.delta),
        outcome=outcome,
        cost_paid=effective_cost,
        payout_granted=payout,
        active_effects=active_effects,
    )

    if growth_handler is not None:
        growth_receipt = growth_handler.grow(
            entity,
            challenge,
            result,
            apply=apply_growth,
        )
        result.growth_receipt = growth_receipt

    return result
