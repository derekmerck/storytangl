# tangl/persist/repo.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from uuid import UUID
from tangl.vm36.execution.patch import Patch
from .ser import Serializer, PickleSerializer

class Repository:
    def load_latest_snapshot(self, graph_id: UUID) -> tuple[int, bytes] | None: ...
    def append_patch(self, graph_id: UUID, expected_version: int, patch_blob: bytes, idem_key: str | None) -> int: ...
    def save_snapshot(self, graph_id: UUID, version: int, snap_blob: bytes) -> None: ...

@dataclass
class InMemoryRepo(Repository):
    snaps: dict[UUID, tuple[int, bytes]] = field(default_factory=dict)
    events: dict[UUID, list[bytes]] = field(default_factory=dict)
    def load_latest_snapshot(self, graph_id: UUID) -> tuple[int, bytes] | None:
        return self.snaps.get(graph_id)
    def append_patch(self, graph_id: UUID, expected_version: int, patch_blob: bytes, idem_key: str | None) -> int:
        log = self.events.setdefault(graph_id, [])
        if expected_version != len(log):
            raise RuntimeError(f"version conflict: expected {expected_version}, got {len(log)}")
        log.append(patch_blob)
        return len(log)
    def save_snapshot(self, graph_id: UUID, version: int, snap_blob: bytes) -> None:
        self.snaps[graph_id] = (version, snap_blob)