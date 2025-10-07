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

from pydantic import Field, model_validator

from tangl.type_hints import StringMap, UnstructuredData, Identifier
from tangl.core.graph import GraphItem, Node, Graph

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
    (e.g., :class:`Dependency`, :class:`Affordance`) and
    are satisfied by binding a provider node.

    Key Features
    ------------
    * **Multiple acquisition modes** – find, update, create, or clone via :class:`ProvisioningPolicy`.
    * **Flexible targeting** – match by :attr:`identifier` or :attr:`criteria` (or both).
    * **Templated provisioning** – :attr:`template` provides fields for UPDATE/CREATE/CLONE.
    * **Binding** – :attr:`provider` resolves to a live :class:`~tangl.core.graph.Node`; auto-added to the graph if needed.
    * **Hard/soft semantics** – :attr:`hard_requirement` gates whether unresolved requirements block progress.

    API
    ---
    - :attr:`identifier` – alias/uuid/label for a specific provider.
    - :attr:`criteria` – dict used with :meth:`~tangl.core.registry.Registry.find_all` to discover candidates.
    - :attr:`template` – unstructured data used to create/update/clone a provider.
    - :attr:`policy` – :class:`ProvisioningPolicy` that validates required fields.
    - :attr:`provider` – get/set bound provider node (backed by :attr:`provider_id`).
    - :attr:`hard_requirement` – if ``True``, unresolved requirements are reported at planning end.
    - :attr:`is_unresolvable` – sticky flag when prior attempts failed.
    - :attr:`satisfied` – ``True`` if a provider is bound or the requirement is soft.

    Notes
    -----
    Validation rules:

    - ``EXISTING/UPDATE/CLONE`` require :attr:`identifier` **or** :attr:`criteria`.
    - ``CREATE/UPDATE/CLONE`` require :attr:`template`.
    """
    provider_id: Optional[UUID] = None

    identifier: Identifier = None
    criteria: Optional[StringMap] = Field(default_factory=dict)
    template: UnstructuredData = None
    policy: ProvisioningPolicy = ProvisioningPolicy.ANY

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

        if self.policy in [ProvisioningPolicy.EXISTING,
                           ProvisioningPolicy.UPDATE,
                           ProvisioningPolicy.CLONE ]:
            if self.identifier is None and self.criteria is None:
                raise ValueError("EXISTING/UPDATE/CLONE requires an identifier or match criteria")

        if self.policy in [ProvisioningPolicy.CREATE,
                           ProvisioningPolicy.UPDATE,
                           ProvisioningPolicy.CLONE]:
            if self.template is None:
                raise ValueError("CREATE/UPDATE/CLONE requires a template")

        if self.policy in [ProvisioningPolicy.ANY]:
            if self.identifier is None and self.criteria is None and self.template is None:
                raise ValueError("ALL requires at least one of identifier, criteria, or template")

        return self

    is_unresolvable: bool = False  # tried to resolve previously, but failed
    hard_requirement: bool = True

    @property
    def provider(self) -> Optional[NodeT]:
        # This needs to be a graph item rather than a component
        # to ensure that we have access to the graph
        if self.provider_id is not None:
            return self.graph.get(self.provider_id)

    @provider.setter
    def provider(self, value: NodeT) -> None:
        if value is None:
            self.provider_id = None
            return
        if value not in self.graph:
            self.graph.add(value)
        self.graph._validate_linkable(value)  # redundant check that it's in the graph
        self.provider_id = value.uid

    @property
    def satisfied(self):
        return self.provider is not None or not self.hard_requirement
