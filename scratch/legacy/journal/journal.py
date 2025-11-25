# tangl/projection/journal.py
# (MVP intentionally tiny: journal entries are dicts in Patch.journal)
# Later: define BaseFragment/ContentFragment Pydantic models and a projector that
# transforms Patch.journal into renderable DTOs or graph nodes.

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from uuid import UUID
from tangl.vm import Patch

@dataclass
class JournalEntryRow:
    tick_id: UUID
    idx_in_tick: int
    text: str
    speaker: Optional[UUID] = None
    tags: frozenset[str] = frozenset()
    meta: dict = field(default_factory=dict)

@dataclass
class DiscourseIndex:
    rows: List[JournalEntryRow] = field(default_factory=list)
    by_speaker: Dict[UUID, List[int]] = field(default_factory=dict)
    by_tag: Dict[str, List[int]] = field(default_factory=dict)

    def add_patch(self, patch: Patch) -> None:
        base = len(self.rows)
        for i, frag in enumerate(patch.journal):
            row = JournalEntryRow(
                tick_id=patch.tick_id,
                idx_in_tick=i,
                text=frag.get("text", ""),
                speaker=frag.get("speaker_uid"),
                tags=frozenset(frag.get("tags", ())),
                meta={k: v for k, v in frag.items() if k not in {"text", "speaker_uid", "tags"}},
            )
            self.rows.append(row)
            if row.speaker is not None:
                self.by_speaker.setdefault(row.speaker, []).append(base + i)
            for t in row.tags:
                self.by_tag.setdefault(t, []).append(base + i)

    # simple queries
    def mentioned(self, uid: UUID) -> bool:
        return bool(self.by_speaker.get(uid))

    def last_by_speaker(self, uid: UUID) -> Optional[JournalEntryRow]:
        idxs = self.by_speaker.get(uid)
        return self.rows[idxs[-1]] if idxs else None
