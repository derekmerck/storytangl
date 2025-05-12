from collections import ChainMap
from typing import Mapping, Any, Iterable, TypeVar, Generic, Self

from tangl33.utils.sanitize_keys import _sanitise
from .type_hints import StringMap
from .enums import Tier

T = TypeVar("T")

class TierView(ChainMap[str | tuple[Tier | str, str], T], Generic[T]):
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

    # --------------------------------------------------------------
    # public helpers
    # --------------------------------------------------------------
    @classmethod
    def compose(cls, service, **scope_layers: StringMap) -> Self:
        inst = cls()
        for tier, layer in scope_layers.items():
            inst._set_layer(tier, layer)
            # inst.inject(tier, layer)
        return inst

    def inject(self, tier: Tier, mapping: Mapping[str, Any]) -> None:
        """Merge *mapping* into the pre-existing layer for *tier*."""
        clean = {_sanitise(k): v for k, v in mapping.items()}
        self._get_layer(tier).update(clean)  # mutate the fixed layer

    def iter_tiers(self, upto: Tier | None = None, *, reverse=False) -> Iterable[Mapping]:
        """Yield mappings left→right, optionally clipping to ≤ `upto` tier."""
        for tier, mapping in zip(self._tier_index, self.maps):
            if upto is None or (tier <= upto if not reverse else tier >= upto):
                yield mapping

    def _set_layer(self, tier: Tier | str, data) -> None:
        if not isinstance(tier, Tier):
            tier = Tier(tier)
        idx = self._tier_index.index(tier)
        self.maps[idx] = data

    def _get_layer(self, tier: Tier | str):
        if not isinstance(tier, Tier):
            tier = Tier(tier)
        try:
            idx = self._tier_index.index(tier)
            return self.maps[idx]
        except ValueError:
            return None

    def __getitem__(self, key) -> Any:
        if isinstance(key, tuple):
            tier, key = key
            return self._get_layer(tier).get(key)
        return super().__getitem__(key)

    def __setitem__(self, key, value) -> Any:
        if isinstance(key, tuple):
            tier, key = key
            self._get_layer(tier)[key] = value
        super().__setitem__(key, value)
