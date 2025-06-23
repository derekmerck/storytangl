from typing import Generic, TypeVar, Optional
from uuid import UUID

from pydantic import Field, model_validator

from tangl.type_hints import StringMap, Identifier
from tangl.core.entity import Edge, Node
from tangl.core.handler import Predicate
from .requirement import HasRequirement


NodeT = TypeVar('NodeT', bound=Node)

class DependencyEdge(HasRequirement[NodeT], Edge[Node, Optional[NodeT]], Generic[NodeT]):
    # dynamic link concepts, green
    """
    Dependencies are edges with defined sources and open destinations.  For example, a
    node might _require_ a green friend node before it can be used.

    Open/unresolved dependencies at the solution frontier will be provisioned, if possible,
    by the resolver.

    Dependencies may be hard (default, node is unsatisfied if they cannot be resolved) or soft
    (provide if possible), and they may be restricted to only existing nodes, or using indirect
    providers to create and introduce a new node.

    Hard dependencies may also carry their own fallback builder for when no satisfactory
    pre-existing direct or indirect provider is available.
    """
    dest_id: Optional[UUID] = Field(None)  # Optional now
    dest_ref: Optional[Identifier] = Field(None, init_var=True)  # sugar for criteria={'alias': ref}
    req_criteria: StringMap = Field(default_factory=dict, alias="dest_criteria")
    req_predicate: Predicate = Field(None, alias="dest_predicate")

    @model_validator(mode="before")
    @classmethod
    def _map_ref_to_criteria(cls, data):
        dest_ref = data.pop("dest_ref")
        if dest_ref is not None:
            if data["dest_criteria"] is None:
                data["dest_criteria"] = {}
            data["dest_criteria"].setdefault("alias", dest_ref)
        return data


class AffordanceEdge(HasRequirement[NodeT], Edge[Optional[NodeT], Node], Generic[NodeT]):
    """
    Affordances are edges with defined destinations and open sources.  For example, a node may
    be available from any other node that has a green friend node available.

    Affordances are the inverse of a dependency.  A _satisfied_ dependency of node becomes a
    _satisfied_ affordance for the destination, and vice versa.

    Affordances represent nodes that can be made available whenever conditions are met.

    Like dependencies, they can be marked soft (default, provide if possible) or hard (critical,
    paths will be unavailable if they cannot be provided).

    _All_ affordances in the scope (i.e., visible to this node) will be tested _against_ the
    frontier to see if they can be linked. This is usually to present choices or resources that
    follow an entity, like a character avatar that is always available in that character's dialogs,
    or choices that become active whenever specific conditions are met.

    Hard affordances in the scope with a satisfied indirect provider (i.e., a new source
    resource can be immediately linked) may also pre-create a source that will have priority
    when linked later.  For example, to pre-cast a particular character that will be available
    everywhere in a scene.
    """
    # open source
    source_id: Optional[UUID] = Field(None)  # Optional now
    source_ref: Optional[Identifier] = Field(None, init_var=True)  # sugar for criteria={'alias': ref}
    req_criteria: StringMap = Field(default_factory=dict, alias="source_criteria")
    req_predicate: Predicate = Field(None, alias="source_predicate")

    @model_validator(mode="before")
    @classmethod
    def _map_ref_to_criteria(cls, data):
        source_ref = data.pop("source_ref")
        if source_ref is not None:
            if data["source_criteria"] is None:
                data["source_criteria"] = {}
            data["source_criteria"].setdefault("alias", source_ref)
        return data
