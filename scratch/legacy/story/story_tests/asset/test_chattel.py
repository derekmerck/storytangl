
import attr

from tangl.asset import Wallet, ChattelMixin
from tangl.actor import Actor

import pytest

@attr.define
class Chattel( ChattelMixin, Actor ):

    @property
    def value(self) -> float:
        return 100

def test_chattel():

    buyer = Wallet( cash=100 )
    buyer.assets = []
    buyer.__gain__ = lambda x: buyer.assets.append( x )
    assert buyer['cash'] == 100
    print( "buyer", buyer )

    seller = Wallet()
    seller.assets = []
    seller.__gain__ = lambda x: seller.assets.append( x )
    seller.__discard__ = lambda x: seller.assets.remove( x )

    ch = Chattel()
    seller.__gain__( ch )

    ch.price()
    assert( ch in seller.assets )

    ch.buy(buyer, seller )

    print( buyer, buyer.assets )
    print( seller, seller.assets )

    assert( ch in buyer.assets and ch not in seller.assets )
    assert buyer['cash'] == 0
    assert seller['cash'] == 100


if __name__ == "__main__":
    test_chattel()
