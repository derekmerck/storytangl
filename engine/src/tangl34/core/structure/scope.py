from typing import Any
from pydantic import Field

from ..entity import Entity

class ScopeMixin(Entity):

    locals: dict[str, Any] = Field(default_factory=dict)
