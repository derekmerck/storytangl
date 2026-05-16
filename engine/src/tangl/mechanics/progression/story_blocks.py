from __future__ import annotations

"""Thin story-facing facets over :func:`resolve_challenge`.

Two deliberately separate mixins, not one mode-flagged block:

* :class:`HasStatChallenge` -- an *event check*: resolves an authored
  ``StatChallenge`` against the protagonist and exposes
  ``challenge_passed`` / ``challenge_failed`` / ``challenge_outcome`` /
  ``challenge_quality`` in the predicate namespace so authored
  ``continues`` / ``redirects`` can branch (mirrors ``HasGame``'s
  ``game_won`` / ``game_lost`` pattern).
* :class:`HasTraining` -- a *training* activity: resolves a training-tagged
  challenge with a growth handler so the chosen skill improves; normally no
  pass/fail branch.

The protagonist is read from the scoped namespace under ``player`` (published
by the story ``gather_player_fixture`` handler), so these facets need no
bespoke actor lookup.
"""

from typing import Any, ClassVar

from tangl.vm import (
    on_gather_ns,
    on_journal,
    on_update,
)

from .challenges import StatChallenge, resolve_challenge
from .entity.has_stats import HasStats
from .entity.has_wallet import HasWallet
from .growth import GrowthHandler, LinearGrowthHandler
from .outcomes import Outcome


class HasStatChallenge:
    """Block facet that resolves an authored stat challenge on visit."""

    _challenge: ClassVar[StatChallenge] = StatChallenge()
    _growth_handler: ClassVar[GrowthHandler | None] = None


class HasTraining:
    """Block facet that trains one skill on visit.

    Configuration knobs are underscore-prefixed (like ``HasGame._game_class``)
    so authored subclasses can override them without pydantic treating them
    as model fields.
    """

    _training_skill: ClassVar[str] = ""
    _training_difficulty: ClassVar[Any] = "ok"
    _training_tags: ClassVar[frozenset[str]] = frozenset({"training"})
    _growth_handler: ClassVar[GrowthHandler | None] = None


def _actor(cursor: Any, ctx: Any) -> HasStats | None:
    actor = ctx.get_ns(cursor).get("player")
    return actor if isinstance(actor, HasStats) else None


def _refresh_ns_cache(ctx: Any) -> None:
    """Drop cached namespaces so POSTREQS/continues see fresh challenge flags."""
    cache = getattr(ctx, "_ns_cache", None)
    if isinstance(cache, dict):
        cache.clear()
    inflight = getattr(ctx, "_ns_inflight", None)
    if isinstance(inflight, set):
        inflight.clear()


@on_update(wants_caller_kind=HasStatChallenge, wants_exact_kind=False)
def resolve_stat_challenge(
    cursor: HasStatChallenge | None = None,
    *,
    caller: HasStatChallenge | None = None,
    ctx: Any,
    **_kw: Any,
):
    """Resolve the challenge and record predicate-friendly outcome flags."""
    cursor = cursor if isinstance(cursor, HasStatChallenge) else caller
    if not isinstance(cursor, HasStatChallenge):
        return None
    actor = _actor(cursor, ctx)
    if actor is None:
        return None

    result = resolve_challenge(
        cursor._challenge,
        actor,
        wallet=actor if isinstance(actor, HasWallet) else None,
        context_tags=getattr(cursor, "tags", None),
        growth_handler=cursor._growth_handler,
    )

    passed = result.outcome >= Outcome.SUCCESS
    cursor.locals["challenge_outcome"] = int(result.outcome)
    cursor.locals["challenge_quality"] = result.outcome_label
    cursor.locals["challenge_passed"] = passed
    cursor.locals["challenge_failed"] = not passed
    cursor.locals["_challenge_result"] = result
    _refresh_ns_cache(ctx)
    return None


@on_gather_ns(wants_caller_kind=HasStatChallenge, wants_exact_kind=False)
def inject_challenge_context(
    cursor: HasStatChallenge | None = None,
    *,
    caller: HasStatChallenge | None = None,
    ctx: Any,
    **_kw: Any,
) -> dict[str, Any]:
    """Expose challenge outcome to the predicate namespace."""
    cursor = cursor if isinstance(cursor, HasStatChallenge) else caller
    if not isinstance(cursor, HasStatChallenge):
        return {}
    store = cursor.locals
    return {
        "challenge_passed": bool(store.get("challenge_passed")),
        "challenge_failed": bool(store.get("challenge_failed")),
        "challenge_outcome": store.get("challenge_outcome"),
        "challenge_quality": store.get("challenge_quality"),
    }


@on_journal(wants_caller_kind=HasStatChallenge, wants_exact_kind=False)
def journal_stat_challenge(
    cursor: HasStatChallenge | None = None,
    *,
    caller: HasStatChallenge | None = None,
    ctx: Any,
    **_kw: Any,
):
    """Emit a compact result fragment (full journal contract is later work)."""
    from tangl.journal.fragments import ContentFragment

    cursor = cursor if isinstance(cursor, HasStatChallenge) else caller
    if not isinstance(cursor, HasStatChallenge):
        return []
    quality = cursor.locals.get("challenge_quality")
    if not quality:
        return []
    name = cursor._challenge.name or "Challenge"
    return [ContentFragment(content=f"{name}: {quality}.")]


@on_update(wants_caller_kind=HasTraining, wants_exact_kind=False)
def apply_training(
    cursor: HasTraining | None = None,
    *,
    caller: HasTraining | None = None,
    ctx: Any,
    **_kw: Any,
):
    """Resolve a training challenge so the chosen skill grows."""
    cursor = cursor if isinstance(cursor, HasTraining) else caller
    if not isinstance(cursor, HasTraining):
        return None
    actor = _actor(cursor, ctx)
    skill = cursor._training_skill
    if actor is None or not skill or skill not in actor.stats:
        return None

    challenge = StatChallenge(
        name=f"Train {skill}",
        domain=skill,
        difficulty=cursor._training_difficulty,
        tags=set(cursor._training_tags),
    )
    handler = cursor._growth_handler or LinearGrowthHandler()
    result = resolve_challenge(
        challenge,
        actor,
        context_tags=set(cursor._training_tags),
        growth_handler=handler,
    )
    receipt = result.growth_receipt
    cursor.locals["trained_skill"] = skill
    cursor.locals["trained_gain"] = (
        receipt.applied_deltas.get(skill, 0.0) if receipt else 0.0
    )
    return None
