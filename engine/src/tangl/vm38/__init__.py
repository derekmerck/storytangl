"""Compatibility wrapper package that forwards ``tangl.vm38`` to ``tangl.vm``."""

from __future__ import annotations

import importlib
import pkgutil
import sys

import tangl.vm as _vm
from tangl.vm import *  # noqa: F401,F403


def _alias_submodules() -> None:
    src_prefix = "tangl.vm."
    dst_prefix = f"{__name__}."
    for mod in pkgutil.walk_packages(_vm.__path__, src_prefix):
        target = mod.name
        alias = dst_prefix + target[len(src_prefix) :]
        if alias in sys.modules:
            continue
        try:
            sys.modules[alias] = importlib.import_module(target)
        except Exception:
            continue


_alias_submodules()
