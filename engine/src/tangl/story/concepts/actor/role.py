from __future__ import annotations
import logging
from typing import Self

from pydantic import Field, model_validator, field_validator

from tangl.exceptions import AssociationHandlerError
from tangl.type_hints import UniqueLabel, StringMap, Identifier
from tangl.core.graph.graph import Graph  # noqa: F401  # ensure forward ref availability
from tangl.vm import Dependency, ProvisioningPolicy, Requirement
from .actor import Actor

logger = logging.getLogger(__name__)


class Role(Dependency[Actor]):
    """
    A Role is a placeholder for a dynamically assigned Actor, based on the
    mechanic of using an OpenEdge as a placeholder for a dynamically assigned
    Node.

    Actors may be assigned in several ways:

    - By referring to an existing Actor using `actor_ref`
    - By creating a new Actor from a template using `actor_template`
    - By searching for an Actor in the registry that matches `actor_criteria`
      and/or `actor_tags`
    - By cloning an actor and evolving them, using `actor_ref` _and_ providing
      `actor_template` for overrides

    :ivar actor_ref: The id of an existing actor to fill this role
    :ivar actor_template: The template for creating a new actor to fill this role
    :ivar actor_criteria: Attribute criteria, tags, and predicate conditions to select an actor suitable for this role

    Like OpenEdge, Role will not raise an error if it cannot be dereferenced, but a Scene
    with any uncast roles hard dep roles will not be `available`.
    """

    # todo: roles can come with titles, assets that they transfer to the referent

    @property
    def actor(self) -> Actor | None:
        return self.requirement.provider

    @actor.setter
    def actor(self, value: Actor) -> None:
        self.requirement.provider = value

    # init helpers
    actor_ref: Identifier = Field(None, init_var=True)
    actor_criteria: StringMap = Field(None, init_var=True)
    actor_template: StringMap = Field(None, init_var=True)
    requirement_policy: ProvisioningPolicy = Field(None, init_var=True)

    @model_validator(mode="before")
    @classmethod
    def _validate_req(cls, data):
        if 'requirement' not in data:
            req = {
                'identifier': data.pop('actor_ref', None),
                'criteria': data.pop('actor_criteria', {}),
                'template': data.pop('actor_template', None),
                'policy': data.pop('requirement_policy', ProvisioningPolicy.ANY),
                'graph': data['graph']
            }
            if req['template'] is not None:
                # we can infer the object cls of the template
                req['template'].setdefault('obj_cls', Actor)
            data['requirement'] = req
        return data

    # @field_validator('label', mode="after")
    # @classmethod
    # def _uniquify_label(cls, data):
    #     # Often the role is just a character identifier
    #     if data and not data.startswith("ro-"):
    #         return f"ro-{data}"
    #     return data

    # roles may come with titles and assets that should be inherited by the assigned actor
    # assets: list[Asset] = None  # assets associated with the role
    #
    # def cast(self, actor: Actor = None) -> Actor:
    #     """
    #     Assign, find, or create or find a suitable actor for this role.
    #
    #     If successful, it also associates the actor with the role.
    #
    #     If no actor can be found, it returns None.
    #     If an actor is created or discovered but cannot be associated, it raises an association error.
    #     """
    #     if not self.actor:
    #         self._resolve_successor()
    #         if self.actor is not None:
    #             self.associate_with(actor)  # This will check 'can associate'
    #     return self.actor
    #
    # def uncast(self):
    #     if self.actor:
    #         return self.disassociate_from(self.actor)

    # @on_can_associate.register()
    # def _already_cast(self, **kwargs):
    #     if self.actor is not None:
    #         logger.warning(f"Already cast role {self!r}, must uncast before recasting")
    #     return True

