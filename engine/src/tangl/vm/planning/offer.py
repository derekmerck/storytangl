# tangl/vm/planning/offer.py
"""
Offers and planning receipts.

An :class:`Offer` is an *ephemeral* proposal to satisfy a
:class:`~tangl.vm.planning.requirement.Requirement`. Accepting an offer calls
its provisioner, which may mutate the graph. When event-sourcing is enabled,
those mutations are captured as events and later collapsed into a patch.

This module also defines receipts used to summarize planning outcomes.
"""
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
    """
    BuildReceipt(requirement: Requirement, op_kind: str)

    Receipt returned by :meth:`Offer.accept`.

    Why
    ----
    Captures the outcome of attempting to satisfy a single requirement: which
    provider was bound (if any), what operation was implied, and whether the
    offer was accepted.

    Key Features
    ------------
    * **Typed record** – ``record_type='build_receipt'`` for stream filtering.
    * **Provider binding** – references both requirement and chosen provider ids.
    * **Operation summary** – one of ``attach/create/update/clone/noop``.
    * **Diagnostics** – ``accepted`` flag and optional ``reason`` (e.g. ``'unresolvable'``).

    API
    ---
    - :attr:`requirement_id` – requirement satisfied (or attempted).
    - :attr:`provider_id` – chosen/created/updated/cloned node id.
    - :attr:`operation` – operation kind string.
    - :attr:`accepted` – ``False`` when no provider could be produced.
    - :attr:`reason` – optional diagnostic text.
    """
    record_type: Literal['build_receipt'] = Field('build_receipt', alias='type')
    requirement_id: UUID | None = None
    provider_id: UUID | None = None
    operation: Literal['attach', 'create', 'update', 'clone', 'noop'] = 'noop'
    accepted: bool = True
    reason: Optional[str] = None

class Offer(Entity, Selectable):
    """
    Offer(requirement, provisioner, *, priority=50, hard=True)

    Why
    ----
    Ephemeral proposal to satisfy a :class:`~tangl.vm.planning.requirement.Requirement`
    via a :class:`~tangl.vm.planning.provisioning.Provisioner`. Offers are compared
    and selected by priority; acceptance invokes the provisioner and yields a
    :class:`BuildReceipt`.

    Key Features
    ------------
    * **Arbitration** – :attr:`priority` (lower wins) and :attr:`hard` semantics for selectors.
    * **Selectable** – publishes :attr:`selection_criteria` for inverse matching.
    * **Provisioning hook** – delegates to :class:`Provisioner.resolve` which may mutate the graph.
    * **Auditable** – :meth:`accept` returns a :class:`BuildReceipt` with provider/operation.

    API
    ---
    - :attr:`requirement` – target requirement being satisfied.
    - :attr:`provisioner` – default provider logic (domain builders may override).
    - :attr:`priority` – integer priority; lower numbers run earlier.
    - :attr:`hard` – mirrors ``requirement.hard_requirement``.
    - :attr:`selection_criteria` – hints for higher-order selectors.
    - :meth:`accept(ctx)<accept>` – apply provisioner, bind provider, and return a receipt.
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
    """
    PlanningReceipt()

    Final consolidated outcome of :data:`~tangl.vm.frame.ResolutionPhase.PLANNING`.

    Why
    ----
    Aggregates a set of :class:`BuildReceipt` results to summarize what planning
    accomplished and which hard requirements remain unresolved.

    Key Features
    ------------
    * **Counts by operation** – created/updated/cloned/attached tallies.
    * **Unresolved tracking** – list of hard requirement ids still unsatisfied.
    * **Typed record** – ``record_type='planning_receipt'`` for stream filtering.

    API
    ---
    - :meth:`summarize(*builds)<summarize>` – collapse multiple build receipts into one summary.
    - :attr:`created`, :attr:`updated`, :attr:`cloned`, :attr:`attached` – operation counters.
    - :attr:`unresolved_hard_requirements` – list of requirement ids.
    """
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
