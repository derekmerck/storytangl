from __future__ import annotations

"""Asset management helpers for StoryTangl worlds."""

from pathlib import Path
from typing import Type

import yaml

from tangl.core import Graph

from tangl.story.concepts.asset import AssetType, CountableAsset, DiscreteAsset


class AssetManager:
    """AssetManager()

    Registry for singleton asset definitions and helpers to spawn graph tokens.

    Why
    ---
    Worlds load their asset definitions (weapons, items, currencies) from data
    files. The :class:`AssetManager` keeps those classes organised by category,
    offers helpers to hydrate singleton definitions, and creates discrete asset
    tokens that live in a :class:`~tangl.core.Graph`.

    Key Features
    ------------
    * **Registration** – :meth:`register_discrete_class` and
      :meth:`register_countable_class` bind category names to their implementation
      classes.
    * **Loading** – :meth:`load_discrete_from_yaml`,
      :meth:`load_countable_from_yaml`, and their ``*_from_data`` variants populate
      singletons from structured input.
    * **Token factory** – :meth:`create_token` wraps an asset singleton in a
      :class:`~tangl.story.concepts.asset.DiscreteAsset` node bound to a
      :class:`~tangl.core.Graph` instance.

    API
    ---
    - :meth:`register_discrete_class`
    - :meth:`register_countable_class`
    - :meth:`load_discrete_from_yaml`
    - :meth:`load_discrete_from_data`
    - :meth:`load_countable_from_yaml`
    - :meth:`load_countable_from_data`
    - :meth:`create_token`
    - :meth:`get_discrete_type`
    - :meth:`get_countable_type`
    - :meth:`list_discrete`
    - :meth:`list_countable`
    """

    def __init__(self) -> None:
        self.discrete_classes: dict[str, Type[AssetType]] = {}
        self.countable_classes: dict[str, Type[CountableAsset]] = {}
        self.asset_classes: dict[
            str, Type[AssetType] | Type[CountableAsset]
        ] = {}

    # ==================
    # Registration
    # ==================

    def register_discrete_class(self, name: str, cls: Type[AssetType]) -> None:
        """Register a discrete asset class under ``name``."""

        self.discrete_classes[name] = cls
        self.asset_classes[name] = cls

    def register_countable_class(self, name: str, cls: Type[CountableAsset]) -> None:
        """Register a countable asset class under ``name``."""

        self.countable_classes[name] = cls
        self.asset_classes[name] = cls

    # Backwards compatibility -------------------------------------------------

    def register_asset_class(
        self,
        name: str,
        cls: Type[AssetType] | Type[CountableAsset],
    ) -> None:
        """Alias for :meth:`register_discrete_class` and countable variants."""

        if issubclass(cls, CountableAsset):
            self.register_countable_class(name, cls)
        else:
            self.register_discrete_class(name, cls)

    # ==================
    # Loading
    # ==================

    def load_discrete_from_yaml(self, asset_type: str, filepath: Path) -> int:
        """Load discrete asset definitions from ``filepath``."""

        cls = self._get_discrete_class(asset_type)
        entries = self._read_yaml_entries(filepath)
        count = 0
        for item in entries:
            cls(**item)
            count += 1
        return count

    def load_countable_from_yaml(self, asset_type: str, filepath: Path) -> int:
        """Load countable asset definitions from ``filepath``."""

        cls = self._get_countable_class(asset_type)
        entries = self._read_yaml_entries(filepath)
        count = 0
        for item in entries:
            cls(**item)
            count += 1
        return count

    def load_discrete_from_data(self, asset_type: str, data: list[dict]) -> int:
        """Load discrete assets from ``data`` dictionaries."""

        cls = self._get_discrete_class(asset_type)
        count = 0
        for item in data:
            cls(**item)
            count += 1
        return count

    def load_countable_from_data(self, asset_type: str, data: list[dict]) -> int:
        """Load countable assets from ``data`` dictionaries."""

        cls = self._get_countable_class(asset_type)
        count = 0
        for item in data:
            cls(**item)
            count += 1
        return count

    def load_assets_from_file(self, asset_type: str, filepath: Path | str) -> int:
        """Compatibility wrapper for legacy APIs."""

        path = Path(filepath)
        if asset_type in self.discrete_classes:
            return self.load_discrete_from_yaml(asset_type, path)
        if asset_type in self.countable_classes:
            return self.load_countable_from_yaml(asset_type, path)
        raise KeyError(f"No asset class registered for '{asset_type}'")

    def load_from_yaml(self, asset_type: str, filepath: Path | str) -> int:
        """Alias for :meth:`load_assets_from_file`."""

        return self.load_assets_from_file(asset_type, filepath)

    def load_from_data(self, asset_type: str, data: list[dict]) -> int:
        """Alias dispatching to discrete or countable loaders."""

        if asset_type in self.discrete_classes:
            return self.load_discrete_from_data(asset_type, data)
        if asset_type in self.countable_classes:
            return self.load_countable_from_data(asset_type, data)
        raise KeyError(f"No asset class registered for '{asset_type}'")

    # ==================
    # Token Factory
    # ==================

    def create_token(
        self,
        asset_type: str,
        label: str,
        graph: Graph,
        **instance_vars: object,
    ) -> DiscreteAsset:
        """Create a discrete asset token for ``label`` within ``graph``."""

        cls = self._get_discrete_class(asset_type)
        if cls.get_instance(label) is None:
            available = cls.all_instance_labels()
            raise ValueError(
                f"No {asset_type} asset named '{label}'. Available: {available}"
            )

        wrapper_cls = DiscreteAsset[cls]
        return wrapper_cls(label=label, graph=graph, **instance_vars)

    # ==================
    # Lookup
    # ==================

    def get_discrete_type(self, asset_type: str, label: str) -> AssetType:
        """Return the discrete asset singleton for ``label``."""

        cls = self._get_discrete_class(asset_type)
        asset = cls.get_instance(label)
        if asset is None:
            raise KeyError(f"No {asset_type} instance '{label}'")
        return asset

    def get_countable_type(self, asset_type: str, label: str) -> CountableAsset:
        """Return the countable asset singleton for ``label``."""

        cls = self._get_countable_class(asset_type)
        asset = cls.get_instance(label)
        if asset is None:
            raise KeyError(f"No {asset_type} instance '{label}'")
        return asset

    def get_asset_type(
        self,
        asset_type: str,
        label: str,
    ) -> AssetType | CountableAsset:
        """Compatibility wrapper combining discrete and countable lookups."""

        if asset_type in self.discrete_classes:
            return self.get_discrete_type(asset_type, label)
        if asset_type in self.countable_classes:
            return self.get_countable_type(asset_type, label)
        raise KeyError(f"No asset class registered for '{asset_type}'")

    def list_discrete(self, asset_type: str) -> list[str]:
        """List singleton labels for the discrete ``asset_type``."""

        cls = self._get_discrete_class(asset_type)
        return cls.all_instance_labels()

    def list_countable(self, asset_type: str) -> list[str]:
        """List singleton labels for the countable ``asset_type``."""

        cls = self._get_countable_class(asset_type)
        return cls.all_instance_labels()

    # ==================
    # Internal helpers
    # ==================

    def _get_discrete_class(self, asset_type: str) -> Type[AssetType]:
        try:
            return self.discrete_classes[asset_type]
        except KeyError as exc:  # pragma: no cover - defensive
            raise KeyError(
                f"No discrete asset class registered for '{asset_type}'"
            ) from exc

    def _get_countable_class(self, asset_type: str) -> Type[CountableAsset]:
        try:
            return self.countable_classes[asset_type]
        except KeyError as exc:  # pragma: no cover - defensive
            raise KeyError(
                f"No countable asset class registered for '{asset_type}'"
            ) from exc

    @staticmethod
    def _read_yaml_entries(filepath: Path) -> list[dict]:
        with filepath.open(encoding="utf-8") as stream:
            raw = yaml.safe_load(stream) or []

        if isinstance(raw, dict):
            return [raw]
        if isinstance(raw, list):
            return [dict(item) for item in raw]

        raise TypeError(
            f"Unsupported YAML structure in '{filepath}': expected dict or list"
        )
