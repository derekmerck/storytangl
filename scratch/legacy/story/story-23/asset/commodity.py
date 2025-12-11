from typing import *

import attr

from .asset import AssetType
from .wallet import AssetWallet


@attr.define(slots=False, init=False, eq=False, hash=False)
class Commodity(AssetType):
    _instances: ClassVar[dict] = dict()

    units: str = " units"

    @property
    def value(self) -> float:
        return self.utility

    def price(self, count: int, currency: 'Commodity' = None, mult: float = 1.0, **kwargs) -> AssetWallet:
        val =  self.value * currency.value * count * mult
        res = AssetWallet( {currency.uid: val} )
        return res

    def buy(self,
            buyer: AssetWallet,
            seller: AssetWallet = None,
            currency: 'Commodity'= None,
            count: int = 1,
            mult: float=1.0, **kwargs):
        if not currency:
            currency = Commodity.instance("cash")
        buyer.transact( seller,
                        self.price(count, currency, mult),
                        AssetWallet({self.uid: count}) )

    # can't just invert buy b/c buyer may be none for sell
    def sell(self,
             seller: AssetWallet,
             buyer: AssetWallet = None,
             currency: 'Commodity' = None,
             count: int = 1,
             mult: float = 1.0, **kwargs):
        if not currency:
            currency = Commodity.instance("cash")
        seller.transact( buyer,
                         AssetWallet({self.uid: count}),
                         self.price(count, currency, mult) )

    def render(self):
        res = super().render()
        res['value'] = self.value
        return res

    def ns(self) -> dict:
        _ns = super().ns()
        _ns['value'] = self.value
        return _ns


Commodity.__init_entity_subclass__()

cash = Commodity(uid="cash", desc="Common currency of the realm (value={{ value }})")

if TYPE_CHECKING:
    Commodity_ = Commodity
else:
    Commodity_ = object


class CommodityMixin_(Commodity_):
    # represent self as item that can be traded with a wallet, added, discarded

    def price(self, currency: Commodity = None, mult: float = 1.0, **kwargs) -> AssetWallet:
        if not currency:
            currency = Commodity.instance("cash")
        val = self.value * currency.value * mult
        return AssetWallet({currency.uid: val})

    def buy(self, buyer,
             seller = None,
             currency: 'Commodity' = None,
             mult: float = 1.0, **kwargs):
        if not currency:
            currency = Commodity.instance("cash")
        buyer.send(self.price(currency, mult), seller)
        if seller:
            self.__discard_asset__( owner=seller )
        self.__add_asset__( owner=buyer )

    def sell(self, seller,
             buyer=None,
             currency: 'Commodity' = None,
             mult: float = 1.0, **kwargs):
        if not currency:
            currency = Commodity.instance("cash")
        seller.receive(self.price(currency, mult), buyer)
        if buyer:
            self.__add_asset__( owner=buyer )
        self.__discard_asset__( owner=seller )

    def __discard_asset__(self, **kwargs):
        return AssetType.__discard_asset__(self, **kwargs)

    def __add_asset__(self, **kwargs):
        return AssetType.__add_asset__(self, **kwargs)
