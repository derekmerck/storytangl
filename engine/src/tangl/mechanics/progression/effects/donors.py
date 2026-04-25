from __future__ import annotations

from typing import Iterable, Protocol, runtime_checkable

from .situational import SituationalEffect


@runtime_checkable
class EffectDonor(Protocol):
    """Protocol for things that donate situational effects."""

    def get_situational_effects(self) -> Iterable[SituationalEffect]: ...


@runtime_checkable
class TagDonor(Protocol):
    """Protocol for things that donate scenario tags."""

    def get_context_tags(self) -> Iterable[str]: ...


def gather_donor_effects(donors: Iterable[EffectDonor]) -> list[SituationalEffect]:
    """Collect situational effects from explicit donors."""
    effects: list[SituationalEffect] = []
    for donor in donors:
        effects.extend(donor.get_situational_effects())
    return effects


def gather_donor_tags(donors: Iterable[TagDonor]) -> set[str]:
    """Collect scenario tags from explicit donors."""
    tags: set[str] = set()
    for donor in donors:
        tags.update(donor.get_context_tags())
    return tags
