"""
Commodity is _not_ an asset, it is a protocol for buying and selling

It is a tradeable with _value_
"""

from __future__ import annotations
from numbers import Number

# from tangl.graph.mixins import Tradeable, TradeHandler, CanTrade
from .asset import AssetType

# should be able to hook gain and lose in world, too.  If you are receiving
# chattel of type x, push such and such an event.
#
# __on_gain_asset__, __on_lose_asset__


class CommodityTradeHandler(TradeHandler):
    """
    This is a trade handler with a notion of 'value'
    """

    def can_buy(self, commodity: CommodityType, buyer: CommodityTrader, seller: CommodityTrader = None, count=1, discount=0.0):
        from .fungible import cash
        price = commodity.value * count * (1.0-discount)
        if seller and not seller.can_lose(self, count):
            return False
        if buyer.can_lose(cash, price) and buyer.can_gain(self, count):
            return True
        return False

    def buy(self, buyer: CommodityTrader, seller: CommodityTrader=None, count=1, discount=0.0):
        from .fungible import cash
        price = self.value * count * (1.0-discount)
        if not self.can_buy(buyer, seller, count, discount):
            raise RuntimeError

        buyer.gain(self, count)
        buyer.lose(cash, price)

        if seller:
            seller.lose(self, count)
            seller.gain(cash, price)

    def can_sell(self, seller: CommodityTrader, buyer: CommodityTrader=None, count=1, discount=0.0):
        from .fungible import cash
        price = self.value * count * (1.0-discount)
        if not seller.can_lose(self, count):
            return False
        if buyer and not (buyer.can_lose(cash, price) or buyer.can_gain(self, count)):
            return False
        return True

    def sell(self, seller: CommodityTrader, buyer: CommodityTrader=None, count=1, discount=0.0):
        from .fungible import cash
        if not self.can_sell(seller, buyer, count, discount):
            raise RuntimeError
        price = self.value * count * discount

        seller.lose(self, count)
        seller.gain(cash, price)

        if buyer:
            buyer.gain(self, count)
            buyer.lose(cash, price)


class CommodityType(Tradeable, AssetType):
    """
    Commodities are objects that have value and can be possessed,
    traded, etc.

    Nodes that can gain or lose commodities should implement the Vendor
    protocol.

    Not all commodities are assets.  _Fungibles_ are assets that are
    also commodities.
    """

    value: float = 1.0


class CommodityTrader(CanTrade):
    def gain(self, asset: CommodityType, count: Number = 1): ...
    def lose(self, asset: CommodityType, count: Number = 1): ...
    def can_gain(self, asset: CommodityType, count: Number = 1) -> bool: ...
    def can_lose(self, asset: CommodityType, count: Number = 1) -> bool: ...
