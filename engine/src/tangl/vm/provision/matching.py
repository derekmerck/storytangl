from __future__ import annotations

from typing import Any

from tangl.core import Selector

from .provisioner import ProvisionOffer


def _selector_criteria(selector: Selector) -> dict[str, Any]:
    return dict(selector.__pydantic_extra__ or {})


def _base_weight(name: str) -> int:
    if name == "has_identifier":
        return 100
    if name == "has_kind":
        return 70
    if name.startswith("has_"):
        return 30
    return 10


def _exact_bonus(name: str, target: Any, candidate: Any) -> int:
    if candidate is None:
        return 0

    if name == "has_kind" and isinstance(target, type):
        if candidate.__class__ is target:
            return 40
        if isinstance(candidate, target):
            return 20
        return 0

    if name == "has_identifier" and hasattr(candidate, "get_identifiers"):
        try:
            if target in candidate.get_identifiers():
                return 30
        except Exception:
            return 0
        return 0

    if name == "label":
        return 20 if getattr(candidate, "label", None) == target else 0

    return 0


def _exact_kind_match(selector: Selector, candidate: Any) -> bool:
    if candidate is None:
        return False
    target = _selector_criteria(selector).get("has_kind")
    if not isinstance(target, type):
        return False
    if type(candidate) is target:
        return True

    # Token wrappers expose the referenced singleton type via ``wrapped_cls``.
    wrapped_cls = getattr(type(candidate), "wrapped_cls", None)
    if isinstance(wrapped_cls, type) and wrapped_cls is target:
        return True

    # EntityTemplate candidates should rank exact when payload kind is exact.
    candidate_dict = getattr(candidate, "__dict__", None)
    if isinstance(candidate_dict, dict):
        payload = candidate_dict.get("payload")
        if payload is not None and type(payload) is target:
            return True

    return False


def score_selector_specificity(selector: Selector, candidate: Any = None) -> int:
    """Compute a CSS-like specificity score for selector/candidate matching."""
    score = 0
    for name, target in _selector_criteria(selector).items():
        if target is Any:
            continue
        score += _base_weight(name)
        score += _exact_bonus(name, target, candidate)
    return score


def score_requirement_specificity(requirement: Selector, candidate: Any = None) -> int:
    return score_selector_specificity(requirement, candidate)


def policy_tier(policy: Any) -> int:
    """Return policy sort tier (lower is preferred)."""
    from .provisioner import ProvisionPolicy

    if policy & ProvisionPolicy.STUB:
        return 9
    if policy & ProvisionPolicy.EXISTING:
        return 1
    if policy & ProvisionPolicy.UPDATE:
        return 2
    if policy & ProvisionPolicy.CLONE:
        return 3
    if policy & ProvisionPolicy.CREATE:
        return 4
    return 9


def offer_sort_key(offer: ProvisionOffer) -> tuple[int, int, int, int, int, int, int]:
    """Deterministic offer sort key.

    Order:
    1) policy tier
    2) scope distance
    3) distance from caller
    4) exact kind match (exact first)
    5) specificity (higher first)
    6) explicit offer priority
    7) creation sequence
    """
    return (
        policy_tier(offer.policy),
        offer.scope_distance,
        offer.distance_from_caller,
        0 if offer.exact_kind_match else 1,
        -offer.specificity,
        offer.priority,
        offer.seq,
    )


def annotate_offer_specificity(
    requirement: Selector,
    offer: ProvisionOffer,
) -> ProvisionOffer:
    candidate = offer.candidate
    specificity = score_requirement_specificity(requirement, candidate=candidate)
    exact_kind_match = _exact_kind_match(requirement, candidate)
    return offer.model_copy(
        update={
            "specificity": specificity,
            "exact_kind_match": exact_kind_match,
        }
    )


def summarize_offer(offer: ProvisionOffer) -> dict[str, Any]:
    return {
        "origin_id": str(offer.origin_id or "") or None,
        "policy": str(offer.policy),
        "scope_distance": offer.scope_distance,
        "build_plan": offer.build_plan,
        "target_ctx": offer.target_ctx,
        "distance_from_caller": offer.distance_from_caller,
        "exact_kind_match": offer.exact_kind_match,
        "specificity": offer.specificity,
        "priority": offer.priority,
    }
