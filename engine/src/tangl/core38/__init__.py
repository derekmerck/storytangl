# tangl/core/bases.py
# language=markdown
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
from .singleton import Singleton
from .record import Record, OrderedRegistry
from .graph import GraphItem, Graph, Subgraph, Edge, Node, HierarchicalNode
from .behavior import Priority, DispatchLayer, Behavior, CallReceipt, BehaviorRegistry, AggregationMode

# Requires:
# - behaviors
# Provides:
# - building
# - dispatch hooks
from .template import EntityTemplate, Snapshot, TemplateRegistry  # Recipe builder
from .token import Token  # Delegated reference builder
from .dispatch import on_init, on_create, on_add_item, on_get_item, on_remove_item, on_link, on_unlink

from .ctx import resolve_ctx
