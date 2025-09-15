# tangl/vm/requirement.py
from enum import Flag, auto, Enum
from typing import Optional, Generic, TypeVar
from uuid import UUID

from pydantic import Field, model_validator

from tangl.type_hints import StringMap, UnstructuredData, Identifier
from tangl.core.graph import GraphItem, Node

NodeT = TypeVar('NodeT', bound=Node)


class ProvisioningPolicy(Enum):
    EXISTING = "existing"  # find by identifier and/or criteria match
    UPDATE = "update"      # find and update from template
    CREATE = "create"      # create from template
    CLONE = "clone"        # find and evolve from template


class Requirement(GraphItem, Generic[NodeT]):

    provider_id: Optional[UUID] = None

    identifier: Identifier = None
    criteria: Optional[StringMap] = Field(default_factory=dict)
    template: UnstructuredData = None
    policy: ProvisioningPolicy = ProvisioningPolicy.EXISTING

    @model_validator(mode="after")
    def _validate_policy(self):
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

        return self

    is_unresolvable: bool = False  # tried to resolve previously, but failed
    hard_requirement: bool = True

    @property
    def provider(self) -> Optional[NodeT]:
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
