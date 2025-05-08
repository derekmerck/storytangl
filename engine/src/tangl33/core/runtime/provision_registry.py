from collections import defaultdict
from typing import Iterable
from uuid import UUID

from pydantic import Field

from ..type_hints import ProvisionKey
from ..registry import Registry
from ..provision import ProvisionCap
from ..enums import Tier


class ProvisionRegistry(Registry[ProvisionCap]):
    """
    Fast lookup of ProvisionCaps by key + tier.
    Each tier gets its own sub-index so resolver can walk NODE→…→GLOBAL.
    """
    tier_index: dict[int, dict[ProvisionKey, set[UUID]]] = \
        Field(default_factory=lambda: defaultdict(lambda: defaultdict(set)), repr=False)

    def add(self, cap: ProvisionCap):
        super().add(cap)
        for key in cap.provides:
            self.tier_index[cap.tier.value][key].add(cap.uid)

    def providers(self, key: ProvisionKey, tier: Tier) -> Iterable[ProvisionCap]:
        ids = self.tier_index[tier].get(key, ())
        return (self.data[i] for i in ids)
