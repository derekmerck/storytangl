# tangl/core/types.py
"""
# tangl.core.types

Wire protocol for changes: **Effects** and **Patches**.

- `Effect`: a single mutation (op + args) with **provenance** `(phase, handler_id)`.
- `Patch`: an **atomic tick** — the ordered list of Effects plus **journal** and **io** transcripts.

**Why not mutate the graph directly?**
Deterministic replay and auditability. Handlers only **emit** Effects; the VM applies them
in a **canonical order** (`vm.patch.canonicalize`) so deletes happen before creates, etc.

Downstream:
- `StepContext.emit/create_node/...` append Effects to the current patch.
- `vm.patch.apply_patch` consumes Effects and calls Graph’s silent mutators.
- `persist.repo` stores Patches as the event log; snapshots store the occasional Graph DTO.
"""
from __future__ import annotations
from enum import StrEnum
from typing import Tuple, TypeAlias

# Paths like ("locals","hp")
AttrPath: TypeAlias = Tuple[str, ...]
# Fully qualified class name, e.g. "tangl.core.entity.Node"
FQN: TypeAlias = str
Tag: TypeAlias = str

class EdgeKind(StrEnum):
    TRANSITION = "transition"
    CONTAINS = "contains"
    AFFORD = "afford"
    REQUIRES = "requires"
    FULFILLS = "fulfills"
    ROLE = "role"

    def prefix(self):
        return str(self.value).lower() + ":"
