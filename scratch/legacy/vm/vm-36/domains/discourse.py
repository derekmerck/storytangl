# tangl/domains/discourse.py
from __future__ import annotations
from typing import Mapping
from tangl.vm36.execution.tick import StepContext
from tangl.projection.journal import DiscourseIndex

class SeesDiscourse:
    DOMAIN = "sees_discourse"  # tag as "domain:sees_discourse" to activate, or mount globally if you prefer

    def __init__(self, idx: DiscourseIndex):
        self.idx = idx

    def vars(self, g, node) -> Mapping[str, object]:
        def has_spoken(ctx: StepContext, speaker_uid) -> bool:
            # same-tick check first
            for frag in reversed(ctx.journal):
                if frag.get("speaker_uid") == speaker_uid:
                    return True
            return self.idx.mentioned(speaker_uid)

        def last_spoken(ctx: StepContext, speaker_uid):
            # same-tick scan, then committed
            for i in range(len(ctx.journal) - 1, -1, -1):
                f = ctx.journal[i]
                if f.get("speaker_uid") == speaker_uid:
                    return {"tick_id": ctx.choice_id, "idx_in_tick": i, **f}
            row = self.idx.last_by_speaker(speaker_uid)
            if row:
                return {"tick_id": str(row.tick_id), "idx_in_tick": row.idx_in_tick,
                        "text": row.text, "speaker_uid": row.speaker, "tags": list(row.tags), **row.meta}
            return None

        return {"discourse": {"has_spoken": has_spoken, "last_spoken": last_spoken}}

    def handlers(self, g, node):
        return ()