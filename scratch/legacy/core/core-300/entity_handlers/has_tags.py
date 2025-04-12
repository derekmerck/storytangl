from __future__ import annotations
import logging
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from tangl.type_hints import Tags

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

class HasTags(BaseModel):
    """Mixin to classify and filter entities based on assigned characteristics or roles."""

    tags: Tags = Field(default_factory=set)

    def has_tags(self, *tags: str) -> bool:
        """Condition querying based on tags, enhancing search and categorization."""
        logger.debug(f"testing tags: {tags} against self: {self.tags}")
        return bool(set(tags).issubset(self.tags))   # has all of

    @staticmethod
    def _filter_by_tags(inst: HasTags, tags: Tags) -> bool:
        return inst.has_tags(*tags)

