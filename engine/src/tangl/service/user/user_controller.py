from __future__ import annotations

"""Backward-compatible shim for :mod:`tangl.service.controllers.user_controller`."""

from ..controllers.user_controller import ApiKeyInfo, UserController

__all__ = ["ApiKeyInfo", "UserController"]
