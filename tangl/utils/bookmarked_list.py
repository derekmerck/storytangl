from typing import Optional, TypeVar, Generic

T = TypeVar("T")


class BookmarkedList(list[T], Generic[T]):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.entries: list[int] = []
        self.bookmarks: dict[str, int] = {}

    def add(self, data: T | list[T], bookmark: Optional[str | list[str]] = None):
        data_index = len(self)
        if isinstance(data, list):
            self.extend(data)
        else:
            self.append(data)
        self.entries.append(data_index)  # record the starting index for this entry
        current_entry = len(self.entries)

        if bookmark:
            if isinstance(bookmark, str):
                bookmarks = {bookmark: current_entry}
            else:
                bookmarks = {k: current_entry for k in bookmark}
            self.bookmarks.update(bookmarks)

    def __getitem__(self, item):
        if isinstance(item, str):
            # It's a bookmark
            entry_index = self.bookmarks[item]
        elif isinstance(item, int):
            entry_index = item
        else:
            raise ValueError("Unknown type for ")

        start_data_index = self.entries[entry_index]
        if entry_index < len(self.entries) - 1:
            end_data_index = self.entries[entry_index + 1]
        else:
            end_data_index = -1
        return self[start_data_index:end_data_index]
