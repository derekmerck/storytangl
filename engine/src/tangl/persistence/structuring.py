from typing import Protocol, Type, Mapping
import dataclasses

try:
    import attr
    HAS_ATTRS = True
except ImportError:
    attr = object
    HAS_ATTRS = False

try:
    import pydantic
    HAS_PYDANTIC = True
except ImportError:
    pydantic = object
    HAS_PYDANTIC = False

from tangl.type_hints import HasUid, UnstructuredData

class StructuringHandlerProtocol(Protocol):

    @classmethod
    def structure(cls,
                  unstructured: UnstructuredData,
                  kind_map: Mapping[str, Type[HasUid]] = None) -> HasUid: ...
    @classmethod
    def unstructure(cls, structured: HasUid) -> UnstructuredData: ...


class StructuringHandler:
    """
    Injects and references class annotations within unstructured data to
    determine which class to instantiate.

    Methods:
      - `structure(data, kind_map)`: Initializes an instance of the
        declared class using `kind`.
      - `unstructure(entity)`: Extracts data from an entity instance into a
        dictionary and writes `kind`.
    """

    @classmethod
    def structure(cls,
                  unstructured: UnstructuredData,
                  kind_map: Mapping[str, Type[HasUid]] = None) -> HasUid:
        unstructured = dict(unstructured)
        kind = unstructured.pop("kind")
        if isinstance(kind, str) and kind_map is not None:
            kind = kind_map[kind]
        if hasattr(kind, "structure"):
            return kind.structure(unstructured)
        return kind(**unstructured)

    @classmethod
    def unstructure(cls, structured: HasUid) -> UnstructuredData:
        if hasattr(structured, 'unstructure'):
            unstructured = structured.unstructure()
        elif dataclasses.is_dataclass(structured):
            unstructured = dataclasses.asdict(structured)
        elif HAS_PYDANTIC and isinstance(structured, pydantic.BaseModel):
            unstructured = structured.model_dump()
        elif HAS_ATTRS and attr.has(structured):
            unstructured = attr.asdict(structured, recurse=True)
        elif isinstance(structured, UnstructuredData):  # already a dict
            unstructured = structured
        else:
            # Trivial fallback for feral classes
            unstructured = {**structured.__dict__}
        if "kind" not in unstructured:
            unstructured["kind"] = structured.__class__
        return unstructured
