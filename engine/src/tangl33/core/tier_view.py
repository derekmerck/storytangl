from collections import ChainMap
from typing import Mapping, Any, Iterable, TypeVar, Generic, Self

from tangl33.utils.sanitize_keys import _sanitise
from .type_hints import StringMap
from .enums import CoreScope

T = TypeVar("T")

class TierView(ChainMap[str | tuple[CoreScope | str, str], T], Generic[T]):
    """
    ChainMap whose *left-to-right layer order* is defined by CoreScope precedence.

    Each entry in `maps` is a tuple  (CoreScope, mapping)  so we can:
      • iterate only layers ≤ a certain CoreScope
      • insert a new layer for a CoreScope without knowing its index
    """

    def __init__(self):
        # one empty dict per CoreScope – index is now stable for life
        self._tier_index: list[CoreScope] = sorted(CoreScope, key=int)  # PRIORITY … DEFAULT
        super().__init__(*({} for _ in self._tier_index))

    # --------------------------------------------------------------
    # public helpers
    # --------------------------------------------------------------
    @classmethod
    def compose(cls, service, **scope_layers: StringMap) -> Self:
        inst = cls()
        for scope, layer in scope_layers.items():
            inst._set_layer(scope, layer)
            # inst.inject(CoreScope, layer)
        return inst

    def inject(self, scope: CoreScope, mapping: Mapping[str, Any]) -> None:
        """Merge *mapping* into the pre-existing layer for *CoreScope*."""
        clean = {_sanitise(k): v for k, v in mapping.items()}
        self._get_layer(scope).update(clean)  # mutate the fixed layer

    def iter_tiers(self, upto: CoreScope | None = None, *, reverse=False) -> Iterable[Mapping]:
        """Yield mappings left→right, optionally clipping to ≤ `upto` CoreScope."""
        for scope, mapping in zip(self._tier_index, self.maps):
            if upto is None or (scope <= upto if not reverse else scope >= upto):
                yield mapping

    def _set_layer(self, scope: CoreScope | str, data) -> None:
        if not isinstance(scope, CoreScope):
            scope = CoreScope(scope)
        idx = self._tier_index.index(scope)
        self.maps[idx] = data

    def _get_layer(self, scope: CoreScope | str):
        if not isinstance(scope, CoreScope):
            scope = CoreScope(scope)
        try:
            idx = self._tier_index.index(scope)
            return self.maps[idx]
        except ValueError:
            return None

    def __getitem__(self, key) -> Any:
        if isinstance(key, tuple):
            scope, key = key
            return self._get_layer(scope).get(key)
        return super().__getitem__(key)

    def __setitem__(self, key, value) -> Any:
        if isinstance(key, tuple):
            scope, key = key
            self._get_layer(scope)[key] = value
        super().__setitem__(key, value)
