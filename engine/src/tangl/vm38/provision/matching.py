from __future__ import annotations

from typing import Any

from tangl.core38 import Selector


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

    if policy & ProvisionPolicy.FORCE:
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


def offer_sort_key(offer: Any) -> tuple[int, int, int, int, int, int, int]:
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
    scope = getattr(offer, "scope_distance", 0)
    if not isinstance(scope, int):
        scope = 0
    distance = getattr(offer, "distance_from_caller", 999)
    if not isinstance(distance, int):
        distance = 999
    specificity = getattr(offer, "specificity", 0)
    if not isinstance(specificity, int):
        specificity = 0
    exact_kind_match = bool(getattr(offer, "exact_kind_match", False))
    priority = getattr(offer, "priority", 0)
    if not isinstance(priority, int):
        priority = 0
    seq = getattr(offer, "seq", 0)
    if not isinstance(seq, int):
        seq = 0

    return (
        policy_tier(offer.policy),
        scope,
        distance,
        0 if exact_kind_match else 1,
        -specificity,
        priority,
        seq,
    )


def annotate_offer_specificity(requirement: Selector, offer: Any) -> Any:
    candidate = getattr(offer, "candidate", None)
    specificity = score_requirement_specificity(requirement, candidate=candidate)
    exact_kind_match = _exact_kind_match(requirement, candidate)
    if hasattr(offer, "model_copy"):
        try:
            return offer.model_copy(
                update={
                    "specificity": specificity,
                    "exact_kind_match": exact_kind_match,
                }
            )
        except Exception:
            pass
    if hasattr(offer, "specificity"):
        try:
            offer.specificity = specificity
            if hasattr(offer, "exact_kind_match"):
                offer.exact_kind_match = exact_kind_match
            return offer
        except Exception:
            pass
    return offer


def summarize_offer(offer: Any) -> dict[str, Any]:
    return {
        "origin_id": str(getattr(offer, "origin_id", "")) or None,
        "policy": str(getattr(offer, "policy", None)),
        "scope_distance": getattr(offer, "scope_distance", None),
        "build_plan": getattr(offer, "build_plan", None),
        "target_ctx": getattr(offer, "target_ctx", None),
        "distance_from_caller": getattr(offer, "distance_from_caller", None),
        "exact_kind_match": getattr(offer, "exact_kind_match", None),
        "specificity": getattr(offer, "specificity", None),
        "priority": getattr(offer, "priority", None),
    }
