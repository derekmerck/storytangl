from __future__ import annotations
from logging import getLogger

from ..node import NodeType
from tangl.entity import BaseEntityHandler

logger = getLogger('tangl.assoc')

class AssociationHandler(BaseEntityHandler):
    """
    The AssociationHandler handles dynamic Node relationships.

    Associations can be parent-to-child or peer-to-peer, which can be assigned without
    affecting parent relationships.  In non-parenting relationships, the peer's namespace
    will _not_ cascade from an associate's ancestors.

    Key Features:
        - can_associate_with: Checks if a node can associate with another node.
        - can_disassociate_from: Checks if a node can disassociate from another node.
        - associate_with: Associates two nodes.
        - disassociate_from: Disassociates two nodes.
    """

    @classmethod
    def can_associate_with_strategy(cls, func):
        return cls.strategy(func, 'can_associate_with_strategy')

    @classmethod
    def can_disassociate_from_strategy(cls, func):
        return cls.strategy(func, 'can_disassociate_from_strategy')

    @classmethod
    def can_associate_with(cls, node: NodeType, associate: NodeType, as_parent: bool = False) -> bool:
        try:
            node_res = cls.invoke_strategies(node, associate, as_parent=as_parent,
                                             strategy_annotation="can_associate_with_strategy")
            associate_res = cls.invoke_strategies(associate, node,
                                                  strategy_annotation="can_associate_with_strategy") if isinstance(
                associate, Associating) else []
            return all(node_res + associate_res)
        except Exception as e:
            logger.error(f"Error in can_associate_with: {e}")
            return False

    @classmethod
    def can_disassociate_from(cls, node: NodeType, associate: NodeType) -> bool:
        try:
            node_res = cls.invoke_strategies(node, associate, strategy_annotation="can_disassociate_from_strategy")
            associate_res = cls.invoke_strategies(associate, node, strategy_annotation="can_disassociate_from_strategy") if isinstance(associate, Associating) else []
            return all(node_res + associate_res)
        except Exception as e:
            logger.error(f"Error in can_disassociate_from: {e}")
            return False

    @classmethod
    def associate_with_strategy(cls, func):
        return cls.strategy(func, 'associate_with_strategy')

    @classmethod
    def disassociate_from_strategy(cls, func):
        return cls.strategy(func, 'disassociate_from_strategy')

    @classmethod
    def associate_with(cls, node: Associating, associate: NodeType, as_parent: bool = False):
        if not cls.can_associate_with(node, associate, as_parent=as_parent):
            raise RuntimeError(f"Cannot associate {node} with {associate}")
        cls.invoke_strategies(node, associate, as_parent=as_parent, strategy_annotation="associate_with_strategy")
        if isinstance(associate, Associating):
            cls.invoke_strategies(associate, node, strategy_annotation="associate_with_strategy")

    @classmethod
    def disassociate_from(cls, node: Associating, associate: NodeType):
        if not cls.can_disassociate_from(node, associate):
            raise RuntimeError(f"Cannot disassociate {node} with {associate}")
        cls.invoke_strategies(node, associate, strategy_annotation="disassociate_from_strategy")
        if isinstance(associate, Associating):
            cls.invoke_strategies(associate, node, strategy_annotation="disassociate_from_strategy")

class Associating:
    """
    Associating nodes carry transient links to other nodes.  By default, connections are
    peer-to-peer, but can be flagged as hierarchical (e.g., ownership) so that the invoking node
    becomes the _parent_ of the passed _child_ node.

    Methods:
        - associates: List of nodes associated with this node.
        - associate_with: Associates this node with another node.
        - disassociate_from: Disassociates this node from another node.
    """

    @property
    def associates(self: NodeType) -> list[Associating]:
        return self.find_children(Associating)

    @AssociationHandler.can_associate_with_strategy
    def _can_associate_with_node(self, node: NodeType, as_parent=False):
        return True

    @AssociationHandler.can_disassociate_from_strategy
    def _can_disassociate_from_node(self, node: NodeType):
        return True

    @AssociationHandler.associate_with_strategy
    def _associate_with_node(self: NodeType, node: NodeType, as_parent=False):
        self.add_child(node, as_parent)

    @AssociationHandler.disassociate_from_strategy
    def _disassociate_from_node(self: NodeType, node: NodeType):
        self.remove_child(node)

    def associate_with(self: NodeType, associate: NodeType, as_parent=False):
        # invokes test for 'can associate' in handler
        return AssociationHandler.associate_with(self, associate, as_parent=as_parent)

    def disassociate_from(self: NodeType, associate: NodeType):
        # invokes test for 'can disassociate' in handler
        return AssociationHandler.disassociate_from(self, associate)
