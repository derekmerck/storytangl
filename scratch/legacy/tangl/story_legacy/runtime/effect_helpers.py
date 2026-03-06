"""Helper functions exposed to StoryScript effect expressions."""

from __future__ import annotations

from functools import partial
from typing import Callable

from tangl.core import Graph

from ..concepts.item import Item


def acquire_item(label: str, *, graph: Graph) -> None:
    """Acquire the scripted item identified by ``label``."""

    Item.acquire(label, graph=graph)


def set_flag(label: str, *, value: bool = True, graph: Graph) -> None:
    """Set the boolean StoryScript flag ``label`` to ``value``."""

    graph.locals[label] = value


STORY_EFFECT_HELPERS: dict[str, Callable[..., None]] = {
    "acquire_item": acquire_item,
    "set_flag": set_flag,
}


def _missing_graph(name: str) -> Callable[..., None]:
    def _raiser(*_: object, **__: object) -> None:
        raise RuntimeError(
            f"Effect helper '{name}' requires the story graph in the execution namespace",
        )

    return _raiser


def bind_effect_helpers(*, graph: Graph | None) -> dict[str, Callable[..., None]]:
    """Return helper callables bound to ``graph`` for use in expressions."""

    if graph is None:
        return {name: _missing_graph(name) for name in STORY_EFFECT_HELPERS}
    return {name: partial(helper, graph=graph) for name, helper in STORY_EFFECT_HELPERS.items()}


__all__ = ["STORY_EFFECT_HELPERS", "bind_effect_helpers"]
