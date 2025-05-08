from collections import defaultdict

from ..enums import Phase, Tier
from ..capability import Capability

class CapabilityCache:
    def __init__(self):
        self._store: dict[tuple[Phase, Tier], list[Capability]] = \
            defaultdict(list)

    def register(self, cap: Capability):
        bucket = self._store[(cap.phase, cap.tier)]
        bucket.append(cap)
        bucket.sort(key=lambda c: -c.priority)      # highest first

    def iter_phase(self, phase: Phase, tier: Tier):
        return iter(self._store.get((phase, tier), ()))