from enum import auto, IntEnum
from uuid import UUID
from typing import Iterator, Optional

from pydantic import Field

from tangl.core39 import Node, Record, BehaviorRegistry, ExecContext, Priority
from .evolution import TraversableNode, TraversableEdge
from .requirement import Requirement, Dependency, Affordance

##############################
# PLANNING
##############################

class ProvisioningOffer(Record):
    caller: ...
    policy: ...
    complexity: ...
    accept_cb: ...

class PlanningPolicy(IntEnum):
    EXISTING = auto()  # push or nearby
    MODIFY = auto()    # find close + update
    CREATE = auto()    # template or token
    CLONE = auto()     # find close + clone w update
    FORCE = auto()     # force a minimal candidate into existence (DIRTY)

def on_get_provision_offers(priority=Priority.EARLY): ...
def on_accept_provision_offers(priority=Priority.EARLY): ...

class PlanningContext(ExecContext):
    caller: TraversableNode = None
    authorities: list[BehaviorRegistry] = Field(default_factory=list)
    affordances: list[Affordance] = Field(default_factory=list)
    results: dict[UUID, ProvisioningOffer] = Field(default_factory=list)

    @on_get_provision_offers(priority=Priority.EARLY)
    def _get_affordances(self, *_, **__) -> Iterator[ProvisioningOffer]:
        for affordance in self.affordances:
            if affordance.satisfied_by(self.caller):
                yield ProvisioningOffer(
                    caller=self.caller,
                    policy=PlanningPolicy.EXISTING,
                    accept_cb=affordance.attach)

    @on_get_provision_offers(priority=Priority.NORMAL)
    def _find_nearby_providers(self) -> Iterator[ProvisioningOffer]:
        for ancestor in self.caller.ancestors():  # what kind of ancestors? any kind?
            for edge in ancestor.edges_out():
                if edge.successor:
                    ...

    def get_offers(self, req: Requirement) -> list[ProvisioningOffer]:
        return BehaviorRegistry.call_all("get_provision_offers", self.caller, req)

    def accept_offer(self, *offers: ProvisioningOffer) -> Node:
        ...

    def resolve_dep(self, dep: Dependency) -> bool:
        offers = self.get_offers(dep)
        provider = self.accept_offer(*offers)
        if provider:
            dep.attach(provider)
            return True
        return False

    def plan_frontier(self, node: TraversableNode):
        for dep in node.edges_out(kind=Dependency, satisified=False):
            self.resolve_dep(dep)


