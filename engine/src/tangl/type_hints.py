# tangl/type_hints.py
from typing import Protocol, Any, Type, Union, Callable, TypeAlias, MutableMapping, Optional
from uuid import UUID
from enum import Enum
from pathlib import Path

# General types
StringMap: TypeAlias = MutableMapping[str, Any]  # A dict with identifier-safe string keys such as namespace, constraints, unstructured data
Primitive: TypeAlias = str | int | float | Enum | bool
Pathlike: TypeAlias = Path | str
Typelike: TypeAlias = Type | str
Predicate: TypeAlias = Callable[[StringMap], bool]
Hash: TypeAlias = bytes         # Digests are bytes

# Used by business logic concepts
Label: TypeAlias = str          # Not unique, will never be used for hashing
UniqueLabel: TypeAlias = str    # Must be unique within namespace, may be used for hashing
Identifier: TypeAlias = Union[UUID, UniqueLabel, Hash]  # Any unique alias assigned to an instance
Expr: TypeAlias = str           # Evaluable/executable string expression
Tag: TypeAlias = Union[Enum, str, int]  # Tags may be enums, strs, or ints
ClassName: TypeAlias = str      # Unique name of an entity subclass
TemplateName: TypeAlias = str   # Unique name of a default attributes template
TemplateMap: TypeAlias = dict[TemplateName, StringMap]  # Collection of default attributes by name
Step: TypeAlias = int           # Graph traversal or resolution step counter

# Used by storage and serializers
class HasUid(Protocol):
    uid: UUID
UnstructuredData = StringMap
# A string map of kwargs suitable for structuring a HasUid instance, includes an 'obj_cls' and 'uid' key
FlatData: TypeAlias = str | bytes
# A data-stream representation of an object suitable for serialization

# UI style hints
StyleId: TypeAlias = str                 # ui element id, '#id' or 'id=name'
StyleClass: TypeAlias = str | list[str]  # ui element classes, ['npc', 'happy'] or 'npc.happy'
StyleDict: TypeAlias = StringMap         # ui element style dictionary, {'color': 'orange', ...}
