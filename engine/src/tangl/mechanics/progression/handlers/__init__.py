from __future__ import annotations

from .base import StatHandler
from .probit import ProbitStatHandler
from .linear import LinearStatHandler
from .logint import LogIntStatHandler

_HANDLER_REGISTRY: dict[str, type[StatHandler]] = {
    "probit": ProbitStatHandler,
    "linear": LinearStatHandler,
    "logint": LogIntStatHandler,
}


def get_handler_cls(name: str | None) -> type[StatHandler]:
    """Resolve a registered handler name to a concrete handler class."""
    if name is None:
        return ProbitStatHandler

    return _HANDLER_REGISTRY.get(name.strip().lower(), ProbitStatHandler)

__all__ = [
    "StatHandler",
    "ProbitStatHandler",
    "LinearStatHandler",
    "LogIntStatHandler",
    "get_handler_cls",
]
