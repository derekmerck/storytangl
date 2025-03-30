import pytest
from tangl.utils.bookmarked_list import BookmarkedList, Bookmark


class TestBookmarkedList:
    def test_empty_list(self):
        blist = BookmarkedList()
        assert len(blist) == 0
        assert blist.get_items() == []
        assert blist.get_bookmarks() == []

    def test_add_single_item(self):
        blist = BookmarkedList[str]()
        blist.add_item("first")
        assert len(blist) == 1
        assert blist.get_items() == ["first"]

    def test_add_item_with_bookmark(self):
        blist = BookmarkedList[str]()
        blist.add_item("first", "intro", "section")

        bookmarks = blist.get_bookmarks()
        assert len(bookmarks) == 1
        assert bookmarks[0].name == "intro"
        assert bookmarks[0].bookmark_type == "section"
        assert bookmarks[0].index == 0

    def test_add_multiple_items(self):
        blist = BookmarkedList[int]()
        blist.add_items([1, 2, 3], "first_batch", "numbers")

        assert len(blist) == 3
        assert blist.get_items() == [1, 2, 3]

        # Check the bookmark was created
        bookmarks = blist.get_bookmarks()
        assert len(bookmarks) == 1
        assert bookmarks[0].name == "first_batch"
        assert bookmarks[0].index == 0

        # Add more items with a new bookmark
        blist.add_items([4, 5],"second_batch", "numbers")
        assert len(blist) == 5
        assert blist.get_items() == [1, 2, 3, 4, 5]

        # Now we should have two bookmarks
        bookmarks = blist.get_bookmarks()
        assert len(bookmarks) == 2
        assert bookmarks[1].name == "second_batch"
        assert bookmarks[1].index == 3

    def test_get_slice_by_index(self):
        blist = BookmarkedList[str]()
        blist.add_items(["a", "b"], "start", "section")
        blist.add_items(["c", "d"], "middle", "section")
        blist.add_items(["e", "f"], "end", "section")

        # Get the first section
        assert blist.get_slice(0, "section") == ["a", "b"]

        # Get the middle section
        assert blist.get_slice(1, "section") == ["c", "d"]

        # Get the last section
        assert blist.get_slice(2, "section") == ["e", "f"]

        # Use negative indexing
        assert blist.get_slice(-1, "section") == ["e", "f"]
        assert blist.get_slice(-2, "section") == ["c", "d"]

    def test_get_slice_by_name(self):
        blist = BookmarkedList[str]()
        blist.add_items(["a", "b"], "start", "section")
        blist.add_items(["c", "d"], "middle", "section")
        blist.add_items(["e", "f"], "end", "section")

        assert blist.get_slice("start", "section") == ["a", "b"]
        assert blist.get_slice("middle", "section") == ["c", "d"]
        assert blist.get_slice("end", "section") == ["e", "f"]

    def test_mixed_bookmark_types(self):
        blist = BookmarkedList[str]()

        # Add chapters and sections
        blist.add_items(["Title page"], "intro", "chapter")
        blist.add_items(["Section 1.1"], "section1.1", "section")
        blist.add_items(["Section 1.2"], "section1.2", "section")
        blist.add_items(["Chapter 2"], "chapter2", "chapter")
        blist.add_items(["Section 2.1"], "section2.1", "section")

        # Get by chapter
        assert blist.get_slice(0, "chapter") == ["Title page", "Section 1.1", "Section 1.2"]
        assert blist.get_slice(1, "chapter") == ["Chapter 2", "Section 2.1"]

        # Get by section
        assert blist.get_slice(0, "section", early_stop_types=["chapter"]) == ["Section 1.1"]
        assert blist.get_slice(1, "section", early_stop_types=["chapter"]) == ["Section 1.2"]
        assert blist.get_slice(2, "section", early_stop_types=["chapter"]) == ["Section 2.1"]

    def test_empty_bookmark_type(self):
        blist = BookmarkedList[str]()
        blist.add_items(["a", "b"])

        # No bookmarks of this type
        assert blist.get_slice(0, "nonexistent") == []

        # Create a bookmark with no type
        blist.set_bookmark("untypedMark")
        assert blist.get_slice("untypedMark", None) == []

    def test_invalid_indices(self):
        blist = BookmarkedList[str]()
        blist.add_items(["a", "b"], "first", "section")

        with pytest.raises(IndexError):
            blist.get_slice(1, "section")  # Only have one bookmark

        with pytest.raises(IndexError):
            blist.get_slice(-2, "section")  # Only have one bookmark

        with pytest.raises(KeyError):
            blist.get_slice("nonexistent", "section")

    def test_find_bookmark_containing(self):
        blist = BookmarkedList[str]()
        blist.add_items(["a", "b"], "first", "section")
        blist.add_items(["c", "d", "e"], "second", "section")

        # Find containing bookmark
        bookmark = blist.find_bookmark_containing(3)
        assert bookmark.name == "second"
        assert bookmark.index == 2

        # Find with type filter
        bookmark = blist.find_bookmark_containing(1, "section")
        assert bookmark.name == "first"

        # No bookmark before the first item
        assert blist.find_bookmark_containing(-1) is None

    def test_duplicate_bookmark_prevention(self):
        blist = BookmarkedList[str]()
        blist.add_item("a", "first", "section")

        # Try to add another bookmark with the same name and type
        with pytest.raises(ValueError):
            blist.set_bookmark("first", "section")

    def test_bookmark_sorting(self):
        blist = BookmarkedList[str]()
        blist.add_item("a", "Z", "section")  # Deliberately out of alphabetical order
        blist.add_item("b", "A", "section")

        # Bookmarks should be sorted by index, not name
        bookmarks = blist.get_bookmarks()
        assert bookmarks[0].name == "Z"
        assert bookmarks[1].name == "A"

    def test_empty_items_list(self):
        blist = BookmarkedList[str]()
        blist.add_items([])  # Empty list, should not fail

        assert len(blist) == 0
