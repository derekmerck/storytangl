from __future__ import annotations
from enum import Enum
from typing import *
from collections import Counter

from pydantic import Field

from tangl.story.concepts.asset import CountableAsset as Fungible, AssetWallet as Wallet

WalletHandler = object
HasWallet = object

Affiliation = str | Enum
# todo: affiliation should be like "move" in game handler?

class Token(Fungible):
    """
    Tokens are fungible assets that can be grouped and aggregated
    by type, specifically to be used in game.

    Extends fungible, which only has name and value, with an enumerated
    affiliation, e.g., "Red" or "Blue".
    """
    affiliation: Affiliation

Token.load_instances_from_yaml('tangl.mechanics.game.token_games.resources', 'tokens.yaml')


class TokenHandler(WalletHandler):
    """
    A token bag is a wallet for tokens.
    """

    @classmethod
    def value_by_affiliation(cls, bag: Wallet) -> Counter:
        token_cls = getattr(bag, 'token_cls', Token)
        res = Counter()
        for k, v in bag.items():
            f = token_cls.get_instance(k)
            res[f.affiliation] += f.value * v
        return res

    @classmethod
    def dominant_affiliation(cls, bag: Wallet) -> Enum:
        token_cls = getattr(bag, 'token_cls', Token)
        res = cls.value_by_affiliation(bag, token_cls)
        cand = res.most_common()
        # sort by total power desc (10 > 5 > 1)
        cand.sort(key=lambda x: x[1], reverse=True)
        return cand[0][0]

    @classmethod
    def summary(cls, bag: Wallet):
        token_cls = getattr(bag, 'token_cls', Token)
        contents = { k: v for k, v in bag.items() if v > 0 }
        contents = sorted( contents.items(), key=lambda k, v: k.value * v )

        res = {
            'total_power': cls.total_value(bag),
            'total_count': bag.total(),
            'dominant_affiliation': cls.dominant_affiliation(bag, token_cls),
            'items': contents
        }
        return res

TokenType = TypeVar('TokenType', bound=Token)


class Bag(Wallet, Generic[Type[TokenType]]):
    token_cls: ClassVar[Type[TokenType]] = Token


class HasTokens(HasWallet, Generic[Type[TokenType]]):

    wallet: Bag[Type[TokenType]] = Field(..., alias="bag")

    # may want to include a "Bag" class that tracks contained token type?

    def value_by_affiliation(self) -> Counter:
        return TokenHandler.value_by_affiliation(self.wallet)

    def dominant_affiliation(self) -> Affiliation:
        return TokenHandler.dominant_affiliation(self.wallet)
