"""Compatibility wrapper package that forwards ``tangl.core38`` to ``tangl.core``."""

from __future__ import annotations

import importlib
import pkgutil
import sys

import tangl.core as _core
from tangl.core import *  # noqa: F401,F403


def _alias_submodules() -> None:
    src_prefix = "tangl.core."
    dst_prefix = f"{__name__}."
    for mod in pkgutil.walk_packages(_core.__path__, src_prefix):
        target = mod.name
        alias = dst_prefix + target[len(src_prefix) :]
        if alias in sys.modules:
            continue
        try:
            sys.modules[alias] = importlib.import_module(target)
        except Exception:
            # Keep compatibility wrapper best-effort during staged cutover.
            continue


_alias_submodules()
