from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class MediaCompiler:
    """Index media directories into a resource manager when available."""

    def index(
        self,
        media_dir: Path,
        organization_hints: dict | None = None,
    ):
        try:
            from tangl.media.media_resource.resource_manager import ResourceManager
        except ModuleNotFoundError:  # pragma: no cover - optional dependency
            logger.warning("Media support not available")
            return None

        if not media_dir.exists():
            return None

        resource_manager = ResourceManager(resource_path=media_dir)

        if organization_hints:
            for subdir, _config in organization_hints.items():
                subdir_path = media_dir / subdir
                if subdir_path.exists():
                    resource_manager.index_directory(subdir, tags={f"category:{subdir}"})
        else:
            resource_manager.index_directory(".")

        return resource_manager
