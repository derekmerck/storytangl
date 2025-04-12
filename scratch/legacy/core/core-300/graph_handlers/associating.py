from __future__ import annotations
import logging

from tangl.type_hints import UniqueLabel
from tangl.core.handler import BaseHandler, Priority
from tangl.core.entity.handlers import Lockable
from tangl.core.graph import Node

logger = logging.getLogger(__name__)

class AssociationHandler(BaseHandler):

    # @BaseHandler.task_signature
    # def on_can_associate(node: Associating, *, other: Associating, as_parent=False, **kwargs) -> bool:
    #     ...
    #
    # @BaseHandler.task_signature
    # def on_associate(node: Associating, *, other: Associating, as_parent=False, **kwargs):
    #     ...

    # @BaseHandler.task_signature
    # def on_can_disassociate(node: Associating, *, other: Associating, **kwargs) -> bool:
    #     ...
    #
    # @BaseHandler.task_signature
    # def on_disassociate(node: Associating, *, other: Associating, **kwargs):
    #     ...

    @classmethod
    def can_associate_strategy(cls, task_id: UniqueLabel = "on_can_associate",
                             domain: UniqueLabel = "global",
                             priority: int = Priority.NORMAL ):
        return super().strategy(task_id, domain, priority)

    @classmethod
    def associate_strategy(cls, task_id: UniqueLabel = "on_associate",
                             domain: UniqueLabel = "global",
                             priority: int = Priority.NORMAL ):
        return super().strategy(task_id, domain, priority)

    @classmethod
    def can_disassociate_strategy(cls, task_id: UniqueLabel = "on_can_disassociate",
                                domain: UniqueLabel = "global",
                                priority: int = Priority.NORMAL):
        return super().strategy(task_id, domain, priority)

    @classmethod
    def disassociate_strategy(cls, task_id: UniqueLabel = "on_disassociate",
                                domain: UniqueLabel = "global",
                                priority: int = Priority.NORMAL):
        return super().strategy(task_id, domain, priority)

    @classmethod
    def can_associate_with(cls, node: Associating, other: Associating, as_parent=False, **kwargs) -> bool:
        return cls.execute_task(node, 'on_can_associate', other=other, as_parent=as_parent, result_mode="all_true", **kwargs) and cls.execute_task(other, 'on_can_associate', other=node, result_mode="all_true", **kwargs)

    @classmethod
    def associate_with(cls, node: Associating, other: Associating, as_parent=False, skip_check=False, **kwargs):
        """
        If 'as_parent', then add other as a child of node, otherwise, add them
        as children of one-another without reparenting either.
        """
        if not skip_check and not cls.can_associate_with(node, other, as_parent=as_parent, **kwargs):
            raise RuntimeError
        cls.execute_task(node, 'on_associate', other=other, as_parent=as_parent, **kwargs)
        cls.execute_task(other, 'on_associate', other=node, **kwargs)
        node.add_child(other, as_parent=as_parent)
        if not as_parent:
            other.add_child(node, as_parent=False)

    @classmethod
    def can_disassociate_from(cls, node: Associating, other: Associating, **kwargs) -> bool:
        return cls.execute_task(node, 'on_can_disassociate', other=other, result_mode="all_true", **kwargs) and cls.execute_task(other, 'on_can_disassociate', other=node, result_mode="all_true", **kwargs)

    @classmethod
    def disassociate_from(cls, node: Associating, other: Associating, skip_check=False, **kwargs):
        """
        Calls remove child on both, if one is the parent of the other, they will be unparented.
        """
        logger.debug("Trying to disassociate {node!r} from {other!r}")
        if not skip_check and not cls.can_disassociate_from(node, other, **kwargs):
            raise RuntimeError
        cls.execute_task(node, 'on_disassociate', other=other, **kwargs)
        cls.execute_task(other, 'on_disassociate', other=node, **kwargs)
        if node in other.children:
            other.remove_child(node)
        if other in node.children:
            node.remove_child(other)

class Associating(Lockable):

    @property
    def associates(self: Node) -> list[Associating]:
        return self.find_children(Associating)

    @AssociationHandler.can_associate_strategy()
    def _check_availability(self, skip_avail_check=False, **kwargs) -> bool:
        if skip_avail_check:
            return True
        return self.available(**kwargs)
    AssociationHandler.register_strategy(_check_availability, 'can_disassociate')

    def can_associate_with(self, other: Associating, as_parent=False, **kwargs) -> bool:
        return AssociationHandler.can_associate_with(self, other, as_parent=as_parent, **kwargs)

    def associate_with(self, other: Associating, as_parent=False, **kwargs):
        return AssociationHandler.associate_with(self, other, as_parent=as_parent, **kwargs)

    def can_disassociate_from(self, other: Associating, **kwargs) -> bool:
        return AssociationHandler.can_disassociate_from(self, other, **kwargs)

    def disassociate_from(self, other: Associating, **kwargs):
        return AssociationHandler.disassociate_from(self, other, **kwargs)

