# tangl/vm/planning/offer.py
"""
Offers and planning receipts.

An :class:`Offer` is an *ephemeral* proposal to satisfy a
:class:`~tangl.vm.planning.requirement.Requirement`. Accepting an offer calls
its provisioner, which may mutate the graph. When event-sourcing is enabled,
those mutations are captured as events and later collapsed into a patch.

This module also defines receipts used to summarize planning outcomes.
"""
from __future__ import annotations
from typing import Optional, Literal, Self, Callable, Any, TYPE_CHECKING, Type
from uuid import UUID

from pydantic import Field

from tangl.type_hints import StringMap
from tangl.core import JobReceipt, Entity, Registry, Node
from tangl.core.entity import Selectable
from tangl.vm.context import Context
from .requirement import Requirement, ProvisioningPolicy
from .provisioning import Provisioner

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
    # fixed, no-init
    record_type: Literal['build_receipt'] = Field('build_receipt', alias='type')
    result_type: Type[UUID] = UUID

    # common job receipt fields
    blame_id: UUID = Field(alias='provisioner_id')
    caller_id: UUID = Field(alias='requirement_id')
    result: UUID | None = Field(None, alias='provider_id')

    # extended data
    operation: ProvisioningPolicy = ProvisioningPolicy.NOOP
    accepted: bool = True
    hard_req: Optional[bool] = None  # Only relevant if not accepted/accepted and failed?
    reason: Optional[str] = None     # Only relevant if not accepted/accepted and failed?

    @property
    def provider_id(self) -> UUID | None:
        # alias from canonical 'result' attrib
        return self.result

    def provider(self, registry: Registry) -> Node | None:
        # Records don't have graphs, but provide named convenience accessors against a registry
        return registry.get(self.provider_id) if self.provider_id else None


class ProvisionOffer(Selectable, Entity):
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
    requirement: Requirement
    provisioner: Provisioner

    # provisioner annotations for sorting
    operation: ProvisioningPolicy
    priority: int = 50       # lower runs earlier in selection

    selection_criteria: StringMap = Field(default_factory=dict)
    # for inverse filtering, predicates on acceptance

    # Will try `prov.resolve(req)` by default
    accept_func: Callable[..., Entity | None] = None
    accept_func_takes_req: bool = False

    def describe(self) -> str:
        r = self.requirement
        return f"Offer[{self.short_uid()}]: policy={r.policy.value}, id={r.identifier}, crit={r.criteria}"

    def accept(self, *, ctx: Context) -> BuildReceipt:
        """
        Accept via provisioner; watchers will record events if event_sourced.

        Provisioner.accept creates or finds, provider is linked (or marked unresolvable?) here.
        """
        if self.accept_func is None:
            provider = self.provisioner.resolve(self.requirement)
        elif self.accept_func_takes_req:
            provider = self.accept_func(self.requirement)
        else:
            provider = self.accept_func()

        if provider is None:
            # todo: This might actually be an error condition, we don't want to create
            #       an offer that doesn't return a provider, however, it looks like we
            #       currently use this to flag for unresolvable
            self.requirement.is_unresolvable = True
            return BuildReceipt(
                provisioner_id=self.provisioner.uid,
                requirement_id=self.requirement.uid,
                provider_id=None,
                operation=ProvisioningPolicy.NOOP,
                accepted=False,
                hard_req=self.requirement.hard,
                reason='unresolvable',
            )

        # todo: guarantee that provider satisfies req as advertised

        # Passed everything! Assign the provider to the req.
        self.requirement.provider = provider
        return BuildReceipt(
            provisioner_id=self.provisioner.uid,
            requirement_id=self.requirement.uid,
            result=provider.uid,
            operation=self.operation,
            accepted=True
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
    attached: int = 0
    updated: int = 0
    created: int = 0
    cloned: int = 0
    unresolved_hard_requirements: list[UUID] = Field(default_factory=list)

    @classmethod
    def summarize(cls, *builds: BuildReceipt) -> Self:

        attached = 0
        updated = 0
        created = 0
        cloned = 0

        unresolved_hard_requirements = []

        for b in builds:
            if not b.accepted and b.reason == 'unresolvable':
                unresolved_hard_requirements.append(str(b.caller_id))
                continue
            match b.operation:
                case ProvisioningPolicy.EXISTING: attached += 1
                case ProvisioningPolicy.UPDATE: updated += 1
                case ProvisioningPolicy.CREATE: created += 1
                case ProvisioningPolicy.CLONE: cloned += 1
        # (If we want to distinguish deps vs affordances, increment above accordingly.)

        pr = cls(
            # resolved_dependencies=0,
            # resolved_affordances=0,
            attached=attached,
            updated=updated,
            created=created,
            cloned=cloned,
            unresolved_hard_requirements=unresolved_hard_requirements,
            result="ok"
        )

        return pr
