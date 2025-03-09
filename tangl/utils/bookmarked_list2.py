from typing import Generic, TypeVar, Optional, List, Tuple, NewType
T = TypeVar("T")

BType = str
BName = str

from collections import namedtuple

Bookmark = namedtuple("Bookmark", ["name", "type", "index"])

class UniversalBookmarkedList(Generic[T]):
    """
    A single list of items, plus a single timeline of bookmarks
    referencing item indices, with each bookmark labeled by (type, name).
    """

    def __init__(self):
        self._items: list[T] = []
        # each bookmark: (name: str, btype: Optional[str], start_index: int)
        self._bookmarks: list[Bookmark[BName, Optional[BType], int]] = []

    def add_item(
        self,
        item: T,
        bookmark_type: Optional[BType] = None,
        bookmark_name: Optional[BName] = None
    ) -> None:
        """Append a single item to the list. Optionally record a bookmark."""
        start_idx = len(self._items)
        self._items.append(item)
        if bookmark_name is not None:
            self._bookmarks.append(Bookmark(bookmark_name, bookmark_type, start_idx))
        # _bookmarks is strictly in ascending order by start_idx

    def add_items(
        self,
        items: list[T],
        bookmark_type: Optional[BType] = None,
        bookmark_name: Optional[BName] = None
    ) -> None:
        """Append multiple items at once, create an optional bookmark at their start."""
        start_idx = len(self._items)
        self._items.extend(items)
        if bookmark_name is not None:
            # The bookmark references the position before these new items
            self._bookmarks.append(Bookmark(bookmark_name, bookmark_type, start_idx))

    def set_bookmark(
        self,
        bookmark_type: BType,
        bookmark_name: BName,
    ):
        """Explicitly mark a bookmark at the current boundary."""
        start_idx = len(self._items)
        self._bookmarks.append(Bookmark(bookmark_name, bookmark_type, start_idx))

    def get_slice(
        self,
        which: int | str = -1,
        bookmark_type: Optional[BType] = None,
    ) -> List[T]:
        """
        Retrieve the slice of items from a specific bookmark of `bookmark_type`.
        If `which` is int => interpret as an index among that type's bookmarks (negative ok).
        If `which` is str => interpret as the named bookmark for that type.
        The slice goes from that bookmark's start_index to the next bookmark with the
        same type or the end of items if none.
        """
        # 1) gather all bookmarks of this type, in ascending item index
        typed_bmarks = [(b.index, b.name) for b in self._bookmarks if b.type == bookmark_type]
        if not typed_bmarks:
            return []

        # 2) find the "which" bookmark
        if isinstance(which, int):
            # handle negative
            if which < 0:
                which = len(typed_bmarks) + which
            if which < 0 or which >= len(typed_bmarks):
                raise IndexError(f"Bookmark index {which} out of range for type {bookmark_type}")
            start_idx, name = typed_bmarks[which]
            typed_index = which
        else:
            # which is a str => find the matching named bookmark
            typed_index = None
            start_idx = None
            for idx, (i, nm) in enumerate(typed_bmarks):
                if nm == which:
                    typed_index = idx
                    start_idx = i
                    break
            if typed_index is None:
                raise KeyError(f"No bookmark named {which} for type {bookmark_type}")

        # 3) find the next same-type bookmark or end
        if typed_index + 1 < len(typed_bmarks):
            next_start = typed_bmarks[typed_index + 1][0]
        else:
            next_start = len(self._items)

        return self._items[start_idx:next_start]

    def get_items(self) -> list[T]:
        """Return the entire list if needed."""
        return self._items
