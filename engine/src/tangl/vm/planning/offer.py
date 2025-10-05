# tangl/vm/planning/offer.py
from typing import Optional, Literal, Self
from uuid import UUID

from pydantic import Field

from tangl.type_hints import StringMap
from tangl.core import JobReceipt, Entity
from tangl.core.entity import Selectable
from tangl.vm.context import Context
from .open_edge import Requirement
from .provisioning import Provisioner, ProvisioningPolicy

class BuildReceipt(JobReceipt):
    record_type: Literal['build_receipt'] = Field('build_receipt', alias='type')
    requirement_id: UUID | None = None
    provider_id: UUID | None = None
    operation: Literal['attach', 'create', 'update', 'clone', 'noop'] = 'noop'
    accepted: bool = True
    reason: Optional[str] = None

class Offer(Entity, Selectable):
    """
    An Offer proposes a concrete way to satisfy a Requirement (e.g., attach an
    existing node, create/clone/update then attach). Accepting the offer performs
    the mutation (captured by watchers if event-sourced) and returns a BuildReceipt.
    """
    requirement: Requirement = Field(...)
    provisioner: Provisioner = Field(...)
    priority: int = 50       # lower runs earlier in selection
    hard: bool = True        # mirrors requirement.hard_requirement
    selection_criteria: StringMap = Field(default_factory=dict)  # for inverse filtering

    def describe(self) -> str:
        r = self.requirement
        return f"Offer[{self.short_uid()}]: policy={r.policy.value}, id={r.identifier}, crit={r.criteria}"

    def accept(self, *, ctx: Context) -> BuildReceipt:
        """
        Apply via provisioner; watchers will record events if event_sourced.
        """
        before = self.requirement.provider_id
        node = self.provisioner.resolve()  # may mutate graph (watched)
        if node is None:
            return BuildReceipt(
                result=None,
                requirement_id=self.requirement.uid,
                provider_id=None,
                operation='noop',
                accepted=False,
                reason='unresolvable',
            )
        op = 'attach'
        # Rough heuristic: report create/update/clone if template/policy indicate it
        match self.requirement.policy:
            case ProvisioningPolicy.CREATE: op = 'create'
            case ProvisioningPolicy.UPDATE: op = 'update'
            case ProvisioningPolicy.CLONE:  op = 'clone'
            case _:                         op = 'attach' if before else 'attach'
        return BuildReceipt(
            result=node.uid,
            requirement_id=self.requirement.uid,
            provider_id=node.uid,
            operation=op,
            accepted=True,
        )


class PlanningReceipt(JobReceipt):
    record_type: Literal['planning_receipt'] = Field('planning_receipt', alias='type')
    resolved_dependencies: int = 0
    resolved_affordances: int = 0
    created: int = 0
    updated: int = 0
    cloned: int = 0
    attached: int = 0
    unresolved_hard_requirements: list[str] = Field(default_factory=list)

    @classmethod
    def summarize(cls, *builds: BuildReceipt) -> Self:

        created = 0
        updated = 0
        cloned = 0
        attached = 0

        unresolved_hard_requirements = []

        for b in builds:
            if not b.accepted and b.reason == 'unresolvable':
                unresolved_hard_requirements.append(str(b.requirement_id))
                continue
            match b.operation:
                case 'create': created += 1
                case 'update': updated += 1
                case 'clone':  cloned  += 1
                case 'attach': attached += 1
        # (If we want to distinguish deps vs affordances, increment above accordingly.)

        pr = cls(
            # resolved_dependencies=0,
            # resolved_affordances=0,
            created=created, updated=updated, cloned=cloned, attached=attached,
            unresolved_hard_requirements=unresolved_hard_requirements,
            result="ok"
        )

        return pr
