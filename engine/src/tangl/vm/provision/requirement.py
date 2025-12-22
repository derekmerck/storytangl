# tangl/vm/requirement.py
"""
Requirements and provisioning policy.

A :class:`Requirement` is a graph item that expresses *what must be linked*
at the frontier and *how* to obtain it (via :class:`ProvisioningPolicy`).
Requirements are carried by :class:`~tangl.vm.planning.open_edge.Dependency`
and :class:`~tangl.vm.planning.open_edge.Affordance` edges.
"""
from enum import Flag, auto
from typing import Optional, Generic, TypeVar
from uuid import UUID
from copy import deepcopy

from pydantic import Field, PrivateAttr, model_validator, field_validator

from tangl.type_hints import StringMap, UnstructuredData, Identifier
from tangl.core.graph import GraphItem, Node, Graph
from tangl.core.factory import Template

NodeT = TypeVar('NodeT', bound=Node)

class ProvisioningPolicy(Flag):
    """
    Provisioning strategies for satisfying a requirement.

    - **EXISTING**: Find a pre-existing provider by identifier and/or match criteria.
    - **UPDATE**: Find a provider and update it using a template (in-place edit).
    - **CREATE**: Create a new provider from a template.
    - **CLONE**: Find a reference provider, make a copy, then evolve via template.
    - **ANY**: Any of Existing, Update, Create
    - **NOOP**: No-op operation (Unsatisfiable and not allowed on Requirement)

    Notes
    -----
    Validation ensures the presence of ``identifier/criteria`` for EXISTING-family
    policies and a ``template`` for CREATE/UPDATE/CLONE.
    """
    EXISTING = auto()    # find by identifier and/or criteria match
    UPDATE = auto()      # find and update from template
    CREATE = auto()      # create from template
    CLONE = auto()       # find and evolve from template

    NOOP = auto()        # not possible

    ANY = EXISTING | UPDATE | CREATE   # No reason to clone unless explicitly indicated

class Requirement(GraphItem, Generic[NodeT]):
    """
    Requirement(identifier | criteria | template, policy: ProvisioningPolicy = EXISTING, *, hard_requirement: bool = True)

    GraphItem placeholder describing a needed provider at the resolution frontier.

    Why
    ----
    Encodes *what must be linked* (by identifier/criteria) and *how to obtain it*
    (via :class:`ProvisioningPolicy`). Requirements are carried on open edges
    (e.g., :class:`Dependency`, :class:`Affordance`) and are satisfied by
    binding a provider node.

    In protocol / constraint-satisfaction terms, a Requirement is the VM's
    **Constraint** object:

    * Its **selector surface** is the combination of :attr:`identifier` and
      :attr:`criteria`, exposed via :meth:`get_selection_criteria` and
      :meth:`satisfied_by`. This describes *what* would be acceptable.
    * Its **provisioning contract** is the combination of :attr:`policy`,
      :attr:`template`, :attr:`reference_id`, and :attr:`hard_requirement`.
      This describes *how* the engine may satisfy the selector once a match
      is found.

    Key Features
    ------------
    * **Multiple acquisition modes** – find, update, create, or clone via :class:`ProvisioningPolicy`.
    * **Flexible targeting** – match by :attr:`identifier` or :attr:`criteria` (or both).
    * **Templated provisioning** – :attr:`template` provides fields for UPDATE/CREATE/CLONE.
    * **Explicit cloning** – :attr:`reference_id` binds CLONE operations to a specific source node.
    * **Binding** – :attr:`provider` resolves to a live :class:`~tangl.core.graph.Node`; auto-added to the graph if needed.
    * **Hard/soft semantics** – :attr:`hard_requirement` gates whether unresolved requirements block progress.
    * **Scoped inheritance** – :attr:`satisfied_at_scope_id` records where a binding occurred for downstream reuse.

    API
    ---
    - :attr:`identifier` – alias/uuid/label for a specific provider.
    - :attr:`criteria` – dict used with :meth:`~tangl.core.registry.Registry.find_all` to discover candidates.
    - :attr:`template` – unstructured data used to create/update/clone a provider.
    - :attr:`policy` – :class:`ProvisioningPolicy` that validates required fields.
    - :attr:`asset_ref` – direct-addressed asset token to satisfy the requirement.
    - :attr:`provider` – get/set bound provider node (backed by :attr:`provider_id`).
    - :attr:`reference_id` – explicit source node for :attr:`ProvisioningPolicy.CLONE`.
    - :attr:`hard_requirement` – if ``True``, unresolved requirements are reported at planning end.
    - :attr:`is_unresolvable` – sticky flag when prior attempts failed.
    - :attr:`satisfied_at_scope_id` – scope node where the requirement was satisfied.
    - :attr:`satisfied` – ``True`` if a provider is bound or the requirement is soft.

    Notes
    -----
    Validation rules:

    - ``EXISTING/UPDATE`` require :attr:`identifier` **or** :attr:`criteria`.
    - ``CLONE`` requires :attr:`reference_id` and :attr:`template`.
    - ``CREATE/UPDATE`` require :attr:`template`.

    Protocol view:

    - **Constraint:** each Requirement instance attached to an open edge.
    - **Selector:** the subset of fields used by
      :meth:`get_selection_criteria` / :meth:`satisfied_by`.
    - **Contract:** the provisioning fields (:attr:`policy`,
      :attr:`template`, :attr:`reference_id`, :attr:`hard_requirement`)
      that guide how offers and plans are constructed.

    A future refinement (not yet implemented) is to formalize this selector
    surface as a small :pep:`544` ``Protocol`` (e.g. ``Selector`` with
    ``get_selection_criteria`` / ``satisfied_by``), so other constraint-like
    objects can participate in the same matching pipeline without inheriting
    from :class:`Requirement`.
    """
    provider_id: Optional[UUID] = None

    identifier: Optional[Identifier] = None  # aka 'ref' or 'alias'
    asset_ref: Optional[Identifier] = None
    """Direct asset token reference (bypasses template lookup when provided)."""
    criteria: Optional[StringMap] = Field(default_factory=dict)
    template: Optional[UnstructuredData | Template] = None
    template_ref: Optional[Identifier] = None
    policy: ProvisioningPolicy = ProvisioningPolicy.ANY
    reference_id: Optional[UUID] = None
    """Explicit reference node to support :attr:`ProvisioningPolicy.CLONE`."""

    satisfied_at_scope_id: Optional[UUID] = None
    """Scope identifier where the requirement was satisfied."""

    _provider_obj: Optional[NodeT] = PrivateAttr(default=None)

    @field_validator("template", mode="before")
    @classmethod
    def _coerce_template_instance(cls, value):
        if isinstance(value, Template):
            return value
        return value

    @model_validator(mode="after")
    def _validate_policy(self):
        # todo: this validates that the req is _independently_ complete.
        #       But we also want to be able to _search_ for an appropriate
        #       template based on criteria...
        """
        identifier is for unique EXISTING
        criteria is filter for any EXISTING
        template is fallback for CREATE or provides UPDATE/CLONE attribs

        identifier only:     unique match, must be satisfied with EXISTING
        criteria only:       any matching, must be satisfied with EXISTING
        id/crit:             unique that also matches criteria, must be satisfied with EXISTING
        template only:       must be satisfied with CREATE
        id/crit, template:   match and UPDATE/CLONE according to template
        """
        if self.policy is ProvisioningPolicy.NOOP:
            raise ValueError("Policy cannot be NOOP")

        has_template_source = (
            self.template is not None
            or self.template_ref is not None
            or self.asset_ref is not None
        )

        if self.policy in [ProvisioningPolicy.EXISTING, ProvisioningPolicy.UPDATE]:
            if self.identifier is None and self.criteria is None:
                raise ValueError("EXISTING/UPDATE requires an identifier or match criteria")

        if self.policy is ProvisioningPolicy.CLONE:
            if self.reference_id is None:
                raise ValueError("CLONE requires reference_id to specify source node")
            if not has_template_source:
                raise ValueError("CLONE requires template data to evolve clone")

        if self.policy in [ProvisioningPolicy.CREATE, ProvisioningPolicy.UPDATE]:
            if not has_template_source:
                raise ValueError(f"{self.policy.name} requires a template")

        if self.policy in [ProvisioningPolicy.ANY]:
            if (
                self.identifier is None
                and self.criteria is None
                and self.asset_ref is None
                and not has_template_source
            ):
                raise ValueError(
                    "ANY requires at least one of identifier, criteria, template, template_ref, or asset_ref"
                )

        return self

    is_unresolvable: bool = False  # tried to resolve previously, but failed
    hard_requirement: bool = True

    @property
    def provider(self) -> Optional[NodeT]:
        # This needs to be a graph item rather than a component
        # to ensure that we have access to the graph
        if self.graph is None:
            return self._provider_obj
        if self.provider_id is not None:
            return self.graph.get(self.provider_id) or self._provider_obj
        return self._provider_obj

    @provider.setter
    def provider(self, value: NodeT) -> None:
        if value is None:
            self._provider_obj = None
            self.provider_id = None
            return
        provider_graph = getattr(value, "graph", None)
        if provider_graph is None or self.graph is None:
            self._provider_obj = value
            self.provider_id = getattr(value, "uid", None)
            return
        if provider_graph is not None and provider_graph is not self.graph:
            self.provider_id = value.uid
            self._provider_obj = value
            return
        if value not in self.graph:
            self.graph.add(value)
        self.graph._validate_linkable(value)  # redundant check that it's in the graph
        self.provider_id = value.uid
        self._provider_obj = value

    @property
    def satisfied(self):
        return self.provider is not None or not self.hard_requirement

    @property
    def reference(self) -> Optional[NodeT]:
        """Return the reference node used for :attr:`ProvisioningPolicy.CLONE`."""

        if self.reference_id is None:
            return None
        return self.graph.get(self.reference_id)

    def get_selection_criteria(self) -> StringMap:
        criteria = deepcopy(self.criteria) or {}
        if self.identifier:
            criteria.setdefault("has_identifier", self.identifier)
        return criteria

    def satisfied_by(self, other: NodeT) -> bool:
        # Another inverted case of Match/Selected
        return other.matches(**self.get_selection_criteria())
