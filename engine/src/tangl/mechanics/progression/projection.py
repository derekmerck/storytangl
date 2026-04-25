from __future__ import annotations

from collections.abc import Mapping

from .handlers import ProbitStatHandler, StatHandler
from .measures import Quality
from .outcomes import Outcome
from .stats.stat import Stat, ValueLike

_QUALITY_LABELS: dict[Quality, str] = {
    Quality.VERY_POOR: "very poor",
    Quality.POOR: "poor",
    Quality.MID: "ok",
    Quality.HIGH: "good",
    Quality.VERY_HIGH: "very good",
}

_OUTCOME_LABELS: dict[Outcome, str] = {
    Outcome.DISASTER: "disaster",
    Outcome.FAILURE: "failure",
    Outcome.SUCCESS: "success",
    Outcome.MAJOR_SUCCESS: "major success",
}


def project_quality(
    value: ValueLike | Stat,
    *,
    handler: type[StatHandler] = ProbitStatHandler,
) -> Quality:
    """Project a stat-like value to the canonical five-tier quality scale."""
    if isinstance(value, Stat):
        return value.quality

    fv = Stat.normalize_value(value, handler=handler)
    return Quality(handler.qv_from_fv(fv))


def project_quality_label(
    value: ValueLike | Stat,
    *,
    handler: type[StatHandler] = ProbitStatHandler,
) -> str:
    """Project a stat-like value to a human-readable quality label."""
    return _QUALITY_LABELS[project_quality(value, handler=handler)]


def project_outcome_label(outcome: Outcome) -> str:
    """Map an outcome band to a compact narrative label."""
    return _OUTCOME_LABELS[outcome]


def project_payout_quality(payout: Mapping[str, int]) -> Quality | None:
    """
    Project a wallet-shaped payout into a coarse reward quality band.

    This intentionally preserves only relative narrative magnitude.
    """
    total = sum(max(0, amount) for amount in payout.values())
    if total <= 0:
        return None
    if total == 1:
        return Quality.MID
    if total <= 3:
        return Quality.HIGH
    return Quality.VERY_HIGH


def project_payout_label(payout: Mapping[str, int]) -> str:
    """Map a payout vector to a compact narrative label."""
    quality = project_payout_quality(payout)
    if quality is None:
        return "no reward"
    return _QUALITY_LABELS[quality]
