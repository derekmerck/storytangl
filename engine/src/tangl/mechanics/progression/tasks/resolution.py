from __future__ import annotations

from typing import Iterable, Optional, Protocol

from ..definition.stat_system import StatSystemDefinition
from ..effects.modifier_stack import aggregate_modifiers
from ..effects.situational import SituationalEffect
from ..handlers.base import StatHandler
from ..handlers.probit import ProbitStatHandler
from ..outcomes import Outcome, sample_outcome
from ..entity.has_stats import HasStats
from .task import Task


class HasWalletLike(Protocol):
    """
    Protocol for types that behave like HasWallet for basic operations.

    This is intentionally minimal so that tests can use simple stand-ins.
    """

    wallet: dict[str, int]

    def can_afford(self, cost: dict[str, int]) -> bool: ...

    def spend(self, cost: dict[str, int]) -> None: ...

    def earn(self, reward: dict[str, int]) -> None: ...


def compute_delta(
    task: Task,
    entity: HasStats,
    *,
    system: Optional[StatSystemDefinition] = None,
    effects: Iterable[SituationalEffect] = (),
    context_tags: Iterable[str] | None = None,
    dominance_attacker_domain: Optional[str] = None,
    dominance_defender_domain: Optional[str] = None,
    handler: type[StatHandler] | None = None,
) -> float:
    """
    Compute the net delta = effective_competency - effective_difficulty
    for this task and entity.

    Pieces
    ------
    - domain: inferred from task/system.
    - base competency: entity.compute_competency(domain).
    - base difficulty: task.get_difficulty(domain, system).
    - dominance: system.get_dominance(attacker, defender) (if both given).
        Positive dominance means the attacker has the advantage, so
        we *subtract* it from difficulty (making the check easier).
    - situational effects:
        - aggregated and clamped via handler.clamp_modifiers().
        - competency / difficulty channels kept separate.
    - context bonuses (optional):
        - system.context_bonuses[context_tag][domain]
        - we treat these as *competency* bonuses summed over tags.

    Notes
    -----
    This function does **not** sample an Outcome. That is done by
    `resolve_task`.
    """
    system = system or entity.stat_system

    # Determine domain
    domain = task.infer_domain(system)

    # Base competency (may average intrinsic+domain)
    competency = entity.compute_competency(domain)

    # Base difficulty
    difficulty = task.get_difficulty(domain=domain, system=system)

    # Dominance: attacker vs defender, if given
    dominance_bonus = 0.0
    if dominance_attacker_domain and dominance_defender_domain:
        dominance_bonus = system.get_dominance(
            dominance_attacker_domain,
            dominance_defender_domain,
        )

    # Context bonuses: treat as competency bonuses
    context_tags = set(context_tags or ())
    context_bonus = 0.0
    for tag in context_tags:
        context_bonus += system.get_context_bonus(tag, domain or "")

    # Situational effects
    handler = handler or (
        # If domain has a Stat with a handler, use that
        (entity.stats.get(domain).handler if domain and domain in entity.stats else None)
        or ProbitStatHandler
    )

    modifier_totals = aggregate_modifiers(
        effects,
        tags=context_tags,
        stat_name=domain,
        handler=handler,
    )

    # Effective values
    effective_competency = (
        competency
        + context_bonus
        + modifier_totals.clamped_competency
    )
    effective_difficulty = (
        difficulty
        # Positive dominance makes task easier → reduces difficulty
        - dominance_bonus
        + modifier_totals.clamped_difficulty
    )

    return effective_competency - effective_difficulty


def resolve_task(
    task: Task,
    entity: HasStats,
    *,
    system: Optional[StatSystemDefinition] = None,
    effects: Iterable[SituationalEffect] = (),
    context_tags: Iterable[str] | None = None,
    dominance_attacker_domain: Optional[str] = None,
    dominance_defender_domain: Optional[str] = None,
    handler: type[StatHandler] | None = None,
    wallet: Optional[HasWalletLike] = None,
    auto_spend: bool = True,
    auto_reward: bool = True,
    roll: float | None = None,
) -> Outcome:
    """
    Resolve a Task against an entity, producing an Outcome.

    Parameters
    ----------
    task:
        The challenge definition.
    entity:
        Must implement HasStats.
    system:
        Optional explicit StatSystemDefinition. Defaults to entity.stat_system.
    effects:
        Iterable of SituationalEffect currently in scope.
    context_tags:
        Scenario tags (e.g. {"#combat", "#night"}). If omitted, uses task.tags.
    dominance_attacker_domain / dominance_defender_domain:
        Optional dominance matchup; if provided, will be read from system.
    handler:
        Optional StatHandler subclass to use for likelihood. If omitted,
        we prefer the handler on the domain Stat, then ProbitStatHandler.
    wallet:
        Optional wallet-like object (HasWallet or stand-in). If provided and
        `auto_spend`/`auto_reward` are True, cost and reward will be applied.
    auto_spend:
        If True and wallet is provided, cost is charged before resolution
        (raises ValueError if cannot afford).
    auto_reward:
        If True and wallet is provided, reward is granted after resolution.

    Returns
    -------
    Outcome
    """
    system = system or entity.stat_system

    # Spend cost up-front if requested
    if wallet is not None and auto_spend and task.cost:
        if not wallet.can_afford(dict(task.cost)):
            raise ValueError(f"Wallet cannot afford task cost: {task.cost!r}")
        wallet.spend(dict(task.cost))

    # Compute delta
    if context_tags is None:
        effective_tags = task.tags
    else:
        effective_tags = context_tags
    delta = compute_delta(
        task,
        entity,
        system=system,
        effects=effects,
        context_tags=effective_tags,
        dominance_attacker_domain=dominance_attacker_domain,
        dominance_defender_domain=dominance_defender_domain,
        handler=handler,
    )

    # Choose handler
    domain = task.infer_domain(system)
    final_handler: type[StatHandler] = handler or (
        (entity.stats.get(domain).handler if domain and domain in entity.stats else None)
        or ProbitStatHandler
    )

    # Likelihood and outcome
    p_success = final_handler.likelihood(delta)
    outcome = sample_outcome(p_success, roll=roll)

    # Apply reward after resolution if requested
    if wallet is not None and auto_reward and task.reward:
        wallet.earn(dict(task.reward))

    return outcome
