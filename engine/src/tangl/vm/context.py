"""Compatibility context exports for legacy import paths."""

from __future__ import annotations

from .runtime.frame import PhaseCtx as Context

# Legacy materialization context path retained as a lightweight alias.
MaterializationContext = Context

__all__ = ["Context", "MaterializationContext"]
