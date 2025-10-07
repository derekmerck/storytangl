# tangl/vm/planning/offer.py
"""
Offers and planning receipts.

A :class:`ProvisionOffer` is an *ephemeral* proposal to satisfy a
:class:`~tangl.vm.planning.requirement.Requirement`. Accepting an offer now
returns a provider (or ``None``) without mutating the requirement or graph.
Selectors are responsible for binding the provider, handling failures, and
constructing :class:`BuildReceipt` instances that document the outcome.

This module also defines receipts used to summarize planning outcomes.
"""
from __future__ import annotations
from typing import Optional, Literal, Self, Callable, Type
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

    Receipt summarizing how a selector handled a :class:`ProvisionOffer`.

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
    ProvisionOffer(requirement, provisioner, *, priority=50)

    Why
    ----
    Ephemeral proposal to satisfy a :class:`~tangl.vm.planning.requirement.Requirement`
    via a :class:`~tangl.vm.planning.provisioning.Provisioner`. Offers are compared
    and selected by priority; acceptance invokes the provisioner and returns a
    provider (or ``None``) for selectors to process.

    Key Features
    ------------
    * **Arbitration** – :attr:`priority` (lower wins); selectors inspect
      :attr:`Requirement.hard_requirement` directly when needed.
    * **Selectable** – publishes :attr:`selection_criteria` for inverse matching.
    * **Provisioning hook** – delegates to :class:`Provisioner.resolve` or a
      custom callback to compute a provider without side effects.
    * **Pure resolution** – :meth:`accept` simply returns a provider, leaving
      binding and receipt construction to selector logic.

    API
    ---
    - :attr:`requirement` – target requirement being satisfied.
    - :attr:`provisioner` – default provider logic (domain builders may override).
    - :attr:`priority` – integer priority; lower numbers run earlier.
    - :attr:`selection_criteria` – hints for higher-order selectors.
    - :meth:`accept(ctx)<accept>` – compute a provider and return it without
      mutating the requirement or graph.
    """
    requirement: Requirement
    provisioner: Provisioner

    # provisioner annotations for sorting
    operation: ProvisioningPolicy
    priority: int = 50       # lower runs earlier in selection

    selection_criteria: StringMap = Field(default_factory=dict)
    # for inverse filtering, predicates on acceptance

    # Will try `prov.resolve(req)` by default
    accept_func: Callable[..., Node | None] | None = None
    accept_func_takes_req: bool = False

    def describe(self) -> str:
        r = self.requirement
        return f"ProvisionOffer[{self.short_uid()}]: policy={r.policy.value}, id={r.identifier}, crit={r.criteria}"

    def accept(self, *, ctx: Context) -> Node | None:
        """Compute a provider for ``requirement`` without side effects."""

        if self.accept_func is None:
            return self.provisioner.resolve(self.requirement)
        if self.accept_func_takes_req:
            return self.accept_func(self.requirement)
        return self.accept_func()


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
