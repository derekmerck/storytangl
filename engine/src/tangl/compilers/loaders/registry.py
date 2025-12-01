from __future__ import annotations

from importlib import import_module
from typing import Callable

from .base import ScriptLoader

LOADER_REGISTRY: dict[str, Callable[[], ScriptLoader]] = {}


def register_loader(name: str):
    """Register a loader factory under a short name."""

    def deco(factory: Callable[[], ScriptLoader]):
        LOADER_REGISTRY[name] = factory
        return factory

    return deco


def get_loader(loader_ref: str) -> ScriptLoader:
    """Instantiate a loader based on a registry reference or module path."""

    if loader_ref.startswith("builtin:"):
        name = loader_ref.split(":", 1)[1]
        factory = LOADER_REGISTRY[name]
        return factory()

    module_path, qualname = loader_ref.split(":", 1)
    module = import_module(module_path)
    loader_cls = getattr(module, qualname)
    return loader_cls()
