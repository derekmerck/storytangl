import uuid

import pytest

from tangl.journal import Journal, JournalItem

#  Tests that a single entry can be added to the journal and retrieved using get_entries
def test_add_single_entry_and_retrieve():
    # Create a Journal instance
    journal = Journal()
    assert len(journal.items) == 0

    # Create a JournalItemModel instance
    entry = JournalItem(uid=uuid.uuid4(), text="Entry 1")

    # Add the entry to the journal
    journal.push_entry(entry)

    assert len(journal.items) == 1

    # Retrieve the entries from the journal
    entries = journal.get_entry()

    # Assert that the retrieved entries contain the added entry
    assert entry in entries

#  Tests that multiple entries can be added to the journal and retrieved using get_entries
def test_add_multiple_entries_and_retrieve():
    # Create a Journal instance
    journal = Journal()

    # Create multiple JournalItemModel instances
    entry1 = JournalItem(uid=uuid.uuid4(), text="Entry 1")
    entry2 = JournalItem(uid=uuid.uuid4(), text="Entry 2")
    entry3 = JournalItem(uid=uuid.uuid4(), text="Entry 3")

    # Add the entries to the journal
    journal.start_new_section("bookmark1")
    journal.push_entry(entry1, entry2, entry3)

    assert entry1 in journal.items
    assert entry2 in journal.items
    assert entry3 in journal.items

    # Retrieve the entries from the journal
    entries = journal.get_section()

    # Assert that the retrieved entries contain all the added entries
    assert entry1 in entries
    assert entry2 in entries
    assert entry3 in entries

    # Retrieve the entries from the journal
    entries = journal.get_section("bookmark1")

    # Assert that the retrieved entries contain all the added entries
    assert entry1 in entries
    assert entry2 in entries
    assert entry3 in entries

# 1. Initialization and attribute checking
def test_initialization():
    journal = Journal()
    assert journal.items == []
    assert journal.section_keys == {}


# 2. Adding entries and retrieving them
def test_add_and_retrieve_entries():
    journal = Journal()

    entry1 = JournalItem(uid=uuid.uuid4(), text="entry1")
    entry2 = JournalItem(uid=uuid.uuid4(), text="entry2")

    journal.push_entry(entry1)
    assert journal.get_section() == [entry1]

    journal.push_entry(entry2)
    assert journal.get_section() == [entry1, entry2]


# 3. Using bookmarks to retrieve entries
def test_bookmarks():
    journal = Journal()

    entry1 = JournalItem(uid=uuid.uuid4(), text="entry1")
    entry2 = JournalItem(uid=uuid.uuid4(), text="entry2")
    entry3 = JournalItem(uid=uuid.uuid4(), text="entry3")

    journal.start_new_section("bookmark1")
    journal.add_item(entry1)
    journal.add_item(entry2)

    journal.start_new_section("bookmark2")
    journal.add_item(entry3)

    assert journal.get_section("bookmark1") == [entry1, entry2]
    assert journal.get_section("bookmark2") == [entry3]


# 4. Checking for errors and edge cases
def test_errors_and_edge_cases():
    journal = Journal()

    # Attempt to add invalid entry
    with pytest.raises(TypeError):
        journal.push_entry(None)

    # Attempt to add invalid entry type
    with pytest.raises(TypeError):
        journal.push_entry("string")

    # Invalid type for start and stop
    with pytest.raises(TypeError):
        journal.get_entry(uuid.uuid4())

    with pytest.raises(KeyError):
        journal.get_section("invalid_section")

def test_idempotent_get_update():
    update_handler = Journal()

    # Add a series of updates
    for i in range(5):
        update_handler.push_entry( JournalItem( uid=uuid.uuid4(), text=f"block{i + 1}" ) )

    # Retrieve the most recent update
    result1 = update_handler.get_entry()

    # Retrieving the update again should give the same result
    result2 = update_handler.get_entry()
    assert result1 == result2

    # Adding a new update and retrieving it should also be idempotent
    update_handler.start_new_section("bookmark1")
    update_handler.push_entry( JournalItem(uid=uuid.uuid4(), text="block6"))
    result3 = update_handler.get_entry()
    result4 = update_handler.get_entry()
    assert result3 == result4
    assert result3 != result2


def test_journal_new_entry_and_update():
    journal = Journal()
    journal.start_new_entry()
    update = JournalItem(uid=uuid.uuid4(), text="Test Update")
    journal.push_entry(update)

    assert journal.get_entry() == [ update ]


def test_journal_get_entry():
    journal = Journal()
    journal.start_new_entry()
    update1 = JournalItem(uid=uuid.uuid4(), text="Update 1")
    journal.add_item(update1)
    update2 = JournalItem(uid=uuid.uuid4(), text="Update 2")
    journal.add_item(update2)

    entry = journal.get_entry()
    assert len(entry) == 2
    assert entry[0] == update1

    journal.start_new_entry()
    update3 = JournalItem(uid=uuid.uuid4(), text="Update 3")
    journal.push_entry(update3)

    entry = journal.get_entry()
    assert len(entry) == 1
    assert entry[0] == update3


def test_journal_get_section():
    journal = Journal()
    journal.start_new_section("foo")
    update1 = JournalItem(uid=uuid.uuid4(), text="Update 1")
    journal.add_item(update1)
    update2 = JournalItem(uid=uuid.uuid4(), text="Update 2")
    journal.add_item(update2)

    entry = journal.get_entry()
    assert len(entry) == 2, 'Should have 2 entries on default request'
    assert entry[0] == update1

    journal.start_new_entry()
    update3 = JournalItem(uid=uuid.uuid4(), text="Update 3")
    journal.add_item(update3)

    entry = journal.get_entry()
    assert len(entry) == 1
    assert entry[0] == update3

    section = journal.get_section()
    assert len(section) == 3

    journal.start_new_section("bar")
    update4 = JournalItem(uid=uuid.uuid4(), text="Update 4")
    journal.add_item(update4)

    section = journal.get_section()
    assert len(section) == 1

    section = journal.get_section('foo')
    assert len(section) == 3

    section = journal.get_section('bar')
    assert len(section) == 1

    entry = journal.get_entry()
    assert len(entry) == 1

    entry = journal.get_entry(0)
    assert len(entry) == 2, 'Entry 0 should retrieve 2 entries'
    assert entry == [update1, update2 ]
