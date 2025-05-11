from __future__ import annotations
from typing import TYPE_CHECKING
from dataclasses import dataclass, field
from uuid import UUID

from .. import Phase, Service
from ..type_hints import ProvisionKey
from ..capability import Capability
from ..entity import Entity
from ..type_hints import StringMap

if TYPE_CHECKING:
   from ..graph import Node, Graph

@dataclass(kw_only=True)
class ProviderCap(Capability, Entity):
    """
    Registers a *provider* for some resource (shop, actor, sound, …).

    *provides* is a set of keys this provider can satisfy.
    """
    service: Service = Service.PROVIDER
    phase: Phase = Phase.RESOLVE
    provides: set[ProvisionKey] = field(default_factory=set)

    # In most cases apply() just returns the provider-node reference
    def apply(self, node: 'Node', driver, graph: 'Graph', ctx: StringMap) -> 'Node':
        return node

