from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Blocker:
    """One blocker reason with optional structured context for viability diagnostics."""

    reason: str
    context: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ViabilityResult:
    """Result DTO for non-mutating provisioning viability checks."""

    viable: bool
    chain: list[str] = field(default_factory=list)
    scope_distance: int = 0
    blockers: list[Blocker] = field(default_factory=list)
