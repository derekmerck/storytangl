"""Ledger metadata response."""

from __future__ import annotations

from uuid import UUID

from tangl.service.response.native_response import InfoModel


class StoryInfo(InfoModel):
    title: str
    step: int
    cursor_id: UUID
    journal_size: int
