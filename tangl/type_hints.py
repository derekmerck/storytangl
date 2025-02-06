from typing import Protocol, Any, Type, Union
from uuid import UUID
from enum import Enum
from pathlib import Path

# General types
StringMap = dict[str, Any]
Primitive = str | int | float | Enum | bool
Pathlike = Path | str
Typelike = Type | str

# Used by business logic
Label = str          # Not unique, will not be used for hashing
Expr = str           # evaluable/executable string expression
UniqueLabel = str    # Must be unique within namespace, may be used for hashing
Hash = int | bytes
Identifier = Union[UUID, UniqueLabel, Hash]
Tag = Enum | str | int  # Tags may be enums, strs, or ints
ClassName = str      # Unique name of an entity subclass
TemplateName = str   # Unique name of a default attributes template
TemplateMap = dict[TemplateName, dict[str, Any]]
Turn = int

# Used by Storage and Serializers
class HasUid(Protocol):
    uid: UUID
FlatData = str | bytes
UnstructuredData = StringMap

# UI style hints
StyleId = str            # ui element id, #id or id=name
StyleClass = str         # ui element class list, npc, npc.win
StyleDict = StringMap    # ui element style dictionary, {'color': 'orange', ...}
