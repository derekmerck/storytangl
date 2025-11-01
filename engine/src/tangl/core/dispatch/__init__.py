# core-dispatch, global registry and handlers

from .core_dispatch import core_dispatch, on_create, on_init, on_link, on_unlink
from .scoped_dispatch import scoped_dispatch
from .hooked_registry import on_index, HookedRegistry
