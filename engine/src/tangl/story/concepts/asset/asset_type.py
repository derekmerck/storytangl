from __future__ import annotations

from typing import Any

from pydantic import Field

from tangl.core.singleton import InstanceInheritance


class AssetType(InstanceInheritance):
    """Story-level singleton definition for tokenizable assets.

    Asset types describe the platonic item or resource. Discrete assets become
    graph-local state by wrapping an ``AssetType`` subclass with ``Token[...]``;
    fungible assets use :class:`CountableAsset` and live in an
    :class:`AssetWallet`.
    """

    value: float = 0.0
    description: str | None = None
    traits: set[str] = Field(default_factory=set)

    def __init__(
        self,
        *,
        label: str,
        inherit_from: str | None = None,
        from_ref: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            label=label,
            inherit_from=inherit_from or from_ref,
            **kwargs,
        )

    def describe(self) -> str:
        """Return narrative-facing description text for this asset type."""
        return self.description or self.label

    @property
    def text(self) -> str:
        """Legacy-friendly short description surface."""
        return self.describe()


class CountableAsset(AssetType):
    """Fungible asset definition tracked by count in an asset wallet."""

    value: float = 1.0
    units: str = "units"
    symbol: str | None = Field(default=None)


Fungible = CountableAsset
