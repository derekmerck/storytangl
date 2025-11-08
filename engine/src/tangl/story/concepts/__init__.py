__all__ = ["Concept"]


def __getattr__(name: str):
    if name == "Concept":
        from .concept import Concept as _Concept

        return _Concept
    raise AttributeError(name)
