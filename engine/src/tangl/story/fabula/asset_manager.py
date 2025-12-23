from __future__ import annotations

"""Asset management helpers for StoryTangl worlds."""

from pathlib import Path
from typing import TYPE_CHECKING, Any, Type

import yaml

from tangl.core import Graph
from tangl.core.graph import Token
from tangl.core.factory.token_factory import TokenFactory
from tangl.core.singleton import Singleton

from tangl.story.concepts.asset import AssetType, CountableAsset

if TYPE_CHECKING:
    from tangl.core.graph import Node


class AssetManager:
    """AssetManager()

    Registry for singleton asset definitions and helpers for token creation.

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
    * **Token factory** – :attr:`token_factory` resolves and wraps singleton bases
      into :class:`~tangl.core.graph.Token` nodes.

    API
    ---
    - :attr:`token_factory`
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

    def __init__(self, *, token_factory: TokenFactory | None = None) -> None:
        self.discrete_classes: dict[str, Type[AssetType]] = {}
        self.countable_classes: dict[str, Type[CountableAsset]] = {}
        self.token_factory = token_factory or TokenFactory(label="assets")

    def register_discrete_class(self, name: str, cls: Type[AssetType]) -> None:
        """Register a discrete asset class under ``name``."""

        self.discrete_classes[name] = cls
        self.token_factory.register_type(cls)

    def register_countable_class(self, name: str, cls: Type[CountableAsset]) -> None:
        """Register a countable asset class under ``name``."""

        self.countable_classes[name] = cls

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
    # Token TemplateFactory
    # ==================

    def create_token(
        self,
        asset_type: str | type[Singleton] | None = None,
        label: str | None = None,
        graph: Graph | None = None,
        *,
        token_type: str | type[Singleton] | None = None,
        overlay: dict[str, Any] | None = None,
        **overlay_kw: Any,
    ) -> Token | "Node":
        """Create a token by wrapping a registered singleton base."""

        token_type = token_type or asset_type
        if token_type is None or label is None:
            raise ValueError("token_type and label are required for token creation")

        resolved_type = self._resolve_token_type(token_type)
        if resolved_type is None:
            raise ValueError(f"Token type '{token_type}' is not registered")

        base = self.token_factory.resolve_base(resolved_type, label=label)
        if base is None:
            available = resolved_type.all_instance_labels()
            raise ValueError(
                f"No {resolved_type.__name__} base named '{label}'. Available: {available}"
            )

        token = self.token_factory.wrap(base, overlay=overlay, **overlay_kw)
        if graph is not None and token not in graph:
            graph.add(token)
        return token

    def has_token_base(self, token_type: str | type[Singleton], label: str) -> bool:
        """Return ``True`` when a base singleton exists for ``token_type`` and ``label``."""

        resolved_type = self._resolve_token_type(token_type)
        if resolved_type is None:
            return False
        return self.token_factory.resolve_base(resolved_type, label=label) is not None

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

    def _resolve_token_type(
        self,
        token_type: str | type[Singleton],
    ) -> type[Singleton] | None:
        if isinstance(token_type, type) and issubclass(token_type, Singleton):
            return token_type
        if isinstance(token_type, str):
            if token_type in self.discrete_classes:
                return self.discrete_classes[token_type]
            return self.token_factory.get_type(token_type)
        return None

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
