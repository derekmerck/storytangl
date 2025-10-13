"""
.. currentmodule:: tangl.core

Foundational abstractions for self-realizing narrative graphs. These classes
define the *vocabulary* (nouns) and *capabilities* (verbs) for higher-level
story resolution.

Conceptual layers
-----------------

1. :ref:`Identity and Collection<core-identity>`

   - :class:`Entity` provides a universal base for all managed objects.
   - :class:`Registry` organizes entities with robust search and chaining.
   - :class:`Singleton` shared entities that are discoverable by a unique label.

2. :ref:`Graph Topology<core-topology>`

   - :class:`Graph`, and :class:`GraphItems<GraphItem>` like :class:`Node`,
     :class:`Edge`, :class:`Subgraph` describe linked structures and hierarchy.

3. :ref:`Runtime Artifacts<core-artifacts>`

   - :class:`Record` captures immutable events, fragments, and notes.
   - :class:`StreamRegistry` sequences records with bookmarks and channels.
   - :class:`Snapshot` wraps a copy of an entity for record keeping and rematerialization.
   - :class:`Fragment<BaseFragment>` is a record type that encodes narrative/UI output.

4. :ref:`Dispatch<core-dispatch>`

   - :class:`Handler` wraps callable behaviors, returning a :class:`JobReceipt` record.
   - :class:`DispatchRegistry` executes handlers in ordered pipelines.

5. :ref:`Capabilities<core-capability>`

   - :class:`Domain` publishes a namespace (vars + handlers).
   - :class:`Scope` layers implicit (topological) and explicit (affiliated) domains around a node.

Design intent
-------------
`tangl.core` isolates minimal abstractions so that story engines can reason about
identity, relationships, and events *without presupposing narrative content*.
"""

# Base classes for all objects and collections
from .entity import Entity
from .registry import Registry

# Sequential data artifacts
from .record import Record, StreamRegistry, Snapshot, BaseFragment

# Globally reusable objects
from .singleton import Singleton

# Topology and membership related extensions
from .graph import GraphItem, Node, Edge, Subgraph, Graph

# Function dispatch, chaining, auditing
from .dispatch import JobReceipt, Handler, DispatchRegistry

# Opt-in and structurally scoped capability resolution
from .domain import Domain, Scope, global_domain, NS


__all__ = [
    # Identity & collections
    "Entity", "Registry",
    # Singleton
    "Singleton",
    # Graph topology
    "GraphItem", "Node", "Edge", "Subgraph", "Graph",
    # Records/streams
    "Record", "StreamRegistry", "Snapshot", "BaseFragment",
    # Dispatch
    "JobReceipt", "Handler", "DispatchRegistry",
    # Domains & scope
    "Domain", "Scope", "global_domain",
]
