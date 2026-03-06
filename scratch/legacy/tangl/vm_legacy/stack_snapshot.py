from __future__ import annotations

"""Call stack snapshots for event-sourced reconstruction."""

from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import Field

from tangl.core import Record
from tangl.utils.base_model_plus import BaseModelPlus

if TYPE_CHECKING:  # pragma: no cover - import cycle protection
    from tangl.vm.frame import StackFrame


class StackFrameSnapshot(BaseModelPlus):
    """StackFrameSnapshot(return_cursor_id: UUID, call_type: str)"""

    """Persisted slice of a :class:`~tangl.vm.frame.StackFrame`. 

    Why
    ----
    Encapsulates only the data that cannot be reconstructed from the graph so
    that historical call stacks can be replayed without holding full frame
    objects.

    Key Features
    ------------
    * **Minimal payload** – stores return location and call type only.
    * **Graph-derived metadata** – labels and depths are recomputed on restore.

    API
    ---
    - :attr:`return_cursor_id` – node to jump back to when unwinding.
    - :attr:`call_type` – semantic category of the call (defaults to
      ``"generic"``).
    """
    return_cursor_id: UUID
    call_type: str = "generic"


class StackSnapshot(Record):
    """StackSnapshot(frames: list[StackFrameSnapshot] = [])"""

    """Call stack state at a resolution boundary.

    Why
    ----
    Provides an event-sourced trace of the call stack so undo/replay can
    rehydrate historical states without trusting serialized ledger payloads.

    Key Features
    ------------
    * **Net state** – records the stack after each step (bottom to top).
    * **Stream friendly** – uses the ``"stack"`` channel for filtering and
      reconstruction.

    API
    ---
    - :attr:`frames` – ordered list of :class:`StackFrameSnapshot` entries.
    """
    frames: list[StackFrameSnapshot] = Field(default_factory=list)


StackSnapshot.model_rebuild()
