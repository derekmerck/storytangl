"""Core package namespace for the StoryTangl engine and tooling."""

from pkgutil import extend_path

__path__ = extend_path(__path__, __name__)

from .info import *  # noqa: F401,F403 - re-export package metadata for convenience

__all__ = [name for name in globals() if not name.startswith("_")]
