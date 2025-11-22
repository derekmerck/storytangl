from __future__ import annotations

"""Configuration container for orchestrator behavior."""

from dataclasses import dataclass

from tangl.service.auth import AccessLevel, AuthMode


@dataclass
class ServiceConfig:
    """Lightweight service configuration applied to the orchestrator."""

    auth_mode: AuthMode = AuthMode.OFF
    default_user_label: str = "local"
    default_access_level: AccessLevel = AccessLevel.ADMIN
