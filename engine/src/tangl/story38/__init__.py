"""Compatibility wrapper package that forwards ``tangl.story38`` to ``tangl.story``."""

from __future__ import annotations

import importlib
import pkgutil
import sys

import tangl.story as _story
from tangl.story import *  # noqa: F401,F403


def _alias_submodules() -> None:
    src_prefix = "tangl.story."
    dst_prefix = f"{__name__}."
    for mod in pkgutil.walk_packages(_story.__path__, src_prefix):
        target = mod.name
        alias = dst_prefix + target[len(src_prefix) :]
        if alias in sys.modules:
            continue
        try:
            sys.modules[alias] = importlib.import_module(target)
        except Exception:
            continue


_alias_submodules()
