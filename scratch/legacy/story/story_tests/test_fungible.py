import pytest
from collections import Counter

from tangl.story.asset.fungible import HasWallet, WalletHandler, Fungible

@pytest.fixture(autouse=True)
def _clear_fungible():
    # todo: need a better solution for sharing the 'cash' reference fungible across worlds
    Fungible.clear_instances()
    cash = Fungible(label='cash',
                    value=1.0,
                    units='horns',
                    symbol='Ɐ$',
                    text='the coin of the realm',
                    icon="mdi-cash")


def test_fungible():

    cash = Fungible.get_instance('cash')
    print( cash )
    assert cash


def test_validate_kwargs():
    # Valid case
    WalletHandler._validate_kwargs(cash=100)

    # Invalid case
    with pytest.raises(KeyError):
        WalletHandler._validate_kwargs(non_existent_fungible=100)


def test_gain_lose_wallet():
    wallet = Counter()
    WalletHandler.gain(wallet, cash=100)
    assert wallet['cash'] == 100

    WalletHandler.lose(wallet, cash=50)
    assert wallet['cash'] == 50

    # Test exception when trying to lose more than the wallet contains
    with pytest.raises(RuntimeError):
        WalletHandler.lose(wallet, cash=100)


def test_total_value():
    wallet = Counter(cash=100)
    assert WalletHandler.total_value(wallet) == 100


def test_has_wallet_integration():
    hw = HasWallet()
    hw.gain(cash=200)
    assert hw.wallet['cash'] == 200

    hw.lose(cash=150)
    assert hw.wallet['cash'] == 50

    # Check if HasWallet can_lose and can_gain delegate correctly
    assert hw.can_gain(cash=50)
    assert not hw.can_lose(cash=100)

    hhw = HasWallet(wallet={'cash': 50})
    assert hhw.wallet['cash'] == 50

    print(hhw.model_dump())

    assert hhw.model_dump() == {'wallet': {'cash': 50}}


def test_fungible():

    a = Fungible(label="my_fungible", value=10)
    assert( a.value == 10 )

    # hashable
    A = { a }

    w = Counter()

    w["my_fungible"] = 10
    assert( WalletHandler.total_value(w) == 100 )

    w["cash"] += 10
    assert( WalletHandler.total_value(w) == 110 )


def test_fungible_commodity():

    w = Counter( cash=10 )
    print( w.total() )

    dog = Fungible( label="dog", value=100 )
    w['dog'] = 5

    print( w.total() )  # total items
    # print( w.total( "value" ) )  # total value

    assert w >= Counter( dog=0 )
    assert w == Counter( cash=10, dog=5 )
    assert w != Counter( cash=11, dog=4 )
    assert w <= Counter( cash=100, dog=10 )
    assert not w <= Counter( cash=100 )


# def test_fungible_commodity2():
#
#     d = {"cash": 100}
#     with WalletProxy( d ) as wallet:
#         wallet += { 'cash': 1000 }
#
#     assert d['cash'] == 1100
#
#     print( +w )
#     assert( isinstance(+w, Wallet) )
#     print( -w )
#     assert( isinstance(-w, Wallet) )
#
#     print( w+w )
#     assert( isinstance( w+w, Wallet ))
#
#     print( w-w )
#     assert( isinstance( w-w, Wallet ))
#     assert( not w-w )
#
#     print( w // 2 )
#     print( w * 2.5 )
