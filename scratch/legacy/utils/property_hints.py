from __future__ import annotations

import functools
from typing import Type, Literal, get_type_hints, get_args
import logging
import inspect

from pydantic import BaseModel
# It is not necessary to restrict this to subclasses of BaseModel, as no special
# properties of BaseModel are required, but it is useful in this application.

from tangl.type_hints import UniqueLabel

logger = logging.getLogger(__name__)

ReturnMode = Literal['discrete', 'collection']
ReturnHint = tuple[ReturnMode, Type[BaseModel]]

def get_return_hint(attrib) -> ReturnHint:

    try:
        type_hints = get_type_hints(attrib.fget)
    except (AttributeError, NameError):
        logger.error( f"Failed to get hint from {attrib.fget}")
        raise

    return_hint = type_hints['return']  # list[item] or dict[str, item]

    if inspect.isclass(return_hint) and issubclass(return_hint, BaseModel):
        obj_cls = return_hint
        # It's a discrete element
        return "discrete", obj_cls

    elif return_args := get_args(return_hint):
        obj_cls = return_args[-1]
        if inspect.isclass(obj_cls) and issubclass(obj_cls, BaseModel):
            # It's a collection
            return "collection", obj_cls

    raise TypeError(f"Unable to infer value type from return hint {return_hint}")  # pragma: no cover


@functools.lru_cache()
def get_property_return_hints(cls: Type) -> dict[UniqueLabel, ReturnHint]:
    """
    Inspects class properties and collates return hint annotations as a dict in the
    form `{ property_name: ('discrete'|'collection', obj_cls) }`

    Property names with leading underscores are assumed to be type hinting aliases
    for the un-underscored name, i.e., `_components: Component -> components: Component`

    This is useful for classes that want to re-key input kwargs from property names
    into child-with-type format.
    """
    res = {}
    for attrib_name in dir(cls):

        if attrib_name in ['label', 'path', 'root', 'uid', 'forced', 'is_entry']:
            continue

        attrib = getattr(cls, attrib_name)
        if isinstance(attrib, property) and not hasattr(BaseModel, attrib_name):
            # It _might_ be a child type, try to infer the class
            try:
                hint = get_return_hint(attrib)
                if hint:
                    res[attrib_name.strip("_")] = hint
            except (TypeError, KeyError) as e:
                logger.warning(f"Cannot infer type from { attrib_name }, {e}")
                pass
    return res

