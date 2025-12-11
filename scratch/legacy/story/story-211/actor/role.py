from __future__ import annotations
import random
from typing import Optional
import logging

from pydantic import model_validator

from tangl.type_hints import UniqueLabel, Uid
from tangl.entity.mixins import ConditionHandler
from tangl.graph import GraphFactory
from tangl.graph.mixins import Associating, AssociationHandler
from tangl.story.story import Story, StoryNode
from .actor import Actor

logger = logging.getLogger("tangl.role")
logger.setLevel(logging.WARNING)

class CastingHandler:

    @classmethod
    def cast_by_conditions(cls, story: Story, actor_conditions) -> Optional[Actor]:
        candidates = list( story.find_nodes(Actor) )
        # if there are multiple candidates, the first choice will be random
        random.shuffle(candidates)
        for c in candidates:
            if ConditionHandler.check_conditions_satisfied_by( actor_conditions, c ):
                return c

    @classmethod
    def cast_by_cloning(cls, story, actor_ref, actor_template) -> Optional[Actor]:
        actor = story.get_node(actor_ref)
        if not actor:
            return
        new_actor = actor.evolve( **actor_template )
        # todo: ensure we call init and register it
        return new_actor

    # def _cast_replica(self) -> Actor | None:
    #     """Biologically similar"""
    #     prime = self._cast_ref()
    #     if prime is None:
    #         return
    #     if hasattr( prime, "as_body_kwargs"):
    #         kwargs = prime.as_body_kwargs()
    #     else:
    #         kwargs = prime.asdict()
    #         for field in ['name', 'surname', 'meta', 'parent']:
    #             if field in kwargs:
    #                 kwargs.pop( field )
    #
    #     kwargs |= self.template
    #
    #     if "preserve_surname" in self.locals:
    #         kwargs['surname'] = prime.surname
    #
    #     obj = Actor( **kwargs, context=self.context, parent=self )
    #     if self.world:
    #         self.world.init_node(obj)   # will call world init, if any
    #     else:
    #         obj.__init_entity__()
    #
    #     # todo: cheating for now and using eid instead of a real ref
    #     if "replicas" in prime.locals:
    #         prime.locals['replicas'].add( obj.pid )
    #     else:
    #         prime.locals['replicas'] = { prime.pid, obj.pid }
    #     obj.locals['replicas'] = prime.locals['replicas']  # ref will share future updates
    #
    #     return obj

    @classmethod
    def cast_by_ref(cls, story, actor_ref) -> Optional[Actor]:
        try:
            return story.get_node(actor_ref)
        except:
            # Unable to cast yet, just return None
            pass

    @classmethod
    def cast_by_template(cls, story, actor_template) -> Optional[Actor]:
        logger.debug(f'cast by template {actor_template}')
        if hasattr(story, 'world') and story.world:
            factory = story.world
        else:
            factory = GraphFactory()
        return factory.create_node(base_cls=Actor, graph=story, **actor_template)

    @classmethod
    def cast(cls, node: Role):
        actor = None
        match bool(node.actor_ref), bool(node.actor_template), bool(node.actor_conditions):
            case False, False, True:
                # Has conditions, find satisfactory actor
                actor = cls.cast_by_conditions(node.story, node.actor_conditions)
            case _, _, True:
                # Has conditions plus a ref or a template, error
                raise TypeError('Conditions preclude ref and template')
            case True, True, _:
                # Has both a template and a ref, clone actor
                actor = cls.cast_by_cloning(node.story, node.actor_ref, node.actor_template)
            case True, _, _:
                # Has a ref, find actor
                actor = cls.cast_by_ref(node.story, node.actor_ref)
            case _, True, _:
                # Has a template, create actor
                actor = cls.cast_by_template(node.story, node.actor_template)
        if actor:
            logger.debug(f"found actor: {actor}")
            node.associate_with( actor )

    @classmethod
    def uncast(cls, node: Role):
        if node.actor:
            node.disassociate_from(node.actor)


class Role(Associating, StoryNode):
    """
    A Role is a placeholder for an Actor, similar to how an Edge is a
    placeholder for a dynamically assigned Traversable.

    Actors may be assigned in several ways:
    - By referring to an existing Actor using `actor_ref`
    - By creating a new Actor from a template using `actor_template`
    - By searching for an Actor in the registry that matches `actor_conditions`
    - By cloning an actor and evolving them, using `actor_ref` _and_ providing
      `actor_template` for overrides

    :ivar actor_ref: The id of an existing actor to fill this role
    :ivar actor_template: The template for creating a new actor to fill this role
    :ivar conditions: Conditions for an actor to be assigned to this role

    Like Edge, role does not raise an error if it cannot be dereferenced, but a scene
    with any uncast roles will not be `available`.
    """

    actor_ref: UniqueLabel | Uid = None
    actor_template: dict = None
    actor_conditions: list = None

    @property
    def label(self):
        super_label = StoryNode.label.fget(self)
        if super_label and not super_label.startswith("ro-"):
            return f"ro-{super_label}"
        return super_label

    @model_validator(mode='after')
    def _check_actor_template_label(self) -> Role:
        if self.actor_template and not self.actor_template.get('label'):
            self.actor_template['label'] = self.label_
        return self

    @model_validator(mode='after')
    def _check_at_least_one(self) -> Role:
        """
        If no casting directive is provided, defaults to using the label as an actor ref.
        """
        fields = ['actor_template', 'actor_ref', 'actor_conditions']
        provided_fields = sum(1 for field in fields if getattr(self, field) is not None)

        if provided_fields == 0:
            self.actor_ref = self.label_  # Use the raw label

        provided_fields = sum(1 for field in fields if getattr(self, field) is not None)
        if not provided_fields >= 1:
            raise ValueError("At least one of 'actor_ref', 'actor_template', or 'actor_conditions' must be provided")

        return self

    def cast(self) -> bool:
        if not self.actor:
            # Associates
            CastingHandler.cast(self)
        if self.actor:
            return True
        return False

    @AssociationHandler.can_associate_with_strategy
    def _can_associate_actor(self, actor: Actor, **kwargs):
        if actor is self.actor:
            raise ValueError("Actor is already in this role")
        return True

    @model_validator(mode='after')
    def _try_to_cast(self):
        # only precast if you have a world assigned
        logger.debug("Pre-casting")
        self.cast()

    @AssociationHandler.can_associate_with_strategy
    def _check_valid_actor(self, associate, as_parent: bool = True):
        if not isinstance(associate, Actor):
            return False
        return True

    def uncast(self):
        # Disassociates
        CastingHandler.uncast(self)

    @property
    def actor(self) -> Actor:
        return self.find_child(Actor)
