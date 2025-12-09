from __future__ import annotations
from typing import Optional, TypeVar, Iterator, Callable
import logging

from pydantic import Field

from tangl.type_hints import UnstructuredData
from tangl.utils.base_model_plus import HasSeq
from tangl.core.registry import Registry
from .record import Record

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

RecordT = TypeVar('RecordT', bound=Record)


class StreamRegistry(Registry[HasSeq]):
    # language=rst
    """
    StreamRegistry(data: dict[~uuid.UUID, Record])

    Append-only ordered stream of :class:`Record`.

    Why
    ----
    Provides temporal ordering and bookmark semantics for records, enabling
    logs, journals, and patches to be stored and queried without ambiguity.
    A single stream can be hierarchically segmented into chapters, sections,
    entries, and other logical units by using typed markers.

    Key Features
    ------------
    * **Monotonic seq** – strict temporal order within the stream; sequence
      numbers come from :class:`HasSeq` and are monotonically increasing.
    * **Bookmarks** – mark boundaries with :meth:`set_marker`, using
      ``marker_type`` as a namespace (e.g., ``"chapter"``, ``"section"``,
      ``"entry"``) so the same logical name (``"start"``, ``"latest"``)
      can be reused at multiple levels.
    * **Slices** – extract intervals with :meth:`get_slice` and
      :meth:`get_section`, combining sequence ranges with normal match
      criteria.
    * **Channels via tags** – logical substreams can be filtered with
      normal registry criteria, e.g. ``is_instance=BaseFragment`` and
      ``has_channel="journal"`` (sugar for a ``"channel:journal"`` tag).

    API
    ---
    - :meth:`add_record` / :meth:`push_records`
    - :meth:`get_section(**criteria)<get_section>` – retrieve a section
      between typed markers
    - :meth:`last(**criteria)<last>` – last matching record
    """

    markers: dict[str, dict[str, int]] = Field(default_factory=dict)
    max_seq: int = -1

    def find_all(self, sort_key: Callable[[RecordT], object] | None = None, **criteria) -> Iterator[RecordT]:
        # language=rst
        """Iterate over records matching ``criteria`` sorted by ``seq`` by default."""

        effective_sort_key = sort_key or (lambda record: record.seq)
        yield from super().find_all(sort_key=effective_sort_key, **criteria)

    # Only useful b/c contents are always sorted
    def last(self, **criteria) -> Optional[Record]:
        # language=rst
        """Last by seq that matches criteria."""
        return max(self.find_all(**criteria), default=None)

    def _ensure_seq(self, item: RecordT) -> RecordT:
        # If seq is missing or negative, assign next.
        seq = getattr(item, "seq", None)
        if seq is None or not isinstance(seq, int) or seq <= self.max_seq:
            return item.model_copy(update={"seq": self.max_seq + 1})
        return item

    # ---- bookmarks ----

    def set_marker(
        self,
        marker_name: str,
        marker_type: str = '_',
        marker_seq: int | None = None,
        *,
        overwrite: bool = False,
    ) -> None:
        # language=rst
        """Bookmark a sequence position for ``marker_name`` under ``marker_type``.

        Markers are stored as ``markers[marker_type][marker_name] = seq`` and
        provide named boundaries for later slicing.

        Parameters
        ----------
        marker_name:
            Logical name for the bookmark (e.g., ``"start"``, ``"choice-17"``).
            Names are local to a ``marker_type``; you can reuse the same name
            under different types (e.g., ``"start"`` for both ``"chapter"``
            and ``"section"`` markers).
        marker_type:
            Namespace for the bookmark. Separates independent marker streams
            such as ``"chapter"``, ``"section"``, or ``"entry"``. This allows
            hierarchical segmentation of the same underlying stream; for
            example, a single fragment log can be cut into chapters, within
            which sections, within which individual entries.
        marker_seq:
            Sequence index to record. If ``None``, the marker is placed at
            ``self.max_seq + 1``, i.e., *just after* the last appended record.
            This is useful when you want to mark the start of the *next*
            region before appending more records. To mark the start of an
            existing batch, pass its first record's ``seq`` explicitly (as
            :meth:`push_records` does).
        overwrite:
            When ``True``, replace an existing marker of the same name within
            the same type instead of raising. Useful for sliding bookmarks
            like ``"latest"`` or ``"cursor"``.
        """
        if marker_seq is None:
            marker_seq = self.max_seq + 1
            # be careful about 1-off errors!  Set the marker _before_ appending
        logger.debug(f"Adding marker: {marker_name}@{marker_type} to {marker_seq}")
        if marker_type not in self.markers:
            self.markers[marker_type] = {}
        if not overwrite and marker_name in self.markers[marker_type]:
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

    def get_slice(self, start_seq: int, end_seq: int, *, predicate=None, **criteria) -> Iterator[RecordT]:
        def _predicate(record: RecordT) -> bool:
            if not start_seq <= record.seq < end_seq:
                return False
            if predicate is not None and not predicate(record):
                return False
            return True
        # HasSeq has a built-in `__lt__` so a bare `sorted(values)` works, but passing a
        # sort_key kwarg explicitly into find_all will also internally sort and yield
        # from the sorted list
        return self.find_all(predicate=_predicate, **criteria)

    # Prior ref - early stop types entry << section << chapter << book, etc.
    # def get_entry(self, which=-1) -> list[Record]:
    #     # early stop types param looks for terminating section edges, as well
    #     items = self.journal.get_slice(which, bookmark_type="entry", early_stop_types=["section"])
    #     return [self.get(uid) for uid in items]

    def get_section(self, marker_name: str, marker_type: str = '_', **criteria) -> Iterator[RecordT]:
        # language=rst
        """
        Iterate over records between a named marker and the next marker
        of the same type.

        Sections are half-open intervals in sequence space:

        * Start at the sequence stored in ``markers[marker_type][marker_name]``.
        * End at the next higher marker of the same ``marker_type``, or at
          ``max_seq + 1`` if there is no later marker of that type.

        Special case
        ------------
        If ``marker_name == "latest"``, the section starts at the most
        recently set marker of the given ``marker_type`` (i.e., the marker
        whose recorded seq is maximal for that type).

        This is typically combined with normal registry criteria, e.g.::

            stream.get_section("latest", "entry",
                               is_instance=BaseFragment,
                               has_channel="journal")

        to retrieve "the most recent entry section of journal fragments".
        """
        md = self.markers.get(marker_type) or {}
        if not md:
            raise KeyError(f"{marker_name}@{marker_type} not found")

        # Allow a sentinel name to always refer to the most recently set marker of this type.
        if marker_name == "latest":
            # pick the marker with the greatest seq; seq is monotonic for this stream
            marker_name, start = max(md.items(), key=lambda kv: kv[1])
        else:
            if marker_name not in md:
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

    def slice_to_seq(self, max_seq: int) -> StreamRegistry:
        """Copy records up to and including ``max_seq`` into a new stream."""

        truncated = StreamRegistry()
        truncated.markers = {
            marker_type: {name: seq for name, seq in markers.items() if seq <= max_seq}
            for marker_type, markers in self.markers.items()
        }

        for record in self.find_all(predicate=lambda item: item.seq <= max_seq):
            truncated.add_record(record)

        return truncated

    def remove(*args, **kwargs):
        raise NotImplementedError("Cannot remove records from a StreamRegistry.")
