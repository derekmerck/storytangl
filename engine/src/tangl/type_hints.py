from typing import Protocol, Any, Type, Union, Dict, NewType, Callable, TYPE_CHECKING
from uuid import UUID
from enum import Enum
from pathlib import Path

# General types
StringMap = NewType('StringMap', dict[str, Any])  # A dict with identifier-safe string keys
Primitive = str | int | float | Enum | bool
Pathlike = Path | str
Typelike = Type | str

# Used by business logic
Label = str          # Not unique, will not be used for hashing
Expr = str           # Evaluable/executable string expression
UniqueLabel = str    # Must be unique within namespace, may be used for hashing
Hash = bytes         # Digests are bytes
Identifier = Union[UUID, UniqueLabel, Hash]
Tag = Union[Enum, str, int]  # Tags may be enums, strs, or ints
ClassName = str      # Unique name of an entity subclass
TemplateName = str   # Unique name of a default attributes template
TemplateMap = dict[TemplateName, dict[str, Any]]
Step = int           # Traversal step counter

# Used by storage and serializers
class HasUid(Protocol):
    uid: UUID
FlatData = str | bytes
UnstructuredData = StringMap
# A string map of kwargs suitable for structuring a HasUid instance, includes an 'obj_cls' and 'uid' key

# UI style hints
StyleId = str            # ui element id, #id or id=name
StyleClass = str         # ui element class list, npc, npc.win
StyleDict = StringMap    # ui element style dictionary, {'color': 'orange', ...}
