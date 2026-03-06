"""Legacy compatibility shim for the pre-cutover ``tangl.core`` surface."""

import os

import tangl.core as _core38

from tangl.core import *  # noqa: F401,F403
from tangl.core import (
    BaseFragment as _LegacyBaseFragment,
    BehaviorRegistry,
    Edge as _LegacyEdge,
    Entity as _LegacyEntity,
    Graph as _LegacyGraph,
    GraphItem as _LegacyGraphItem,
    HasContent,
    Node as _LegacyNode,
    Record as _LegacyRecord,
    Registry as _LegacyRegistry,
    Snapshot as _LegacySnapshot,
    StreamRegistry as _LegacyStreamRegistry,
    Subgraph as _LegacySubgraph,
)


_V38_VALUES = {"1", "true", "yes", "on", "v38", "new"}
_LEGACY_VALUES = {"0", "false", "no", "off", "legacy", "old"}


def _pick(symbol: str, legacy_value, v38_value, *, default: str = "v38"):
    raw_value = os.getenv(
        f"TANGL_SHIM_CORE_{symbol}",
        os.getenv("TANGL_SHIM_CORE_DEFAULT", default),
    )
    selected = str(raw_value).strip().lower()
    if selected in _LEGACY_VALUES:
        return legacy_value
    if selected in _V38_VALUES:
        return v38_value
    raise ValueError(
        f"Invalid shim value '{raw_value}' for TANGL_SHIM_CORE_{symbol}. "
        f"Use one of {sorted(_LEGACY_VALUES | _V38_VALUES)}."
    )


__all__ = getattr(
    _core38,
    "__all__",
    [name for name in dir(_core38) if not name.startswith("_")],
)

# Legacy compatibility aliases for import-surface blast-radius testing.
Entity = _pick("ENTITY", _LegacyEntity, _core38.Entity)
Registry = _pick("REGISTRY", _LegacyRegistry, _core38.Registry)
GraphItem = _pick("GRAPHITEM", _LegacyGraphItem, _core38.GraphItem)
Graph = _pick("GRAPH", _LegacyGraph, _core38.Graph)
Edge = _pick("EDGE", _LegacyEdge, _core38.Edge)
Subgraph = _pick("SUBGRAPH", _LegacySubgraph, _core38.Subgraph)
Record = _pick("RECORD", _LegacyRecord, _core38.Record)
Snapshot = _pick("SNAPSHOT", _LegacySnapshot, _core38.Snapshot)
Node = _pick("NODE", _LegacyNode, _core38.Node)
BaseFragment = _LegacyBaseFragment
ContentAddressable = HasContent
LayeredDispatch = BehaviorRegistry
StreamRegistry = _LegacyStreamRegistry

__all__ += [
    "BaseFragment",
    "ContentAddressable",
    "LayeredDispatch",
    "StreamRegistry",
]
