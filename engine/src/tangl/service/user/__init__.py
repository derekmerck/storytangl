"""Service user package."""

from __future__ import annotations

from .user import User

__all__ = ["ApiKeyInfo", "User", "UserController"]


def __getattr__(name: str):
    if name in {"ApiKeyInfo", "UserController"}:
        from .user_controller import ApiKeyInfo, UserController

        return {"ApiKeyInfo": ApiKeyInfo, "UserController": UserController}[name]
    raise AttributeError(name)
