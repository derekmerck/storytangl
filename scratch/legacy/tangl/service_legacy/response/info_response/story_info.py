"""Ledger metadata response."""

from __future__ import annotations

from uuid import UUID

from tangl.service.response.native_response import InfoModel


class StoryInfo(InfoModel):
    """Metadata describing the current story ledger."""

    title: str
    """Story/world title."""

    step: int
    """Current step count."""

    cursor_id: UUID
    """Current cursor identifier within the story graph."""

    journal_size: int
    """Number of fragments present in the journal."""

    cursor_label: str | None = None
    """Label for the current cursor node, if available."""
