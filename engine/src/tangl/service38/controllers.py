"""Compatibility barrel that resolves controller symbols lazily at runtime."""

from __future__ import annotations

__all__ = [
    "ApiKeyInfo",
    "DEFAULT_CONTROLLERS",
    "RuntimeController",
    "SystemController",
    "UserController",
    "WorldController",
]

_SYMBOL_TO_MODULE = {
    "ApiKeyInfo": "tangl.service.controllers",
    "DEFAULT_CONTROLLERS": "tangl.service.controllers",
    "RuntimeController": "tangl.service.controllers",
    "SystemController": "tangl.service.controllers",
    "UserController": "tangl.service.controllers",
    "WorldController": "tangl.service.controllers",
}


def __getattr__(name: str):
    module_name = _SYMBOL_TO_MODULE.get(name)
    if module_name is None:
        raise AttributeError(name)
    module = __import__(module_name, fromlist=[name])
    value = getattr(module, name)
    globals()[name] = value
    return value
