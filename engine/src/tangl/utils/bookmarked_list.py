from typing import Generic, TypeVar, Optional, List, Union, Dict, Iterator
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

T = TypeVar("T")  # List item type
BName = str       # Convenience for arg type ordering
BType = str       # Convenience for arg type ordering

@dataclass(frozen=True)
class Bookmark:
    """Immutable bookmark record with name, type, and index information."""
    name: BName
    bookmark_type: Optional[BType]
    index: int

    def __lt__(self, other):
        """Allow bookmarks to be sorted by index."""
        if not isinstance(other, Bookmark):
            return NotImplemented
        return self.index < other.index


class BookmarkedList(Generic[T]):
    """
    A single list of items, plus a timeline of bookmarks referencing
    item indices, with each bookmark labeled by (type, name).

    Type Parameters:
        T: The type of items stored in the list
        BType: The type of bookmark categories/types
    """

    def __init__(self):
        self._items: list[T] = []
        self._bookmarks: list[Bookmark] = []

    def add_item(
            self,
            item: T,
            bookmark_name: Optional[BName] = None,
            bookmark_type: Optional[BType] = None,
    ) -> None:
        """
        Append a single item to the list. Optionally record a bookmark.

        Args:
            item: The item to add to the list
            bookmark_type: Optional category for the bookmark
            bookmark_name: Optional name for the bookmark

        Raises:
            ValueError: If a bookmark with the same name and type already exists
        """
        start_idx = len(self._items)
        self._items.append(item)

        if bookmark_name is not None:
            self._add_bookmark(bookmark_name, start_idx, bookmark_type)

    def add_items(
            self,
            items: list[T],
            bookmark_name: Optional[BName] = None,
            bookmark_type: Optional[str] = None
    ) -> None:
        """
        Append multiple items at once, create an optional bookmark at their start.

        Args:
            items: List of items to add
            bookmark_type: Optional category for the bookmark
            bookmark_name: Optional name for the bookmark

        Raises:
            ValueError: If a bookmark with the same name and type already exists
        """
        if not items:
            return

        start_idx = len(self._items)
        self._items.extend(items)

        if bookmark_name is not None:
            self._add_bookmark(bookmark_name, start_idx, bookmark_type)

    def set_bookmark(
            self,
            bookmark_name: BName,
            bookmark_type: Optional[BType] = None,
    ) -> None:
        """
        Explicitly mark a bookmark at the current boundary.

        Args:
            bookmark_name: Name for the bookmark
            bookmark_type: Optional category for the bookmark

        Raises:
            ValueError: If a bookmark with the same name and type already exists
        """
        start_idx = len(self._items)
        self._add_bookmark(bookmark_name, start_idx, bookmark_type)

    def _add_bookmark(
            self,
            bookmark_name: BName,
            index: int,
            bookmark_type: Optional[BType] = None,
    ) -> None:
        """
        Internal method to add a bookmark with validation.

        Args:
            bookmark_name: Name for the bookmark
            bookmark_type: Optional category for the bookmark
            index: Position in the item list

        Raises:
            ValueError: If a bookmark with the same name and type already exists
        """
        # Check for duplicates
        if bookmark_name in [b.name for b in self._bookmarks]:
            raise ValueError(f"Bookmark with name '{bookmark_name}' already exists")

        bookmark = Bookmark(name=bookmark_name, bookmark_type=bookmark_type, index=index)
        self._bookmarks.append(bookmark)
        # Ensure monotonicity on add, bookmarks order by index
        self._bookmarks.sort()

    def get_bookmarks(self, bookmark_type: BType = None) -> list[Bookmark]:
        """
        Get all bookmarks, optionally filtered by type.

        Args:
            bookmark_type: Optional type to filter by

        Returns:
            List of bookmarks, sorted by index
        """
        if bookmark_type is None:
            return self._bookmarks
        return list(filter(lambda x: x.bookmark_type == bookmark_type, self._bookmarks))

    def get_slice(
            self,
            which: Union[int, BName] = -1,
            bookmark_type: Optional[BType] = None,
            early_stop_types: Optional[list[BType]] = None,
    ) -> List[T]:
        """
        Retrieve the slice of items from a specific bookmark of `bookmark_type`.

        Args:
            which: If int => index among bookmarks of this type (negative ok)
                   If str => named bookmark for the type
            bookmark_type: Optional category to filter bookmarks
            early_stop_types: Optional list of container categories that provide
                   an ending edge for a bookmark section

        Returns:
            List of items from the specified bookmark to the next bookmark of
            the same type or the end of items.

        Raises:
            IndexError: If an integer index is out of range
            KeyError: If a string name doesn't match any bookmark of the specified type
        """
        bookmarks = self.get_bookmarks(bookmark_type=bookmark_type)

        if not bookmarks:
            logger.debug(f"No such bookmark type {bookmark_type}")
            return []

        # Find the bookmark
        if isinstance(which, int):
            # Handle negative indices
            if which < 0:
                which = len(bookmarks) + which

            if which < 0 or which >= len(bookmarks):
                raise IndexError(f"Bookmark index {which} out of range for type {bookmark_type}")

            bookmark = bookmarks[which]
            selected_idx = which

            logger.debug(f"Final which: {which}")

        else:  # which is a name

            bookmark = None
            selected_idx = None
            for idx, b in enumerate(bookmarks):
                if b.name == which:
                    selected_idx = idx
                    bookmark = b
                    break

            if not bookmark:
                raise KeyError(f"No bookmark named '{which}' for type '{bookmark_type}'")

        # Find the next bookmark of the same type
        if selected_idx + 1 < len(bookmarks):
            next_bookmark = bookmarks[selected_idx + 1]
            end_idx = next_bookmark.index
        else:
            end_idx = len(self._items)

        logger.debug(f"Working range for {bookmark_type, which}: {selected_idx}:{end_idx}")

        # check for earlier stop indices, such as for sections ending at chapter edges
        for sbt in early_stop_types or []:
            if sbt == bookmark_type:
                logger.warning(f"Setting an early stop type {sbt} to the same thing as the bookmark type is harmless, but probably not what you meant to do.")
            # list bookmarks of this type
            sbt_bookmarks = self.get_bookmarks(bookmark_type=sbt)
            logger.debug("sbt_bookmarks: %s", sbt_bookmarks)

            # consider them in reverse order, similar to "find bookmark containing",
            # we want to find any container _edge_ between the bookmark index and the
            # end_idx
            for bm in reversed(sbt_bookmarks):
                # if this bookmark index > end_idx, it's irrelevant
                if bm.index >= end_idx or bm.index <= bookmark.index:
                    logger.debug(f"skipping out of range ({bm.index} for {bm.name}")
                    pass
                # otherwise, if this bookmark index < end_index, it's the _first_
                # early end of this type, if we break, we can skip the rest
                else:
                    logger.debug(f"first container edge in range ({bm.index}) for {bm.name}")
                    end_idx = bm.index
                    break

        return self._items[bookmark.index:end_idx]

    def get_items(self) -> List[T]:
        """Return the entire list of items."""
        return self._items.copy()

    def find_bookmark_containing(self, index: int, bookmark_type: Optional[str] = None) -> Optional[Bookmark]:
        """
        Find the most recent bookmark that contains the given index.

        Args:
            index: The item index to look for
            bookmark_type: Optional type to filter by

        Returns:
            The bookmark, or None if no matching bookmark found
        """
        bookmarks = self.get_bookmarks(bookmark_type=bookmark_type)

        for bookmark in reversed(bookmarks):
            if bookmark.index <= index:
                return bookmark

        return None

    def __len__(self) -> int:
        """Return the number of items in the list."""
        return len(self._items)

    def __iter__(self) -> Iterator[T]:
        """Iterate through all items."""
        return iter(self._items)
