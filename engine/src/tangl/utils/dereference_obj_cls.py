from typing import TypeVar, Type, Optional
import logging

logger = logging.getLogger(__name__)

TypeT = TypeVar("TypeT", bound=Type)

# todo: this isn't actually used, the code in bm+ is simpler
def subclass_by_name(base_cls: TypeT, cls_name: str) -> Optional[TypeT]:
    logger.debug(f"subclass_by_name {base_cls.__name__} == {cls_name}")
    if base_cls.__name__ == cls_name:
        return base_cls
    for cls_ in base_cls.__subclasses__():
        if cls_.__name__ == cls_name:
            return cls_
        if cls_ := subclass_by_name(cls_, cls_name):
            return cls_
    return None  # can't raise here b/c it is a base case in a recursive call

def dereference_obj_cls(cls: TypeT, cls_name: str) -> TypeT:
    if cls_name is None:
        return cls
    if isinstance(cls_name, type):
        return cls_name
    obj_cls = subclass_by_name(cls, cls_name)
    if obj_cls is None:
        raise ValueError(f"Cannot dereference subclass {cls_name} in {cls.__name__}")
    return obj_cls
