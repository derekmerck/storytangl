from __future__ import annotations

from typing import Any, Optional

from pydantic import Field

from tangl.type_hints import Identifier
from tangl.vm.provision import ProvisioningPolicy, Requirement
from tangl.media.media_resource import MediaResourceInventoryTag as MediaRIT


class MediaRequirement(Requirement[MediaRIT]):
    """Requirement for media resources using path-only templates."""

    media_path: Optional[str] = None
    media_role: str = "narrative_im"
    world_id: Optional[str] = None
    media_provider: MediaRIT | None = Field(default=None, exclude=True)

    def model_post_init(self, __context: Any) -> None:
        super().model_post_init(__context)
        template = self.template or {}
        if isinstance(template, dict):
            self.media_path = template.get("media_path", self.media_path)
            self.media_role = template.get("media_role", self.media_role)
            self.world_id = template.get("world_id", self.world_id)

    @property
    def provider(self) -> MediaRIT | None:  # type: ignore[override]
        return self.media_provider

    @provider.setter
    def provider(self, value: MediaRIT | None) -> None:  # type: ignore[override]
        self.media_provider = value
        self.provider_id = getattr(value, "uid", None)

    @classmethod
    def for_path(
        cls,
        *,
        graph,
        media_path: str,
        media_role: str = "narrative_im",
        world_id: Optional[str] = None,
        policy: ProvisioningPolicy = ProvisioningPolicy.ANY,
        identifier: Optional[Identifier] = None,
    ) -> "MediaRequirement":
        """Helper to build a requirement directly from a media path."""

        template = {
            "media_path": media_path,
            "media_role": media_role,
            "world_id": world_id,
        }
        return cls(
            graph=graph,
            template=template,
            policy=policy,
            identifier=identifier,
        )
