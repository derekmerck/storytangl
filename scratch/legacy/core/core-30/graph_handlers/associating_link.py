from __future__ import annotations
from uuid import UUID
import copy
from typing import Type, ClassVar, Self
import logging

from pydantic import Field, model_validator

from tangl.type_hints import StringMap, UniqueLabel, Strings, Tags
from tangl.core.handler import BaseHandler, Priority
from tangl.core.entity.handlers import SelfFactoringHandler, AvailabilityHandler, ConditionHandler
from tangl.core.graph import Node, Edge
from .associating import AssociationHandler, Associating

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

class AssociatingLinkHandler(AssociationHandler):

    @classmethod
    def resolve_successor(cls, link: AssociatingLink, **kwargs) -> Node:
        logger.debug("calling resolve_link task")
        return cls.execute_task(link, "on_resolve_link", result_mode='first', **kwargs)

    @BaseHandler.strategy("on_resolve_link", priority=Priority.LATE)
    @staticmethod
    def _resolve_find(link: AssociatingLink, **kwargs) -> Node:
        logger.debug("Trying to resolve find")
        if any([link.successor_conditions, link.successor_ref]):
            return link.graph.find_node(
                shuffle=True,
                with_cls=link.successor_cls,
                with_tags=link.successor_tags,
                with_conditions=link.successor_conditions)

    @BaseHandler.strategy("on_resolve_link", priority=Priority.LATE)
    @staticmethod
    def _resolve_create(link: AssociatingLink, **kwargs) -> Node:
        logger.debug("Trying to resolve create")
        if link.successor_template:
            template = copy.deepcopy(link.successor_template)
            template.setdefault('obj_cls', link.successor_cls)
            return SelfFactoringHandler.create_node(**template, graph=link.graph)

    # todo: Not quite sure how to indicate that on_new should be called with this world's domain...
    # @classmethod
    # def cast_by_template(cls, story, casting_template) -> Optional[Actor]:
    #     logger.debug(f'cast by template {casting_template}')
    #     if hasattr(story, 'world') and story.world:
    #         factory = story.world
    #     else:
    #         from tangl.core.entity.handlers import SelfFactoryingHandler
    #         factory = SelfFactoryingHandler
    #     casting_template.setdefault('obj_cls', Actor)
    #     return factory.create_node(**casting_template, graph=story)

class AssociatingLink(Associating, Edge):
    """
    Links a node to a _dynamically_ assigned resource.

    Note that even if a new node is created, this handler does _not_ parent or
    associate the successor with the edge, although it _does_ add it to the graph.
    """
    # create a node
    successor_template: StringMap = None

    # find satisfying node
    successor_conditions: Strings = None
    successor_tags: Tags = None

    successor_cls: ClassVar[Type[Node]] = None
    successor_parent: ClassVar[bool] = True

    @model_validator(mode='after')
    def _check_at_least_one(self) -> Self:
        req_fields = ['successor_ref', 'successor_template', 'successor_conditions', 'successor_tags']
        provided_fields = sum(1 for field in req_fields if getattr(self, field) is not None)
        if not provided_fields >= 1:
            raise ValueError(f"At least one of {req_fields} must be provided")
        return self

    @model_validator(mode='after')
    def _pre_resolve(self):
        # only precast if you have a world assigned
        logger.debug(f"Pre-resolution")
        self._resolve_successor()

    def _resolve_successor(self) -> Node:
        successor = AssociatingLinkHandler.resolve_successor(self)
        self.associate_with(successor)

    def associate_with(self, other: Associating, as_parent=False, **kwargs):
        if not other:
            return
        if isinstance(other, (UniqueLabel, UUID)):
            other = self.graph.get_node(other)
        if other in self.children:
            logger.debug("Declining to re-associate the same successor")
            return
        # The availability check induces a circular dependency since avail
        # also tries to find an associate if possible.
        return super().associate_with(other=other, as_parent=as_parent, skip_avail_check=True, **kwargs)

    @property
    def successor(self) -> Node:
        try:
            return Edge.successor.fget(self)
        except KeyError:
            pass

    @AssociationHandler.can_associate_strategy()
    def _can_associate_with_cls(self, other: Associating, **kwargs) -> bool:
        if not isinstance(other, self.successor_cls):
            logger.warning(f"Tried to associate with wrong cls {other!r}")
            return False
        return True

    @AssociationHandler.can_associate_strategy()
    def _matches_conditions(self, other: Associating, **kwargs) -> bool:
        if self.successor_conditions and not ConditionHandler.check_conditions_satisfied_by(self.successor_conditions, other):
            return False
        return True

    @AssociationHandler.can_associate_strategy()
    def _matches_tags(self, other: Associating, **kwargs) -> bool:
        if self.successor_tags and not other.has_tags(self.successor_tags):
            return False
        return True

    @AssociationHandler.associate_strategy(priority=Priority.FIRST)
    def _set_successor_ref(self, other: Associating, **kwargs):
        if not isinstance(other, Associating):
            raise TypeError(f"Other {other!r} is not associating")
        self.successor_ref = other.uid

    @AssociationHandler.disassociate_strategy()
    def _unset_successor_ref(self, other: Associating, **kwargs):
        self.successor_ref = None
