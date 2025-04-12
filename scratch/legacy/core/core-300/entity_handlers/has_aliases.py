from __future__ import annotations
import logging

from pydantic import BaseModel, Field

from tangl.type_hints import Identifier

logger = logging.getLogger(__name__)

class HasAliases(BaseModel):

    aliases: set[Identifier] = Field(default_factory=set)

    def _get_identifiers(self) -> set[Identifier]:
        return self.aliases

