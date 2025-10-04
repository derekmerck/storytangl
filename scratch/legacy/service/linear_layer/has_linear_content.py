import functools

from tangl.utils.bookmarked_list import BookmarkedList, BName, BType
from tangl.core.fragment import ContentFragment

class HasLinearContent():
    # todo: want to tie together with linear history layer updates

    @functools.wraps(BookmarkedList[ContentFragment].add_items)
    def add_content(self, items: list[dict], bookmark_name: BName = None, bookmark_type: BType = None, **kwargs) -> None:
        fragments = [ ContentFragment(**item) for item in items ]
        self.linear_layer.add_items(fragments, bookmark_name=bookmark_name, bookmark_type=bookmark_type)

    @functools.wraps(BookmarkedList[ContentFragment].get_slice)
    def get_content(self, *args, **kwargs) -> None:
        self.fragment_layer.get_slice(*args, **kwargs)
