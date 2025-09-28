# Base classes for all objects and collections
from .entity import Entity
from .registry import Registry

# Sequential data extensions
from .record import Record, StreamRegistry

# Globally reusable objects
from .singleton import Singleton

# Topology and membership related extensions
from .graph import GraphItem, Node, Edge, Subgraph, Graph

# Function dispatch, chaining, auditing
from .dispatch import JobReceipt, Handler, DispatchRegistry

# Opt-in and structurally scoped capability resolution
from .domain import Domain, Scope, global_domain

# Pre-image content output
from .fragment import ContentFragment, ControlFragment, GroupFragment, InfoFragment, PresentationHints
