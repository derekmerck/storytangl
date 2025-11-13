__all__ = ["Concept", "Item", "Flag"]


def __getattr__(name: str):
    if name == "Concept":
        from .concept import Concept as _Concept

        return _Concept
    if name == "Item":
        from .item import Item as _Item

        return _Item
    if name == "Flag":
        from .item import Flag as _Flag

        return _Flag
    raise AttributeError(name)
