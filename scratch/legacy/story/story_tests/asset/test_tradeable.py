import pytest
import pydantic

from tangl.graph import Node
from tangl.graph.mixins.wrapped_singleton import WrappedSingleton
from tangl.story.asset.tradeable import TradeHandler, CanTrade, Tradeable


class MockTrader(CanTrade, Node):
    name: str

class MockTradeable(Tradeable, Node):
    name: str


@pytest.fixture
def tradeable_nodes():
    trader1 = MockTrader(label="trader1", name="Trader 1")
    trader2 = MockTrader(label="trader2", name="Trader 2")
    item1 = MockTradeable(label="item1", name="Item 1")
    item2 = MockTradeable(label="item2", name="Item 2")
    trader1.associate_with(item1)
    trader2.associate_with(item2)

    return trader1, trader2, item1, item2


def test_trade_handler_success(tradeable_nodes):

    trader1, trader2, item1, item2 = tradeable_nodes
    assert item1 in trader1.tradeables
    assert item2 in trader2.tradeables

    trade_handler = TradeHandler()
    trade_handler.trade(trader1, item1, trader2, item2)

    assert item1 in trader2.tradeables
    assert item2 in trader1.tradeables

def test_trade_handler_failure_no_item(tradeable_nodes):

    trader1, trader2, item1, item2 = tradeable_nodes
    # Note: trader2 does not own item2
    trader2.disassociate_from(item2)

    trade_handler = TradeHandler()
    with pytest.raises(ValueError):
        trade_handler.trade(trader1, item1, trader2, item2)

@pytest.mark.xfail(reason="Not sure why this isn't working")
def test_trade_handler_failure_no_agreement(tradeable_nodes):

    trader1, trader2, item1, item2 = tradeable_nodes

    class StubbornNode(MockTrader):
        def agrees_to_trade(self, my_item: Node, their_item: Node) -> bool:
            return False

    stubborn_trader = StubbornNode(label="stubborn_trader", name="Stubborn Trader")
    stubborn_trader.receive(item1)

    trade_handler = TradeHandler()
    with pytest.raises(ValueError):
        trade_handler.trade(stubborn_trader, item1, trader2, item2)

from tangl.story.asset import AssetType

class MockTradeableAssetType(Tradeable, AssetType):
    name: str


TradeableAsset = WrappedSingleton.create_wrapper_cls("TradeableAsset", MockTradeableAssetType)

def test_tradeable_asset():
    # Create some nodes and assets
    trader1 = MockTrader(label="trader1", name="Trader 1")
    trader2 = MockTrader(label="trader2", name="Trader 2")
    asset1 = MockTradeable(label="asset1", name="Asset 1")
    trader1.associate_with(asset1)

    # Check that the nodes own the correct assets
    assert asset1 in trader1.tradeables

    # Create a TradeHandler and perform the trade
    trade_handler = TradeHandler()
    trade_handler.give(trader1, asset1, trader2)

    # Check that the nodes now own the other's assets
    assert asset1 not in trader1.tradeables
    assert asset1 in trader2.tradeables
