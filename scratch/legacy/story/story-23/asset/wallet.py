from typing import *
from collections import defaultdict
from pprint import pformat

from .asset import AssetType

Counterlike = TypeVar( "Counterlike", bound=dict )

class AssetWallet( Counter ):

    def __init__(self, *args, **kwargs):
        if "asset_base" in kwargs:
            self.asset_base = kwargs.pop("asset_base")
        else:
            self.asset_base = AssetType
        super().__init__(*args, **kwargs)

    def total_utility(self, asset_typ: str = None) -> Union[dict[str, int], int]:
        """Could be cost, power, whatever"""
        res = defaultdict( int )
        for asset_uid, asset_count in self.items():
            asset = self.asset_base.instance( asset_uid )
            res[ asset.__class__.__name__ ] += asset_count * asset.utility
        if asset_typ:
            return res[asset_typ]
        return dict( res )

    def summary(self) -> dict[str, dict]:
        res = defaultdict( dict )
        for asset_uid, asset_count in self.items():
            asset = self.asset_base.instance( asset_uid )
            res[asset.__class__.__name__][asset_uid] = asset_count
        return dict( res )

    def __repr__(self):
        # return Counter.__repr__(self)
        return pformat( self.summary() )

    def can_afford(self, price: Optional["AssetWallet"] = None, **kwargs):
        if not price and kwargs:
            price = AssetWallet( **kwargs )
        return self >= price

    def send(self, assets: Counterlike = None,
             other: Optional["AssetWallet"] = None, **kwargs):
        if not isinstance(assets, AssetWallet):
            if not assets:
                assets = kwargs
            assets = AssetWallet( assets )
        # print( "sending", assets)
        if self.can_afford(assets):
            self.subtract( assets )
            if other is not None:
                other.update( assets )
            return True
        raise ValueError("Source has insufficient resources to send")

    def receive(self, assets: Counterlike = None,
                other: Optional["AssetWallet"] = None, **kwargs):
        if not isinstance(assets, AssetWallet):
            if not assets:
                assets = kwargs
            assets = AssetWallet( assets )
        # print( "receiving", assets)
        if other is None or other.can_afford(assets):
            self.update( assets )
            if other is not None:
                other.subtract( assets )
            return True
        raise ValueError("Receiver has insufficient resources to send")

    def transact(self, to_send: Counterlike, to_receive: Counterlike, other: "AssetWallet"):
        self.send( to_send, other )
        self.receive( to_receive, other )

    def __mul__(self, other: float) -> 'AssetWallet':
        res = AssetWallet( self )
        for k, v in res.items():
            res[k] = v*other
        return res

    def __ge__(self, other: Counterlike):
        for k, v in other.items():
            if self[k] < other[k]:
                return False
        return True

class ProxyWallet(AssetWallet, ContextManager):
    """
    seller = Hub( assets=assets )
    with ProxyWallet( ctx.player ) as buyer:
        buyer.buy( seller, assets )
    """
    def __init__(self, ref_data: dict, **kwargs):
        self.ref_data = ref_data
        super().__init__(**kwargs)

    def __enter__(self):

        # data = {}
        # print( self.ctx.world.asset_manager._singletons_types )
        # for at in self.ctx.world.asset_manager._singletons_types.values():
        #     print( at )
        #     _data = {k: v for k, v in self.ctx.globals.items() if k in at.keys()}
        #     data |= _data
        # print( data )

        # todo: IMPORTANT - needs fixed to work with world-managed assets
        from tangl.asset import Commodity
        self.asset_base = Commodity
        data = { k: v for k, v in self.ref_data.items()
                 if k in self.asset_base._instances.keys() }
        self.update( data )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # push updates back into globals
        self.ref_data.update( self )


