# tangl/core/record/record.py
from __future__ import annotations
import functools
from typing import Optional, Self
import logging
from enum import Enum
from uuid import UUID

from pydantic import Field, ConfigDict

from tangl.type_hints import UnstructuredData, Hash
from tangl.utils.base_model_plus import HasSeq
from tangl.core.entity import Entity
from tangl.core.registry import Registry

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

# note: currently HasSeq uses a different instance counter _per_ class and shares
#       that counter across all sessions/frames regardless of differences in graph
#       or owner. Practically this means that JournalFragment seq's, for example,
#       will be monotonic in creation order, but NOT continuous if any other records
#       are also being generated.

# •	A StreamRegistry is append-only; seq is unique and monotonic.
# •	Sections are half-open: get_section(X) yields seq ∈ [marker(X), next_marker); never overlaps.
# •	Channels are derived—not a separate index: f"channel:{x}" in tags.
# •	Push returns half-open bounds so callers can pass directly to get_slice.
# •	A Record is frozen; mutate by creating a new one.

@functools.total_ordering
class Record(HasSeq, Entity):
    # language=rst
    """
    Record(origin: Entity)

    Immutable runtime artifact.

    Why
    ----
    Records capture *what happened* in a resolution process—events, fragments,
    snapshots—without allowing mutation. They form the audit trail and the
    replayable history of a story.

    Key Features
    ------------
    * **Frozen** – once created, cannot be changed.
    * **Sequenced** – each record has a monotonic :attr:`seq` number.
    * **Channels** – lightweight filtering by :meth:`has_channel`.

    API
    ---
    - :meth:`origin` – dereference to the originating entity
    - :meth:`has_channel` – check membership in a channel

    Notes
    -----
    Records are graph-independent. Use ``.origin(registry)`` to dereference,
    unlike :class:`GraphItem` properties which use implicit ``.graph`` access.
    This asymmetry preserves record immutability and topology independence.
    """
    # records are immutable once created
    model_config = ConfigDict(frozen=True, extra="allow")

    origin_id: Optional[UUID] = None

    def origin(self, registry: Registry[Self]) -> Self:
        # records are not graph-aware (GraphItem), so dereferencing a node id
        # requires a registry
        return registry.get(self.origin_id)

    def has_channel(self, name: str) -> bool:
        return f"channel:{name}" in self.tags
