from __future__ import annotations
from typing import Callable

from tangl.exceptions import TradeHandlerError
from tangl.graph import NodeType
from tangl.graph.mixins.associating import AssociationHandler, Associating

# todo: integrate this with the fungible wallet

class TradeHandler(AssociationHandler):

    default_strategy_annotation = "willing_to_trade_strategy"

    @classmethod
    def willing_to_trade_strategy(cls, func: Callable):
        return super().strategy(func)

    @classmethod
    def willing_to_trade(cls, node: CanTrade,
              nodes_item: Tradeable = None,   # node loses this
              partner: CanTrade = None,   # trading partner
              partners_item: Tradeable = None):  # node gains this):
        vals = cls.invoke_strategies(node, nodes_item, partner, partners_item)
        vals += cls.invoke_strategies(partner, partners_item, node, nodes_item)
        return all(vals)

    @classmethod
    def can_give(cls, sender: NodeType, item_to_send: NodeType) -> bool:
        return cls.can_disassociate_from(sender, item_to_send)

    @classmethod
    def give(cls, sender: NodeType, item: NodeType, receiver: NodeType = None):
        cls.disassociate_from(sender, item)
        if receiver:
            cls.associate_with(receiver, item)

    @classmethod
    def can_receive(cls, receiver: NodeType, item_to_receive: NodeType) -> bool:
        return cls.can_associate_with(receiver, item_to_receive)

    @classmethod
    def receive(cls, receiver: NodeType, item: NodeType, sender: NodeType = None):
        cls.associate_with(receiver, item)
        if sender:
            cls.disassociate_from(sender, item)

    @classmethod
    def can_trade(cls, node: NodeType, nodes_item: NodeType,
                   partner: NodeType, partners_item: NodeType) -> bool:
        if not cls.can_receive(node, partners_item) or \
              not cls.can_receive(partners_item, nodes_item) or \
              not cls.can_give(node, nodes_item) or \
              not cls.can_give(partner, partners_item):
            return False
        return True

    @classmethod
    def trade(cls, node: NodeType, nodes_item: NodeType,
                   partner: NodeType, partners_item: NodeType):
        if not cls.willing_to_trade(node, nodes_item, partner, partners_item):
            raise TradeHandlerError(f"Unwilling to trade {nodes_item} and {partners_item} between {node} and {partners_item}")
        if not cls.can_trade(node, nodes_item, partner, partners_item):
            raise TradeHandlerError("Bad trade attempted")
        node.give(nodes_item, partner)
        partner.give(partners_item, node)


# class TradeHandler:
#     """
#     Responsible for managing trade transactions between entities.
#
#     This class checks the validity of proposed trades and, if valid, conducts
#     the exchange of `Ownable` nodes between two entities.
#
#     Methods:
#         - trade: Validates and executes the trade between two entities.
#     """
#     @classmethod
#     def trade(cls, from_entity: TraderMixin, to_entity: TraderMixin, from_item: OwnableMixin, to_item: OwnableMixin):
#         # Check if both entities have the items they are trading
#         if from_item not in from_entity.owned_objects or to_item not in to_entity.owned_objects:
#             raise ValueError("One of the items is not available for trade")
#
#         # Check if both entities agree to the trade (could involve more complex logic)
#         if not from_entity.agrees_to_trade(from_item, to_item) or not to_entity.agrees_to_trade(to_item, from_item):
#             raise ValueError("One of the entities does not agree to the trade")
#
#         # Execute the trade
#         from_entity.remove_owned_object(from_item)
#         to_entity.add_owned_object(from_item)
#         to_entity.remove_owned_object(to_item)
#         from_entity.add_owned_object(to_item)
#
#         # Potentially trigger other events or effects as a result of the trade


class CanTrade(Associating):
    """
    Mixin for entities capable of participating in trade transactions.

    Provides methods to manage owned objects and to initiate trades. While
    basic trading logic is provided, it can be extended or overridden
    to cater to specific trading scenarios.

    :ivar tradeables: List of items currently owned by the entity.

    :Methods:

    - :meth:`willing_to_trade`: Determines if the entity agrees to a proposed trade.
    - :meth: `can_receive`
    - :meth:`receive`: Gain a tradeable.
    - :meth: `can_give`
    - :meth:`give`: Lose a tradeable.
    """
    # Parent
    @property
    def tradeables(self) -> list[Tradeable]:
        return self.find_children(Tradeable)

    @TradeHandler.willing_to_trade_strategy
    def _willing_to_trade(self,
                          nodes_item: Tradeable = None,
                          partner: CanTrade = None,
                          partners_item: Tradeable = None):
        # This is a trivial placeholder implementation, each subclass
        # that uses the TraderMixin should override this with logic that
        # decides whether this node agrees to the trade.
        return True

    def willing_to_trade(self, nodes_item, partner, partners_item):
        return TradeHandler.willing_to_trade(self, nodes_item, partner, partners_item)

    def can_receive(self, *args, **kwargs):
        return TradeHandler.can_receive(self, *args, **kwargs)

    def receive(self, *args, **kwargs):
        return TradeHandler.receive(self, *args, **kwargs)

    def can_give(self, *args, **kwargs):
        return TradeHandler.can_give(self, *args, **kwargs)

    def give(self, *args, **kwargs):
        return TradeHandler.give(self, *args, **kwargs)

class Tradeable(Associating):
    """
    A mixin for nodes that can be owned by trading entities.

    Provides placeholder methods for actions taken upon association
    (acquiring) or disassociation (releasing) with an entity. While the
    class provides trivial default implementations, they are intended to be
    overridden for specific behaviors during trades.
    """
    # Child
    pass
