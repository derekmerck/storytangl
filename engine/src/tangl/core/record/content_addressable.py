"""Content-addressable mixin for Records with content-based identity."""

from __future__ import annotations

import logging
from typing import Any, Optional, ClassVar

from pydantic import Field, model_validator, BaseModel, field_validator, ConfigDict

from tangl.type_hints import Hash
from tangl.utils.hashing import hashing_func
from tangl.core.entity import is_identifier

logger = logging.getLogger(__name__)


class ContentAddressable(BaseModel):
    # language=rst
    """
    ContentAddressable(content_hash: bytes)

    Mixin for Records that need content-addressed identifiers.

    Why
    ---
    Content-addressed hashes provide a stable identity tied to *what* a record
    contains, not *when* it was instantiated. This enables deduplication,
    provenance tracking, and reproducibility checks across registries.

    Key Features
    ------------
    * **Automatic hashing** – ``content_hash`` is computed during model
      construction unless explicitly provided (e.g. by :class:`Snapshot`).
    * **Customizable scope** – override :meth:`_get_hashable_content` to control
      which attributes influence the hash (media bytes, template structure, etc.).
    * **Registry alias** – the hash is marked as an identifier for
      :class:`~tangl.core.registry.Registry` lookups.

    Usage
    -----
    .. code-block:: python

        class MyRecord(Record, ContentAddressable):

            @classmethod
            def _get_hashable_content(cls, data: dict) -> Any:
                return {k: v for k, v in data.items() if k != "uid"}

    See also
    --------
    :class:`~tangl.core.record.Record`
    :class:`~tangl.core.snapshot.Snapshot`
    """

    model_config = ConfigDict(frozen=True)
    # Must override to True to run any 'after' model validators
    
    content_hash: Optional[Hash] = Field(
        None,
        json_schema_extra={'is_identifier': True},
        description="Content-addressed identifier computed from record data"
    )

    req_hash: ClassVar[bool] = False
    
    @model_validator(mode='before')
    @classmethod
    def _compute_content_hash(cls, data: Any) -> dict:
        # language=rst
        """Compute content_hash if not explicitly provided.
        
        Called during model construction before field validation.
        If content_hash already present, respects it (for deserialization).
        Otherwise, computes it from _get_hashable_content().
        
        Args:
            data: Raw data dict before Pydantic processing
            
        Returns:
            Data dict with content_hash added
        """
        # Convert to dict if not already (handles various input types)
        if not isinstance(data, dict):
            return data
        
        # If hash already provided, don't override (deserialization case)
        if "content_hash" in data and data["content_hash"]:  # Reject any falsy
            return data

        try:
            # Get hashable content (subclass customization point)
            hashable = cls._get_hashable_content(data)
            logger.info(f"Content hash items: {hashable}")

            # Compute hash using standard hashing function
            if hashable is not None:
                data["content_hash"] = hashing_func(hashable)
            else:
                logger.debug(
                    "%s: _get_hashable_content returned None, no content_hash computed",
                    cls.__name__,
                )
        except Exception as exc:
            logger.warning("%s: failed to compute content_hash: %s", cls.__name__, exc, exc_info=True)
            if cls.req_hash:
                raise
            # Allow construction to proceed without hash
        
        return data
    
    @classmethod
    def _get_hashable_content(cls, data: dict) -> Any:
        # language=rst
        """Extract hashable content from raw data dict.
        
        Override in subclasses to customize what gets hashed.
        
        Default behavior: Hash entire record excluding metadata.
        
        Args:
            data: Raw data dict before Pydantic processing
            
        Returns:
            Hashable content (dict, bytes, str, etc.) or None to skip hashing
            
        Examples:
            # MediaRIT: Hash file content
            @classmethod
            def _get_hashable_content(cls, data: dict) -> Any:
                if 'data' in data:
                    return data['data']
                elif 'path' in data:
                    return compute_data_hash(Path(data['path']))
                return None
            
            # Template: Hash structure excluding metadata
            @classmethod
            def _get_hashable_content(cls, data: dict) -> dict:
                exclude = {'uid', 'content_hash', 'scope', 'label'}
                return {k: v for k, v in data.items() if k not in exclude}
        """
        # Default: Hash everything except known metadata fields
        # todo: could use fields here with a filter
        exclude = {"uid", "is_dirty_", "content_hash", "created_at", "updated_at", "seq", "obj_cls"}
        return {k: v for k, v in data.items() if k not in exclude}

    @is_identifier
    def content_identifier(self) -> str:
        """Get human-readable content identifier (truncated hex).
        
        Useful for logging and debugging.
        
        Returns:
            First 16 hex chars of content_hash, or 'no-hash' if not computed
        """
        if self.content_hash:
            return self.content_hash.hex()[:16]
        return "no-hash"

    # @field_serializer("content_hash")
    # def serialize_hash(self, value: bytes | None) -> str | None:
    #     return value.hex() if value is not None else None

    @field_validator("content_hash", mode="before")
    @classmethod
    def parse_hash(cls, value: Any) -> bytes | None:
        if not value:
            return None
        elif isinstance(value, bytes):
            return value
        elif isinstance(value, str):
            value = value.strip()
            try:
                return bytes.fromhex(value)
            except ValueError as exc:
                msg = f"Invalid hex content_hash: {value!r}"
                raise ValueError(msg) from exc
        return value
