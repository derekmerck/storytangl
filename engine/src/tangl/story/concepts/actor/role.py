from __future__ import annotations
import logging
from typing import Self

from pydantic import Field, model_validator, field_validator

from tangl.exceptions import AssociationHandlerError
from tangl.type_hints import UniqueLabel, StringMap, Identifier
from tangl.vm import Dependency
from .actor import Actor

logger = logging.getLogger(__name__)


class Role(Dependency[Actor]):
    """
    A Role is a placeholder for a dynamically assigned Actor, similar to how an Edge
    is a placeholder for a dynamically assigned Traversable.

    Actors may be assigned in several ways:

    - By referring to an existing Actor using `actor_ref`
    - By creating a new Actor from a template using `actor_template`
    - By searching for an Actor in the registry that matches `actor_conditions`
      and/or `actor_tags`
    - By cloning an actor and evolving them, using `actor_ref` _and_ providing
      `actor_template` for overrides

    :ivar actor_ref: The id of an existing actor to fill this role
    :ivar actor_template: The template for creating a new actor to fill this role
    :ivar actor_conditions: Conditions for an actor to be assigned to this role

    Like Edge, role does not raise an error if it cannot be dereferenced, but a scene
    with any uncast roles will not be `available`.
    """

    successor_ref: Identifier = Field(None, alias="actor_ref")
    successor_template: StringMap = Field(None, alias="actor_template")
    successor_criteria: StringMap = Field(None, alias="actor_criteria")
    # successor_conditions: Strings = Field(None, alias='actor_conditions')

    @property
    def actor(self) -> Actor:
        return self.successor

    @field_validator('label', mode="after")
    @classmethod
    def _uniquify_label(cls, data):
        if data and not data.startswith("ro-"):
            return f"ro-{data}"
        return data

    # roles may come with titles and assets that should be inherited by the assigned actor
    # assets: list[Asset] = None  # assets associated with the role

    def cast(self, actor: Actor = None) -> Actor:
        """
        Assign, find, or create or find a suitable actor for this role.

        If successful, it also associates the actor with the role.

        If no actor can be found, it returns None.
        If an actor is created or discovered but cannot be associated, it raises an association error.
        """
        if not self.actor:
            self._resolve_successor()
            if self.actor is not None:
                self.associate_with(actor)  # This will check 'can associate'
        return self.actor

    def uncast(self):
        if self.actor:
            return self.disassociate_from(self.actor)

    # @on_can_associate.register()
    # def _already_cast(self, **kwargs):
    #     if self.actor is not None:
    #         logger.warning(f"Already cast role {self!r}, must uncast before recasting")
    #     return True

