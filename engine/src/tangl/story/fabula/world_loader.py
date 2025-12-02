from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from tangl.loaders import WorldBundle, WorldCompiler
from tangl.service.world_registry import WorldRegistry

logger = logging.getLogger(__name__)


class WorldLoader(WorldRegistry):
    """Backward-compatible alias that delegates to :class:`WorldRegistry`."""

    def __init__(self, world_dirs: list[Path] | None = None) -> None:
        super().__init__(world_dirs=world_dirs, compiler=WorldCompiler())

    def discover_bundles(self) -> dict[str, WorldBundle]:
        return self.bundles

    def load_world(self, world_id: str, **_kwargs: Any):
        return self.get_world(world_id)
