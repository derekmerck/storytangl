from typing import Type, Any

def make_repr(obj_cls: Type, data: list[tuple[str, Any]] | dict[str, Any]):
    """
    This formats (Type, [(attrib, val), ...]) as Type(attrib=val, ... ) for reprs
    """
    if isinstance(data, dict):
        data = data.items()
    s = f"{obj_cls.__name__}("
    for k, v in data:
        s += f"{k}={str(v)}, "
    s = s[:-2]
    s += ")"
    return s
