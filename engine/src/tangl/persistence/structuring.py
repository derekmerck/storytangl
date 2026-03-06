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
                  obj_cls_map: Mapping[str, Type[HasUid]] = None) -> HasUid: ...
    @classmethod
    def unstructure(cls, structured: HasUid) -> UnstructuredData: ...


class StructuringHandler:
    """
    Injects and references class annotations within unstructured data to
    determine which class to instantiate.

    Methods:
      - `structure(data, obj_cls_map)`: Initializes an instance of the
        declared class using `kind` (preferred) or `obj_cls` (legacy alias).
      - `unstructure(entity)`: Extracts data from an entity instance into a
        dictionary and writes both `kind` and `obj_cls` for compatibility.
    """

    @classmethod
    def structure(cls,
                  unstructured: UnstructuredData,
                  obj_cls_map: Mapping[str, Type[HasUid]] = None) -> HasUid:
        unstructured = dict(unstructured)
        obj_cls = unstructured.pop("kind", None)
        if obj_cls is None:
            obj_cls = unstructured.pop("obj_cls")
        if isinstance(obj_cls, str) and obj_cls_map is not None:
            obj_cls = obj_cls_map[ obj_cls ]
        if hasattr(obj_cls, 'structure'):
            return obj_cls.structure(unstructured)
        return obj_cls( **unstructured )

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
            if "obj_cls" in unstructured:
                unstructured["kind"] = unstructured["obj_cls"]
            else:
                unstructured["kind"] = structured.__class__
        if "obj_cls" not in unstructured:
            unstructured["obj_cls"] = unstructured["kind"]
        return unstructured
