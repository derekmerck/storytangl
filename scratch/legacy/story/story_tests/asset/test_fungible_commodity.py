
from collections import Counter

from tangl.story.asset import Asset, Wallet, Commodity, HasWallet

from tests.conftest import TEST_WORLD_PATH
import pytest




def test_transactions():

    from tangl.story.asset.commodity import cash
    diamonds = Commodity( uid="diamonds", value=1000 )

    buyer = Wallet( cash=10 )
    seller = Wallet( diamonds=10 )

    print( buyer )
    print( seller )

    assert buyer.can_afford( cash=5 )
    assert not buyer.can_afford( diamonds=1 )

    buyer['diamonds'] += 1
    assert buyer.can_afford( diamonds=1 )

    buyer.transact( to_send={ 'cash': 10 }, to_receive={ 'diamonds': 1 }, other=seller)

    print( buyer )
    print( seller )

    assert buyer['cash'] == 0
    assert seller['cash'] == 10
    assert buyer['diamonds'] == 2  # added one above
    assert seller['diamonds'] == 9

    buyer.receive( cash=100 )
    print( buyer )
    assert buyer['cash'] == 100

    with pytest.raises(ValueError):
        seller.send( diamonds=10000, other=buyer )

#
# from tangl.utils.singleton import SingletonsManager
#
# def test_asset_manager():
#
#     s = SingletonsManager()
#     s.add_singletons_cls( Unit )
#     s.add_singletons_cls( Commodity )
#     s.new_instance("Unit", uid="paper", utility=10, move_typ="paper" )
#     u = s.instance("paper")
#     print( Unit._instances.keys() )
#     print( u )
#
#     t = SingletonsManager()
#     t.add_singletons_cls( Unit )
#     print( Unit._instances.keys() )
#     with pytest.raises(KeyError):
#         uu = t.instance("paper")
#         print( uu )


def test_asset_wallet_proxy():

    from tangl.world.world import World
    wo = World.load(TEST_WORLD_PATH)

    ctx = wo.new_context( globals={'cash': 100} )

    with WalletProxy( ctx.globals ) as wallet:
        print( wallet )
        assert wallet["cash"] == 100
        wallet += {"cash": 100}
        print( wallet )
        assert wallet['cash'] == 200

    print( ctx.globals )
    assert ctx.globals["cash"] == 200

    Commodity(uid='cat')

    with WalletProxy( ctx.globals ) as wallet:
        wallet.send( {'cash': 100} )
        wallet.receive( {'cat': 100 })
        print( wallet )

    assert ctx.globals['cash'] == 100
    assert ctx.globals['cat'] == 100
    print( ctx.globals )


if __name__ == "__main__":
    # test_transactions()
    # test_asset_manager()
    pass