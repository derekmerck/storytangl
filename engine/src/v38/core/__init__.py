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
# - specialized shapes
# - provenance
# - behaviors (Behavior(), Behavior.defer())
# - groups of behaviors (BehaviorRegistry.execute_all(), .chain_execute_al)
from .runtime_op import RuntimeOp
from .singleton import Singleton
from .record import Record, OrderedRegistry
from .graph import Graph, Subgraph, Edge, Node, HierarchicalNode
from .behavior import Priority, DispatchLayer, Behavior, CallReceipt, DeferredReceipt, BehaviorRegistry

# Requires:
# - behaviors
# Provides:
# - building
# - flexible dispatch
from .template import EntityTemplate, Snapshot, TemplateRegistry
# from .dispatch import HookedRegistry, HookedBuilder

# Systems Layers
# --------------
# VM -> graph traversal and provisioning rules, cursor controller, rollback/audit
# Service -> persistence, user/account management, and lifecycle endpoints

# Application Layers
# ------------------
# Story -> layers fabula concepts, episodic process, syuzhet on top of VM
# Discourse -> extensions for adapting story concepts to text-narrative engine
# Media -> extensions for adapting story concepts to media engine
# Mechanics -> extensions for modeling specialized story concepts

# Author Layers
# -------------
# Story.World -> content and rules for a particular story
