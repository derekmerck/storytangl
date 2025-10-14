from __future__ import annotations

"""Asset management helpers for StoryTangl worlds."""

from collections.abc import Iterable
from pathlib import Path

from tangl.core.graph.graph import Graph

from .asset_type import AssetType
from .discrete_asset import DiscreteAsset


class AssetManager:
    """AssetManager()

    Registry for singleton asset definitions and helpers to spawn graph tokens.

    Why
    ---
    Scripts refer to asset types (e.g. wearables, tokens) by string keys. The
    :class:`AssetManager` keeps a mapping between those keys and their
    :class:`AssetType` subclasses so instances can be materialized at runtime.

    Key Features
    ------------
    * **Registration** – :meth:`register_asset_class` binds a label to an
      :class:`AssetType` subclass.
    * **Loading** – :meth:`load_from_file` and :meth:`load_from_data` populate
      singleton instances from serialized data.
    * **Token factory** – :meth:`create_token` wraps an asset singleton in a
      :class:`~tangl.story.fabula.asset.discrete_asset.DiscreteAsset` node tied to
      a :class:`~tangl.core.graph.graph.Graph`.

    API
    ---
    - :meth:`register_asset_class`
    - :meth:`load_from_file`
    - :meth:`load_from_data`
    - :meth:`create_token`
    - :meth:`get_asset_type`
    """

    def __init__(self) -> None:
        self.asset_classes: dict[str, type[AssetType]] = {}

    def register_asset_class(self, name: str, cls: type[AssetType]) -> None:
        """Register ``cls`` under ``name`` for later lookup."""
        self.asset_classes[name] = cls

    def _get_asset_cls(self, asset_type: str) -> type[AssetType]:
        try:
            return self.asset_classes[asset_type]
        except KeyError as exc:  # pragma: no cover - defensive
            raise KeyError(f"No asset class registered for '{asset_type}'") from exc

    def load_from_file(self, asset_type: str, filepath: Path) -> None:
        """Load asset instances from ``filepath`` via the registered class."""
        cls = self._get_asset_cls(asset_type)
        if hasattr(cls, "load_instances"):
            cls.load_instances(filepath)  # type: ignore[misc]
            return
        if hasattr(cls, "load_instances_from_yaml"):
            cls.load_instances_from_yaml(filepath)  # type: ignore[misc]
            return
        raise AttributeError(
            f"Asset class {cls.__name__} does not support loading from file"
        )

    def load_from_data(self, asset_type: str, data: Iterable[dict]) -> None:
        """Instantiate assets from iterable ``data`` dictionaries."""
        cls = self._get_asset_cls(asset_type)
        for item_data in data:
            cls(**dict(item_data))

    def create_token(self, asset_type: str, label: str, graph: Graph) -> DiscreteAsset:
        """Create a graph-bound discrete asset node."""
        cls = self._get_asset_cls(asset_type)
        wrapper_cls = DiscreteAsset[cls]
        return wrapper_cls(label=label, graph=graph)

    def get_asset_type(self, asset_type: str, label: str) -> AssetType:
        """Retrieve the singleton asset definition for ``label``."""
        cls = self._get_asset_cls(asset_type)
        asset = cls.get_instance(label)
        if asset is None:  # pragma: no cover - defensive
            raise KeyError(f"No instance '{label}' for asset type '{asset_type}'")
        return asset
