from __future__ import annotations

"""Authentication and authorization primitives for service endpoints."""

from enum import Enum


class AuthMode(str, Enum):
    """Global authentication mode for the orchestrator."""

    OFF = "off"
    ENFORCED = "enforced"


class AccessLevel(str, Enum):
    """Access tiers for orchestrated endpoints and users."""

    ANON = "anon"
    USER = "user"
    ADMIN = "admin"

    # Aliases maintained for backward compatibility with legacy tests and code.
    PUBLIC = ANON
    RESTRICTED = ADMIN

    def allows(self, required: "AccessLevel") -> bool:
        """Return ``True`` when this level meets or exceeds ``required``."""

        order = {
            AccessLevel.ANON: 0,
            AccessLevel.USER: 1,
            AccessLevel.ADMIN: 2,
        }
        return order[self] >= order[required]
