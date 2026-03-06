"""Compatibility wrapper package that forwards ``tangl.service38`` to ``tangl.service``."""

from __future__ import annotations

import importlib
import pkgutil
import sys

import tangl.service as _service
from tangl.service import *  # noqa: F401,F403


def _alias_submodules() -> None:
    src_prefix = "tangl.service."
    dst_prefix = f"{__name__}."
    for mod in pkgutil.walk_packages(_service.__path__, src_prefix):
        target = mod.name
        alias = dst_prefix + target[len(src_prefix) :]
        if alias in sys.modules:
            continue
        try:
            sys.modules[alias] = importlib.import_module(target)
        except Exception:
            continue


_alias_submodules()
