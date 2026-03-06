"""Countable asset type definitions."""

from __future__ import annotations

from typing import Optional

from tangl.core.singleton import InheritingSingleton


class CountableAsset(InheritingSingleton):
    """Fungible asset definition tracked by quantity.

    Why
    ==== 
    Provide a declarative singleton model describing fungible assets (gold, gems).

    API
    ===
    ``value``
        Base value of one unit of the asset.
    ``units``
        Display name for the units of the asset.
    ``symbol``
        Optional glyph used when rendering the asset.
    """

    value: float = 1.0
    """Base value of one unit."""

    units: str = "units"
    """Name for the asset's units."""

    symbol: Optional[str] = None
    """Display symbol for user interfaces."""


# Backward compatibility alias
Fungible = CountableAsset
