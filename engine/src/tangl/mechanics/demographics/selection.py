"""Bounded name-bank offers and origin selection, without global fallback.

Catalog composition happens before a world publishes its catalogs. Runtime lookup
uses the ordinary Selector/TokenCatalog mechanisms and rejects ambiguous offers.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from random import Random
from typing import Annotated

from pydantic import Field

from tangl.core import Selector, TokenCatalog
from tangl.core.bases import Unstructurable

from .data_models import NameBank


class Origin(Unstructurable):
    """An authored origin identity and explicit mixture of local bank references."""

    label: str = Field(min_length=1)
    banks: dict[str, Annotated[float, Field(ge=0, allow_inf_nan=False, strict=True)]] = Field(
        min_length=1,
    )


@dataclass(frozen=True)
class NameSelection:
    """Ephemeral selection receipt; actor provenance ownership is a later slice."""

    origin: Origin
    bank: NameBank


def name_catalog(
    *catalogs: TokenCatalog[NameBank],
    overrides: Sequence[NameBank] = (),
) -> TokenCatalog[NameBank]:
    """Compose explicit base offers and explicit replacements by local naming key.

    Conflicting base offers or repeated override keys are declaration errors.
    Replaced definitions are absent from the returned catalog, even by internal id.
    No source catalog or shared definition is changed.
    """
    offers: dict[str, NameBank] = {}
    for bank in TokenCatalog.chain_find_all(*catalogs):
        key = bank.selection_key or bank.label
        if key in offers and offers[key] is not bank:
            raise ValueError(f"Ambiguous base naming key: {key!r}")
        offers[key] = bank
    override_keys: set[str] = set()
    for bank in overrides:
        key = bank.selection_key or bank.label
        if key in override_keys:
            raise ValueError(f"Repeated naming override key: {key!r}")
        override_keys.add(key)
        offers[key] = bank
    return TokenCatalog(
        NameBank,
        members=tuple(sorted(offers.values(), key=lambda bank: bank.label)),
        label="names",
    )


def select_bank(
    ref: str | Selector | NameBank,
    *,
    catalogs: Sequence[TokenCatalog[NameBank]],
    rng: Random | None = None,
) -> NameBank:
    """Resolve an exact scoped reference or uniformly choose eligible definitions."""
    selector = (
        ref if isinstance(ref, Selector) else Selector(
            has_identifier=ref.uid if isinstance(ref, NameBank) else ref,
        )
    )
    candidates = {
        (type(bank), bank.label): bank
        for catalog in catalogs
        if catalog.has_kind(NameBank)
        for bank in catalog.find_all(selector)
    }
    ordered = sorted(
        candidates.values(),
        key=lambda bank: (bank.label, type(bank).__module__, type(bank).__qualname__),
    )
    if not ordered:
        raise LookupError(f"No eligible NameBank in supplied catalogs for {ref!r}")
    if not isinstance(ref, Selector):
        if len(ordered) > 1:
            raise ValueError(f"Ambiguous NameBank reference in supplied catalogs: {ref!r}")
        return ordered[0]
    if rng is None:
        raise ValueError("Selector bank selection requires an explicit RNG")
    return rng.choice(ordered)


def select_origin(
    origin: Origin,
    *,
    catalogs: Sequence[TokenCatalog[NameBank]],
    rng: Random,
) -> NameSelection:
    """Resolve every declared reference, then draw from positive-weight offers."""
    eligible: list[tuple[NameBank, float]] = []
    for ref, weight in sorted(origin.banks.items()):
        bank = select_bank(ref, catalogs=catalogs, rng=rng)
        if weight > 0:
            eligible.append((bank, weight))
    if not eligible:
        raise ValueError(f"Origin {origin.label!r} has no positive eligible bank weight")
    # Scaling prevents overflow of otherwise valid finite individual weights.
    scale = max(weight for _bank, weight in eligible)
    selected = rng.choices(
        [bank for bank, _weight in eligible],
        weights=[weight / scale for _bank, weight in eligible],
        k=1,
    )[0]
    return NameSelection(origin=origin, bank=selected)
