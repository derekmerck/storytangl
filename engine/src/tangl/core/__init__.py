# Base classes for all objects and collections
from .entity import Entity
from .registry import Registry
from .singleton import Singleton

# Topology and membership related extensions
from .graph import GraphItem, Node, Edge, Subgraph, Graph

# Function dispatch and chaining
from .dispatch import JobReceipt, Handler, HandlerRegistry

# Opt-in and structural namespace, handler, and provider resolution
from .domain import Domain, Scope, global_domain
