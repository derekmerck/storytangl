"""
Shared token substrate for game mechanics.

Game pieces are assets, not a parallel species. This module supplies the two
shapes the ladder needs and nothing else, both built on the existing asset
surface:

- :class:`FungibleGameToken` — interchangeable markers counted in an ordinary
  :class:`~tangl.story.concepts.asset.AssetWallet`. This is the **token rung**:
  advantage is carried by *how much* you hold.
- :class:`GameTokenType` plus :func:`discrete_token_class` — identity-bearing
  pieces as ordinary :class:`~tangl.core.Token` wrappers over a frozen
  definition, held in collections. This is the **named-token rung and above**:
  advantage is carried by *which* pieces you hold and, at the board rung, where
  they sit.

Using the canonical substrate rather than bespoke models is what lets game
pieces participate in registry ownership, selector queries, catalogs, and
``AssetTransactionManager`` transfers when a game is bound into a story graph —
and it is what makes it possible to reach into a running game from outside and
move, mark, or take a piece.

Tokens do not require a graph. A definition is a frozen singleton; a piece is a
node wrapping it with mutable ``instance_var`` state. Both work standalone, so
a game remains runnable as a plain library object.
"""
from __future__ import annotations

from collections import Counter
from typing import Type

from pydantic import Field

from tangl.core import Token
from tangl.core.singleton import Singleton
from tangl.story.concepts.asset import AssetType, AssetWallet, CountableAsset


class FungibleGameToken(CountableAsset):
    """Interchangeable game marker tracked by count in an asset wallet.

    Extends the fungible asset definition with an ``affiliation`` — the side,
    suit, colour, or force type a marker belongs to — which is the one grouping
    every token-rung contest needs and none of them should reinvent.
    """

    affiliation: str | None = None


class GameTokenType(AssetType):
    """Definition for an identity-bearing game piece.

    The frozen half of a discrete piece: what kind of thing it is. Mutable
    per-piece state belongs on fields marked ``instance_var``, which the token
    wrapper materializes.
    """

    affiliation: str | None = None


class DiscreteGameToken(Token):
    """Base wrapper for identity-bearing game pieces.

    Displays as its definition rather than its node label, matching the
    convention used by vehicle components and credential components.
    """

    def get_label(self) -> str:
        return self.token_from or self.label


def discrete_token_class(
    definition_cls: Type[Singleton],
    name: str,
    *,
    base: Type[Token] = DiscreteGameToken,
) -> Type[Token]:
    """Return the token wrapper class bound to a piece definition.

    Thin alias over the core wrapper cache so game modules declare pieces the
    same way assembly and credentials already do.
    """

    return base._create_wrapper_cls(definition_cls, name)


# ─────────────────────────────────────────────────────────────────────────────
# Wallet helpers for the token rung
# ─────────────────────────────────────────────────────────────────────────────


def value_by_affiliation(
    wallet: AssetWallet,
    *,
    token_cls: Type[FungibleGameToken] = FungibleGameToken,
) -> Counter:
    """Return total weighted value per affiliation held in a wallet."""

    totals: Counter = Counter()
    for label, count in wallet.items():
        if count <= 0:
            continue
        definition = token_cls.get_instance(label)
        if definition is None:
            continue
        totals[definition.affiliation] += definition.value * count
    return totals


def dominant_affiliation(
    wallet: AssetWallet,
    *,
    token_cls: Type[FungibleGameToken] = FungibleGameToken,
) -> str | None:
    """Return the affiliation carrying the most weighted value, or None.

    Ties resolve to the alphabetically first affiliation so that composition
    contests stay deterministic; a contest wanting a different tie rule should
    say so explicitly rather than depending on insertion order.
    """

    totals = value_by_affiliation(wallet, token_cls=token_cls)
    if not totals:
        return None
    best = max(totals.values())
    return sorted(label for label, value in totals.items() if value == best)[0]
