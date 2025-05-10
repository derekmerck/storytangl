from collections import ChainMap
from typing import Mapping, Any, Iterable, TypeVar, Generic
import re

from .enums import Tier

_SANITISE_RE = re.compile(r"[^0-9a-zA-Z_]+")

def _sanitise(key: str) -> str:
    """
    Turn *key* into a valid Python identifier:

    * replace illegal chars with '_'      →  "little-dog"  →  "little_dog"
    * prefix '_' if it would start with # →  "123abc"      →  "_123abc"
    """
    key = _SANITISE_RE.sub("_", key)
    if key and key[0].isdigit():
        key = f"_{key}"
    return key or "_"

T = TypeVar("T")

class TieredMap(ChainMap[str, T], Generic[T]):
    """
    ChainMap whose *left-to-right layer order* is defined by Tier precedence.

    Each entry in `maps` is a tuple  (tier, mapping)  so we can:
      • iterate only layers ≤ a certain tier
      • insert a new layer for a tier without knowing its index
    """

    def __init__(self):
        # one empty dict per tier – index is now stable for life
        self._tier_index: list[Tier] = sorted(Tier, key=int)  # PRIORITY … DEFAULT
        super().__init__(*({} for _ in self._tier_index))
        # todo: consider, tier-indexed chainmap of arbitrary chainmaps?

    # --------------------------------------------------------------
    # public helpers
    # --------------------------------------------------------------
    def inject(self, tier: Tier, mapping: Mapping[str, Any]) -> None:
        """Merge *mapping* into the pre-existing layer for *tier*."""
        clean = {_sanitise(k): v for k, v in mapping.items()}
        idx = self._tier_index.index(tier)
        self.maps[idx].update(clean)  # mutate the fixed layer

    def iter_tiers(self, upto: Tier | None = None, *, reverse=False) -> Iterable[Mapping]:
        """Yield mappings left→right, optionally clipping to ≤ `upto` tier."""
        for tier, mapping in zip(self._tier_index, self.maps):
            if upto is None or (tier <= upto if not reverse else tier >= upto):
                yield mapping
