import pytest
import attr

from tangl.core import Node
from tangl.core.mixins.ownable import DiscreteTransactionHandler, Ownable, Owner

OwnerNode = attr.make_class("OwnerNode", (), (Owner, Node))
OwnableNode = attr.make_class("OwnableNode", (), (Ownable, Node))


@pytest.fixture
def ownables():
    # Initialize Owner instances
    trader_a = OwnerNode(label="trader_a")
    trader_b = OwnerNode(label="trader_b")
    # Create two OwnableMixin instances to act as tradable items
    item_a = OwnableNode(label="item_a")
    item_b = OwnableNode(label="item_b")
    # Add items to respective traders
    trader_a.add_child(item_a)
    trader_b.add_child(item_b)
    return trader_a, trader_b, item_a, item_b

def test_trade(ownables):
    trader_a, trader_b, item_a, item_b = ownables

    print( [ o.label for o in trader_a.owned ] )

    # Trader A should have item A and not have item B
    assert item_a in trader_a.owned
    assert item_b not in trader_a.owned
    # Trader B should have item B and not have item A
    assert item_b in trader_b.owned
    assert item_a not in trader_b.owned

    assert DiscreteTransactionHandler.can_send(trader_a, item_a)
    assert DiscreteTransactionHandler.can_receive(trader_a, item_b)

    assert DiscreteTransactionHandler.can_send(trader_b, item_b)
    assert DiscreteTransactionHandler.can_receive(trader_b, item_a)

    # prime, receive, send, partner
    assert DiscreteTransactionHandler.can_transact(trader_a, item_b, item_a, trader_b)

    # Execute trade
    DiscreteTransactionHandler.transact(trader_a, item_b, item_a, trader_b)

    # Trader A should now have item B and not have item A
    assert item_b in trader_a.owned
    assert item_a not in trader_a.owned
    # Trader B should now have item A and not have item B
    assert item_a in trader_b.owned
    assert item_b not in trader_b.owned

def test_multiple_trades(ownables):
    trader_a, trader_b, item_a, item_b = ownables
    # Execute first trade
    DiscreteTransactionHandler.transact(trader_a, item_b, item_a, trader_b)
    # Execute second trade
    DiscreteTransactionHandler.transact(trader_a, item_a, item_b, trader_b)
    # Verify the items are back to original owners
    assert item_a in trader_a.owned
    assert item_b in trader_b.owned


def test_invalid_trade(ownables):
    trader_a, trader_b, item_a, item_b = ownables
    # Try to trade an item not owned by trader_a
    with pytest.raises(RuntimeError):
        DiscreteTransactionHandler.transact(trader_a, item_a, item_b, trader_b)


def test_disassociate_associate(ownables):
    trader_a, _, item_a, _ = ownables
    # Create a new owner
    new_owner = OwnerNode(label="new_owner")
    # Disassociate from current owner
    item_a.disassociate()
    assert item_a not in trader_a.owned
    # Associate with new owner
    item_a.associate(new_owner)
    assert item_a in new_owner.owned


def test_trade_with_oneself(ownables):
    trader_a, _, item_a, item_b = ownables
    # Add item_b to trader_a
    item_b.associate( trader_a )
    # Attempt to trade item_a for item_b with oneself
    with pytest.raises(RuntimeError): # or any specific error you want to raise in this scenario
        DiscreteTransactionHandler.transact(trader_a, item_b, item_a, trader_a)


class CustomTransactionHandler(DiscreteTransactionHandler):
    @classmethod
    def can_transact(cls, prime, node_out, node_in, partner):
        # Require approval for transactions
        return super().can_transact(prime, node_out, node_in, partner) and prime.approved

def test_custom_transaction_handler(ownables):
    trader_a, trader_b, item_a, item_b = ownables
    trader_a.transaction_handler = CustomTransactionHandler
    trader_a.approved = False  # Assume this is a new attribute

    assert not CustomTransactionHandler.can_transact(trader_a, item_b, item_a, trader_b)

    with pytest.raises(RuntimeError):
        CustomTransactionHandler.transact(trader_a, item_b, item_a, trader_b)
