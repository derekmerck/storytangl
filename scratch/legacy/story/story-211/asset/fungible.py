from __future__ import annotations
from numbers import Number
from collections import Counter
from enum import Enum
from typing import Optional, ClassVar, Type

from pydantic import BaseModel, Field

from tangl.type_hints import UniqueLabel
from tangl.exceptions import TradeHandlerError
from tangl.story.asset import AssetType

Wallet = Counter[UniqueLabel]


class Fungible(AssetType):
    """
    Fungibles are bulk commodities such as cash, bulk food, etc. that
    have value and are counted.

    Any node may become a fungible trader by mixing in the "HasWallet"
    class.  Wallets are keyed by the unique labels of the members of the
    Fungible singleton subclass associated with the class's wallet handler.
    """
    # inherits label, text, icon, hash
    value: float = 1.0


class FungibleCommodity(Fungible):

    _instances = Fungible._instances

    units: str = "units"
    symbol: Optional[str] = None


cash = FungibleCommodity(label='cash',
                         units='horns',
                         symbol='Ɐ$',
                         text='the coin of the realm',
                         icon="mdi-cash")

class WalletHandler:

    fungible_cls: ClassVar[Type[Fungible]] = Fungible

    @classmethod
    def _validate_kwargs(cls, **kwargs):
        for k in kwargs:
            if k not in cls.fungible_cls._instances:
                raise TypeError(f"Cannot use {k} with wallet, no such Fungible")

    @classmethod
    def can_gain(cls,
                 wallet: Wallet,
                 **kwargs) -> bool:
        # Trivial implementation, override to create max limits on wallets
        cls._validate_kwargs(**kwargs)
        return True

    @classmethod
    def gain(cls,
             wallet: Wallet,
             **kwargs):
        if not cls.can_gain(wallet, **kwargs):
            raise TradeHandlerError(f"Wallet cannot accept gain of {kwargs}")
        wallet.update(kwargs)

    @classmethod
    def can_lose(cls,
                 wallet: Wallet,
                 **kwargs) -> bool:
        cls._validate_kwargs(**kwargs)
        if wallet >= Counter(kwargs):
            return True
        return False

    @classmethod
    def lose(cls,
             wallet: Wallet,
             **kwargs):
        if not cls.can_lose(wallet, **kwargs):
            raise TradeHandlerError(f"Wallet cannot cover loss of {kwargs}")
        wallet.update({k: -v for k, v in kwargs.items()})

    @classmethod
    def total_value(cls, wallet: Wallet, fungible_cls: Type[Fungible] = None) -> Number:
        fungible_cls = fungible_cls or cls.fungible_cls
        res = 0
        for k, count in wallet.items():
            nv = fungible_cls.get_instance(k).value
            res += nv * count
        return res

    @classmethod
    def render(cls, wallet: Wallet):
        contents = { k: v for k, v in wallet.items() if v > 0 }
        contents = sorted( contents.items(), key=lambda k, v: k.value * v )

        res = {
            'total_value': cls.total_value(wallet),
            'total_count': wallet.total(),
            'items': contents
        }
        return res


class HasWallet(BaseModel):
    """
    A wallet is a wrapped Counter, representing counts of Fungible assets.
    It provides linear functions like add, subtract and statistical aggregations.
    """

    wallet_handler: ClassVar[Type[WalletHandler]] = WalletHandler
    wallet: Counter = Field(default_factory=Counter, validate_default=True)

    def can_gain(self, **kwargs) -> bool:
        return self.wallet_handler.can_gain(self.wallet, **kwargs)

    def gain(self, **kwargs):
        self.wallet_handler.gain(self.wallet, **kwargs)

    def can_lose(self, **kwargs) -> bool:
        return self.wallet_handler.can_lose(self.wallet, **kwargs)

    def lose(self, **kwargs):
        self.wallet_handler.lose(self.wallet, **kwargs)

    def __getattr__(self, item):
        # delegate fungible name attrs to the wallet
        _item = item
        if isinstance(item, Enum):
            _item = item.name
        if isinstance(_item, str):
            _item = _item.lower()
        if x := self.wallet.get(_item):
            return x
        return super().__getattr__(item)

    def render(self):
        return {'wallet': self.wallet_handler.render(self.wallet)}
