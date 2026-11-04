from __future__ import annotations
from typing import TYPE_CHECKING, Any
from uuid import UUID

from pydantic import Field, model_validator, BaseModel

from tangl.type_hints import UniqueLabel
from tangl.media.media_creators.media_spec import MediaResolutionClass, MediaSpec
from tangl.media.media_data_type import MediaDataType
from tangl.presentation.hints import StagingHints

if TYPE_CHECKING:
    from .vector_forge import VectorForge

class VectorScriptItem(BaseModel, extra="allow", arbitrary_types_allowed=True):
    """Nominate a vector by label or by a reference to its subject."""
    label: UniqueLabel = None
    ref: UniqueLabel = None

    staging_hints: StagingHints = None

    @model_validator(mode='after')
    def _check_exactly_one(self):
        if not any([self.label, self.ref]) or all([self.label, self.ref]):
            raise ValueError("Exactly one of `label` or `ref` must be provided")
        return self


class VectorSpec(MediaSpec):
    resolution_class: MediaResolutionClass = MediaResolutionClass.FAST_SYNC
    data_type: MediaDataType = MediaDataType.VECTOR

    source_id: UUID | None = None
    source_hash: bytes | None = None
    source_sha256: str = ""
    plan_identity: str = ""
    registration: tuple[float, float, float, float] | None = None
    locators: tuple[str, ...] = ()
    bindings: dict[str, dict[str, str]] = Field(default_factory=dict)
    targets: tuple[tuple[str, str, str, tuple[int, ...]], ...] = ()
    renderer_version: str = "2"

    def fingerprint_payload(self) -> dict[str, Any]:
        payload = self.normalized_spec_payload()
        for field in ("source_id", "label", "tags", "resolution_class", "persistence_policy"):
            payload.pop(field, None)
        return payload

    @classmethod
    def get_creation_service(cls) -> VectorForge:
        from .vector_forge import VectorForge
        return VectorForge()
