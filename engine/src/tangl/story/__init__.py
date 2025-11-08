
__all__ = ["Concept", "Scene", "Block", "World", "story_dispatch"]


def __getattr__(name: str):
    if name == "World":
        from .fabula import World as _World

        return _World
    if name == "Concept":
        from .concepts import Concept as _Concept

        return _Concept
    if name == "Scene":
        from .episode import Scene as _Scene

        return _Scene
    if name == "Block":
        from .episode import Block as _Block

        return _Block
    if name == "story_dispatch":
        from .dispatch import story_dispatch as _dispatch

        return _dispatch
    raise AttributeError(name)
