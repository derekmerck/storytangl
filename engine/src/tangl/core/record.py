# tangl.core.record.py
from __future__ import annotations
import functools
from typing import Optional, TypeVar, Self, Iterator
import logging
from enum import Enum
from uuid import UUID

from pydantic import Field, ConfigDict

from tangl.type_hints import UnstructuredData
from tangl.utils.base_model_plus import HasSeq
from tangl.core.entity import Entity
from tangl.core.registry import Registry

logger = logging.getLogger(__name__)

# note: currently HasSeq uses a different instance counter _per_ class and shares
#       that counter across all sessions/frames regardless of differences in graph
#       or owner. Practically this means that JournalFragment seq's, for example,
#       will be monotonic in creation order, but NOT continuous if any other records
#       are also being generated.

# •	A RecordStream is append-only; seq is unique and monotonic.
# •	Sections are half-open: get_section(X) yields seq ∈ [marker(X), next_marker); never overlaps.
# •	Channels are derived—not a separate index: record_type == x or f"channel:{x}" in tags.
# •	Push returns half-open bounds so callers can pass directly to get_slice.
# •	A Record is frozen; mutate by creating a new one.

@functools.total_ordering
class Record(HasSeq, Entity):
    """
    Record(record_type: str, blame: Entity)

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
    - :meth:`blame` – dereference to the originating entity
    - :meth:`has_channel` – check membership in a channel
    """
    # records are immutable once created
    model_config = ConfigDict(frozen=True, extra="allow")

    record_type: str | Enum = Field(..., alias='type')
    blame_id: Optional[UUID] = None

    def blame(self, registry: Registry[Self]) -> Self:
        # records are not graph-aware (GraphItem), so dereferencing a node id
        # requires a registry
        return registry.get(self.blame_id)

    @classmethod
    def structure(cls, data: UnstructuredData) -> Self:
        # todo: actually want to use discriminated union to assemble the
        #       correct type by record_type
        #       Or is obj_cls sufficient?  We don't do much with multiple rec_type
        #       pointing to the same object cls
        return super().structure(data)

    def has_channel(self, name: str) -> bool:
        return self.record_type == name or f"channel:{name}" in self.tags

RecordT = TypeVar('RecordT', bound=Record)


class StreamRegistry(Registry[HasSeq]):
    """
    StreamRegistry(data: dict[~uuid.UUID, Record])

    Append-only ordered stream of :class:`Record`.

    Why
    ----
    Provides temporal ordering and bookmark semantics for records, enabling
    logs, journals, and patches to be stored and queried without ambiguity.

    Key Features
    ------------
    * **Monotonic seq** – strict temporal order.
    * **Bookmarks** – mark sections with :meth:`set_marker`.
    * **Slices** – extract intervals with :meth:`get_slice`.
    * **Channels** – filter logical streams with :meth:`iter_channel`.

    API
    ---
    - :meth:`add_record` / :meth:`push_records`
    - :meth:`get_section(**criteria)<get_section>` – retrieve bookmarked section
    - :meth:`iter_channel` – iterate filtered records
    - :meth:`last(**criteria)<last>` – last matching record
    """

    markers: dict[str, dict[str, int]] = Field(default_factory=dict)
    max_seq: int = 0

    def _ensure_seq(self, item: RecordT) -> RecordT:
        # If seq is missing or negative, assign next.
        seq = getattr(item, "seq", None)
        if seq is None or (isinstance(seq, int) and seq < 0):
            return item.model_copy(update={"seq": self.max_seq + 1})
        return item

    # ---- bookmarks ----

    def set_marker(self, marker_name: str, marker_type: str = '_', marker_seq: int = None):
        if marker_seq is None:
            marker_seq = self.max_seq
        logger.debug(f"Adding marker: {marker_name}@{marker_type} to {marker_seq}")
        if marker_type not in self.markers:
            self.markers[marker_type] = {}
        if marker_name in self.markers[marker_type]:
            raise KeyError(f"Marker {marker_name} already exists")
        self.markers[marker_type][marker_name] = marker_seq

    def _next_marker_seq(self, start_seq: int, marker_type: str = "_") -> int:
        """Find the next marker (by seq) of the same type; else end at max_seq."""
        md = self.markers.get(marker_type, {})
        if not md:
            return self.max_seq
        # sort all seqs of this type and pick the first strictly greater than start_seq
        next_seqs = sorted(s for s in md.values() if s > start_seq)
        return next_seqs[0] if next_seqs else self.max_seq + 1

    # ---- slicing ----

    # def get_slice(self, start_seq: int = 0, end_seq: Optional[int] = None, *, inclusive_start: bool = True) -> list[Record]:
    #     """Return records with start_seq <= seq < end_seq (default end = max)."""
    #     end_seq = self._max_seq + 1 if end_seq is None else end_seq
    #     lo = (lambda x: x.seq >= start_seq) if inclusive_start else (lambda x: x.seq > start_seq)
    #     hi = (lambda x: x.seq < end_seq)
    #     return sorted((r for r in self.values() if lo(r) and hi(r)), key=lambda r: r.seq)

    def get_slice(self, start_seq: int, end_seq: int, *, predicate=None, **criteria) -> Iterator[RecordT]:
        def _predicate(record: RecordT) -> bool:
            if not start_seq <= record.seq < end_seq:
                return False
            if predicate is not None and not predicate(record):
                return False
            return True
        # HasSeq has a built-in __lt__ so a bare sort(values) works, but passing the
        # sort_key kwarg explicitly into find_all will also internally sort and yield
        # from the sorted list
        return self.find_all(predicate=_predicate, **criteria, sort_key=lambda x: x.seq)

    # def get_entry(self, which=-1) -> list[Record]:
    #     # early stop types param looks for terminating section edges, as well
    #     items = self.journal.get_slice(which, bookmark_type="entry", early_stop_types=["section"])
    #     return [self.get(uid) for uid in items]

    def get_section(self, marker_name: str, marker_type: str = '_', **criteria) -> Iterator[RecordT]:
        md = self.markers.get(marker_type)
        if not md or marker_name not in md:
            raise KeyError(f"{marker_name}@{marker_type} not found")
        start = md[marker_name]
        end = self._next_marker_seq(start, marker_type)
        logger.debug(f"{marker_name}@{marker_type} start: {start} end: {end}")
        return self.get_slice(start_seq=start, end_seq=end, **criteria)

    # ---- add/push ----

    def add_record(self, item: Record | UnstructuredData):
        if isinstance(item, dict):
            item = Record.structure(item)
        if not isinstance(item, Record):
            raise ValueError(f"Trying to add wrong type {type(item)} to record stream")
        item = self._ensure_seq(item)
        self.max_seq = max(self.max_seq, item.seq)
        self.add(item)

    def push_records(
            self,
            *items: Record | UnstructuredData,
            marker_type: str = "entry",
            marker_name: Optional[str] = None,
    ) -> tuple[int, int]:
        """
        Append a batch atomically and mark the start with a bookmark.
        Returns (start_seq, end_seq_inclusive).
        """
        if not items:
            logger.warning("No-op push to record stream.")
            return self.max_seq, self.max_seq

        # normalize & compute start
        normalized: list[Record] = []
        for it in items:
            if isinstance(it, dict):
                it = Record.structure(it)
            it = self._ensure_seq(it)
            normalized.append(it)
        start_seq = min(normalized).seq
        logger.debug(f"normalized: {[r.seq for r in sorted(normalized)]}")

        for it in normalized:
            self.add_record(it)

        # bookmark
        # Use the first fragment's label or short uid to create a unique marker
        # name for iterating over groups
        first_label = normalized[0].get_label() or f"seq{start_seq}"
        name = marker_name or first_label
        self.set_marker(name, marker_type, start_seq)

        return start_seq, self.max_seq

    # ---- channel/criteria convenience ----

    def iter_channel(self, channel: str, **criteria) -> Iterator[Record]:
        """
        Filter by the effective channel.  Matches record_type or has
        'channel:x' tag by default.

        Same as find_all(has_channel=x, **criteria)
        """
        if channel is not None:
            criteria.setdefault('has_channel', channel)
        yield from self.find_all(**criteria, sort_key=lambda x: x.seq)

    def last(self, channel: str = None, **criteria) -> Optional[Record]:
        """Last by seq that matches criteria."""
        if channel is not None:
            criteria.setdefault('has_channel', channel)
        return max(self.find_all(**criteria, sort_key=lambda x: x.seq), default=None)

    # todo: we will also want something like last_marked(marker_type), which gets
    #       everything from the last marker of that type up to the end, like the last
    #       frame entry.

    def remove(*args, **kwargs):
        raise NotImplementedError("Cannot remove records from a StreamRegistry.")
