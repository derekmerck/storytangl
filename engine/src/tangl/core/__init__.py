# tangl/core/__init__.py
# language=markdown
from __future__ import annotations

import importlib
import sys

"""
tangl.core
==========

Core defines shared vocabulary and foundational data structures and algorithms.

Portability
-----------

Core types should be easy to reason about and implementable in any language with:
- Algebraic data types or class inheritance
- First-class functions
- Associative collections (dict/map)
- Ordered collections (list/array)

Avoid Python-specific magic where possible. Document where unavoidable.

File Organization
-----------------

```
tangl/core/
├── __init__.py           # Public API exports
├── bases.py              # HasIdentity, uid/label/tags, Unstructurable, un/structure(),
│                         #    HasContent, HasOrder, sort_key(), HasState
│
│   # Discovery
├── selector.py           # Selector, match()
├── registry.py           # Registry, RegistryAware, EntityGroup, find_all(), chain_find_all()
│
│   # Lifecycle
├── record.py             # Record, OrderedRegistry, get_slice()
├── singleton.py          # Singleton, InstanceInheritance
│
│   # Relationships
├── graph.py              # GraphItem, Graph, Subgraph, Node, Edge
│
│   # Creation
├── token.py              # Delegate to singleton
├── template.py           # Semi-structured data, TemplateRegistry
│
│   # Doing things
├── runtime_op.py         # RuntimeOp, Query, Predicate, Effect
├── behavior.py           # Behavior, CallReceipt, Priority, DispatchLayer, AggregationMode
└── dispatch.py           # Hooks for create(), new(), add(), get(), remove()
```
"""
# Provides:
# - identity
# - state
# - un/structure
from .entity import Entity

# Requires:
# - identity
# - un/structure
# Provides:
# - selection (Selector.from_kind(), .with_criteria(**_), .matches(entity))
# - discovery (Reg.find_all(selector), .chain_find_all(*reg, selector)
# - grouping/membership
from .selector import Selector
from .registry import Registry, RegistryAware, EntityGroup, HierarchicalGroup

# Requires:
# - selection
# - groups
# Provides:
# - specialized shapes (singleton, record, graph)
# - provenance (record)
# - behaviors (Behavior(), Behavior.defer())
# - groups of behaviors (BehaviorRegistry.execute_all(), .chain_execute_al)
from .runtime_op import RuntimeOp
from .singleton import InheritingSingleton, Singleton
from .record import Record, OrderedRegistry
from .base_fragment import BaseFragment
from .graph import GraphItem, Graph, Subgraph, Edge, Node, HierarchicalNode
from .behavior import Priority, DispatchLayer, Behavior, CallReceipt, BehaviorRegistry, AggregationMode
from .namespace import HasNamespace, contribute_ns
from .bases import HasContent

# Requires:
# - behaviors
# Provides:
# - building
# - dispatch hooks
from .template import EntityTemplate, Snapshot, TemplateRegistry  # Recipe builder
from .token import Token, TokenCatalog, TokenFactory  # Delegated reference builder
from .dispatch import on_init, on_create, on_add_item, on_get_item, on_remove_item, on_link, on_unlink

from .ctx import CoreCtx, Ctx, DispatchCtx, get_ctx, resolve_ctx, using_ctx


# Legacy-compatible aliases retained during namespace cutover.
# ContentAddressable: used by tangl.media.media_resource.media_resource_inv_tag
# LayeredDispatch: used by tangl.ir.dispatch
ContentAddressable = HasContent
LayeredDispatch = BehaviorRegistry


def _alias_legacy_module(alias: str, target: str) -> None:
    """Map legacy deep-import module paths to canonical flat modules."""
    module = importlib.import_module(target)
    sys.modules.setdefault(alias, module)
    parent_name, _, child_name = alias.rpartition(".")
    parent = sys.modules.get(parent_name)
    if parent is not None and not hasattr(parent, child_name):
        setattr(parent, child_name, module)

# Map legacy deep-import module paths so pickled objects referencing old paths
# can still be deserialized. Do not remove without a persistence migration.
for _alias, _target in (
    # Legacy graph package paths.
    ("tangl.core.graph.graph", "tangl.core.graph"),
    ("tangl.core.graph.node", "tangl.core.graph"),
    ("tangl.core.graph.edge", "tangl.core.graph"),
    ("tangl.core.graph.subgraph", "tangl.core.graph"),
    ("tangl.core.graph.token", "tangl.core.token"),
    # Legacy record package paths.
    ("tangl.core.record.record", "tangl.core.record"),
    ("tangl.core.record.stream_registry", "tangl.core.record"),
    ("tangl.core.record.snapshot", "tangl.core.template"),
    ("tangl.core.record.base_fragment", "tangl.core.base_fragment"),
):
    _alias_legacy_module(_alias, _target)
