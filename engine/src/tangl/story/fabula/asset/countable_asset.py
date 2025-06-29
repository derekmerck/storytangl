from __future__ import annotations
from typing import TypeVar, Type, Optional
from collections import Counter

from pydantic import Field, field_validator

from tangl.type_hints import UniqueLabel
from tangl.core.entity import Entity
from tangl.core.services import on_gather_context, on_render_content
from .asset_type import AssetType

class CountableAsset(AssetType):
    """
    A CountableAsset or Fungible is an _unwrapped_ referent singleton
    that is associated with a story via a "Wallet" counter.

    Fungibles are bulk commodities such as cash, bulk food, etc. that
    have value and are counted or measured.

    Any node may become a fungible trader by mixing in the "HasWallet"
    class.  Wallets are keyed by the unique labels of the members of the
    Fungible or its subclasses.
    """
    value: float = 1.0
    units: str = "units"
    symbol: Optional[str] = None

    @classmethod
    def _as_label(cls, key: FungibleLike) -> UniqueLabel:
        if isinstance(key, UniqueLabel):
            return key
        elif isinstance(key, Fungible):
            return key.label
        raise TypeError(f"Unable to refer {type(key)} to label")

    @classmethod
    def _as_fungible(cls, key: FungibleLike) -> Fungible:
        if isinstance(key, Fungible):
            return key
        elif isinstance(key, UniqueLabel):
            return cls.get_instance(key, search_subclasses = True)
        raise TypeError(f"Unable to refer {type(key)} to label")

Fungible = CountableAsset

# common reference value for all worlds
cash = Fungible(label='cash',
                value=1.0,
                units='knots',
                symbol='ʞ$',
                text='the coin of the realm',
                icon="mdi-cash")

# todo: if we searched _up_ subclasses instead of down subclasses, we
#       could have a Fungible class in each domain with its own cash?
#       How do we handle different sets of assets in each world?

FungibleLike = Fungible | str  # Must dereference the string for the key
FungibleT = TypeVar("FungibleType", bound=Fungible)


class AssetWallet(Counter[CountableAsset]):
    """
    A wallet is a Counter, representing counts of Fungible assets.
    It provides linear functions like add, subtract and statistical aggregations.
    """

    def __getitem__(self, key: FungibleLike) -> float:
        key = Fungible._as_label(key)
        return super().__getitem__(key)

    def __setitem__(self, key: FungibleLike, value: float):
        key = Fungible._as_label(key)
        return super().__setitem__(key, value)

    def total_value(self) -> float:
        return sum( [ k.value * v for k, v in self.items() ] )

Wallet = AssetWallet


class WalletHandler():

    @classmethod
    def _validate_kwargs(cls, **kwargs):
        for k in kwargs:
            if not Fungible._as_fungible(k):
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
            raise RuntimeError(f"Wallet cannot accept gain of {kwargs}")
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
            raise RuntimeError(f"Wallet cannot cover loss of {kwargs}")
        wallet.update({k: -v for k, v in kwargs.items()})

    @classmethod
    def total_value(cls, wallet: Wallet) -> float:
        res = 0
        for k, count in wallet.items():
            nv = Fungible._as_fungible(k).value
            res += nv * count
        return res

    @classmethod
    def summary(cls, wallet: Wallet):
        contents = { k: v for k, v in wallet.items() if v > 0 }
        contents = sorted( contents.items(), key=lambda k, v: k.value * v )

        res = {
            'total_value': cls.total_value(wallet),
            'total_count': wallet.total(),
            'items': contents
        }
        return res

class HasAssetWallet(Entity):
    model_config = {'arbitrary_types_allowed': True}

    wallet: Counter[CountableAsset] = Field(default_factory=AssetWallet)

    @field_validator("wallet", mode="before")
    @classmethod
    def _convert_to_wallet(cls, data):
        if isinstance(data, Wallet):
            return data
        elif isinstance(data, (dict, Counter)):
            return Wallet(**data)

    def can_gain(self, **kwargs) -> bool:
        return WalletHandler.can_gain(self.wallet, **kwargs)

    def gain(self, **kwargs):
        WalletHandler.gain(self.wallet, **kwargs)

    def can_lose(self, **kwargs) -> bool:
        return WalletHandler.can_lose(self.wallet, **kwargs)

    def lose(self, **kwargs):
        WalletHandler.lose(self.wallet, **kwargs)

    def __getattr__(self, item):
        # delegate fungible name attrs to the wallet
        if x := self.wallet.__getitem__(item.lower()):
            return x
        return super().__getattr__(item)

    @on_gather_context.register()
    def _include_wallet_items(self, **kwargs):
        return self.wallet

    # # todo: should be "on describe" or something?
    # @on_render_content.register()
    # def _include_wallet_summary(self, **kwargs):
    #     return {'wallet': WalletHandler.summary(self.wallet)}
