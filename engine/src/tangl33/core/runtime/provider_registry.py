from collections import defaultdict
from typing import Iterable
from uuid import UUID
from dataclasses import dataclass, field

from ..type_hints import ProvisionKey
from ..registry import Registry
from ..provision import ResourceProvider
from ..enums import Tier

@dataclass(kw_only=True)
class ProviderRegistry(Registry[ResourceProvider]):
    """
    Fast lookup of ProvisionCaps by key + tier.
    Each tier gets its own sub-index so resolver can walk NODE→…→GLOBAL.
    """
    tier_index: dict[int, dict[ProvisionKey, set[UUID]]] = \
        field(default_factory=lambda: defaultdict(lambda: defaultdict(set)), repr=False)

    def add(self, cap: ResourceProvider) -> None:
        super().add(cap)
        for key in cap.provides:
            self.tier_index[cap.tier.value][key].add(cap.uid)

    def providers(self, key: ProvisionKey, tier: Tier) -> Iterable[ResourceProvider]:
        ids = self.tier_index[tier].get(key, ())
        return (self.data[i] for i in ids)
