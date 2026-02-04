# Provides:
# - identity
# - state
# - un/structure
from .entity import Entity

# Requires:
# - identity
# - un/structure
# Provides:
# - selection (Selector.from_ctx(ctx), .with_attribs(**_), .matches(entity))
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
# - behaviors (Behavior.execute_for(ctx))
# - groups of behaviors (Dispatch.execute_all_for(ctx), .chain_execute_all_for(ctx))
from .runtime_op import RuntimeOp
from .singleton import Singleton
# from .record import Record, OrderedRegistry
# from .graph import Graph, Subgraph, Edge, Node, HierarchicalNode
# from .behavior import Priority, DispatchLayer, Behavior, CallReceipt, BehaviorRegistry

# Requires:
# - behaviors
# Provides:
# - building
# - traversal
# - flexible dispatch
# from .builder import Builder, Factory, BuildOffer  # specialized behaviors
# from .dispatch import HookedRegistry, HookedBuilder
# from .traversable import TraversableGraph, TraversableSubgraph, TraversableNode, Cursor; handle push/pop context, namespaces

# Systems Layers
# --------------
# VM -> layers graph navigation and provisioning rules, transition/cursor controller
# Service -> persistence, graph management, and lifecycle endpoints

# Application Layers
# ------------------
# Story -> layers fabula concepts and episodic process on top of VM
# Discourse -> extensions for adapting story concepts to syuzhet engine
# Media -> extensions for adapting story concepts to media engine

# Author Layers
# -------------
# Story-Worlds -> content and rules for a particular story
