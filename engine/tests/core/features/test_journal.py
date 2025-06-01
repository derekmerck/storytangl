import pytest
from uuid import uuid4, UUID
from dataclasses import dataclass
from tangl.utils.bookmarked_list import BookmarkedList
from tangl.core.features.feature_nodes import ContentFragment
from tangl.core.features.journal import HasJournal

class TestHasJournal(HasJournal):
    # Inherit everything, no change needed for test
    pass

def make_fragments(n, kind="text"):
    return [ContentFragment(uid=uuid4(),
                            content_type=kind,
                            label=f"Frag {i}",
                            content=f"Content {i}") for i in range(n)]

def test_add_single_item():
    journal_graph = TestHasJournal()
    journal_graph.journal.add_item("first")
    assert len(journal_graph.journal) == 1
    assert journal_graph.journal.get_items() == ["first"]

def test_add_single_entry():
    journal_graph = TestHasJournal()
    frags = make_fragments(1)
    journal_graph.add_journal_entry(frags)
    assert len(journal_graph.journal) == 1
    for f in frags:
        assert f.uid in journal_graph.journal

    assert 'entry' in [b.bookmark_type for b in journal_graph.journal._bookmarks], f"Bookmark type 'entry' should exist in {journal_graph.journal._bookmarks}"

    assert journal_graph.journal.get_slice(bookmark_type="abc") == []
    last_entry = journal_graph.journal.get_slice(bookmark_type="entry")
    assert len(last_entry) == 1

    entry = journal_graph.get_journal_entry()
    assert len(entry) == 1
    for f in frags:
        assert f in entry

def test_add_and_retrieve_entry():
    journal_graph = TestHasJournal()
    frags = make_fragments(3)
    journal_graph.add_journal_entry(frags)
    # Fragments should be in registry
    for f in frags:
        assert journal_graph.get(f.uid) == f, "Fragments should be in registry"

    assert len(journal_graph.journal) == 3
    for f in frags:
        assert f.uid in journal_graph.journal, "Fragments should be in view"

    # Entries should be retrievable
    entry = journal_graph.get_journal_entry()
    assert len(entry) == 3
    assert all(isinstance(f, ContentFragment) for f in entry)

def test_section_bookmark_and_slice():
    journal_graph = TestHasJournal()
    frags1 = make_fragments(2)
    frags2 = make_fragments(2, kind="summary")
    journal_graph.add_journal_entry(frags1)
    journal_graph.start_journal_section("start")
    journal_graph.add_journal_entry(frags2)
    journal_graph.start_journal_section("mid")
    # Section "start" should only include the UIDs after the bookmark
    section1 = journal_graph.get_journal_section("start")
    # Should include the two summary fragments (frags2)
    assert len(section1) == 2
    assert section1[0].content_type == "summary"
    assert section1[1].content_type == "summary"

def test_multiple_entries_and_sections():
    journal_graph = TestHasJournal()
    all_frags = []
    for i in range(3):
        frags = make_fragments(2, kind=f"kind{i}")
        all_frags.extend(frags)
        journal_graph.add_journal_entry(frags)
        journal_graph.start_journal_section(f"sec{i}")

    # Should be able to retrieve last entry (the last two frags)
    last_entry = journal_graph.get_journal_entry(-1)
    assert len(last_entry) == 2
    assert last_entry[0].content_type == "kind2"
    # Retrieve a named section by its bookmark
    sec1 = journal_graph.get_journal_section("sec1")
    # Should get the two fragments added after sec1
    assert len(sec1) == 2
    assert sec1[0].content_type == "kind2"

def test_duplicate_bookmark_raises():
    journal_graph = TestHasJournal()
    journal_graph.start_journal_section("chapter1")
    with pytest.raises(ValueError):
        journal_graph.start_journal_section("chapter1")  # Duplicate name not allowed

def test_early_stop_section():
    journal_graph = TestHasJournal()
    frags1 = make_fragments(2)
    frags2 = make_fragments(2)
    journal_graph.add_journal_entry(frags1)
    journal_graph.start_journal_section("first")
    journal_graph.add_journal_entry(frags2)
    journal_graph.start_journal_section("second")
    # Add another entry (after "second")
    frags3 = make_fragments(2)
    journal_graph.add_journal_entry(frags3)
    # When getting first entry, should stop at "second" section
    section = journal_graph.get_journal_entry(0)
    assert len(section) == 2  # Only frags1, as next section is an early stop

def test_empty_journal():
    journal_graph = TestHasJournal()

    assert len(journal_graph.journal) == 0
    assert journal_graph.journal.get_items() == []
    assert journal_graph.journal.get_bookmarks() == []

    assert journal_graph.get_journal_entry() == []
    assert journal_graph.get_journal_section("notfound") == []

