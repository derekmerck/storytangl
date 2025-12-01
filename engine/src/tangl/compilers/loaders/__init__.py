"""Loader registry and simple built-in script loaders."""

from .base import ScriptLoader
from .registry import get_loader, register_loader
from . import simple_single_file, simple_tree  # noqa: F401

__all__ = ["ScriptLoader", "get_loader", "register_loader"]
