import pytest

from tangl.core.record import Record, StreamRegistry as RecordStream

# --- helpers ---------------------------------------------------------------

def mkrec(rtype: str, **kw) -> Record:
    # extra fields are allowed (frozen, extra="allow"); we commonly use tags/label
    return Record(type=rtype, **kw)

def seqs(it):
    return [r.seq for r in it]

@pytest.fixture(autouse=True)
def _reset_seq():
    Record._reset_instance_count()

# --- basic record behavior -------------------------------------------------

def test_record_is_frozen_and_immutable():
    r = mkrec("patch", label="p1")
    with pytest.raises((AttributeError, TypeError, ValueError)):
        r.label = "mutate"

def test_has_channel_matches_type_and_tag():
    r1 = mkrec("patch", tags={"channel:journal"})
    assert r1.has_channel("patch") is True
    assert r1.has_channel("journal") is True
    assert r1.has_channel("audit") is False

def test_structure_from_dict_uses_alias_type():
    d = {"type": "journal", "label": "j1", "tags": {"x", "channel:journal"}}
    r = Record.structure(d)
    assert isinstance(r, Record)
    assert r.record_type == "journal"
    assert r.has_channel("journal")

# --- stream: seq assignment & add -----------------------------------------

def test_add_record_assigns_monotonic_seq():
    rs = RecordStream()
    rs.add_record(mkrec("journal", label="a"))
    rs.add_record(mkrec("journal", label="b"))
    items = list(rs.find_all(sort_key=lambda x: x.seq))
    assert len(items) == 2
    assert items[0].seq == 0
    assert items[1].seq == 1
    assert rs.max_seq == 1

def test_add_record_accepts_dict_and_assigns_seq():
    rs = RecordStream()
    rs.add_record({"type": "patch", "label": "p"})
    last = rs.last()
    assert last is not None and last.record_type == "patch" and last.seq == 0


def test_find_all_defaults_to_seq_sorting_with_manual_seq_values():
    rs = RecordStream()
    manual = [
        mkrec("journal", label="later", seq=10),
        mkrec("journal", label="first", seq=3),
        mkrec("journal", label="middle", seq=7),
    ]

    for rec in manual:
        rs.add_record(rec)

    ordered = list(rs.find_all())
    assert [r.seq for r in ordered] == sorted(r.seq for r in manual)
    assert [r.label for r in ordered] == ["first", "middle", "later"]

# --- stream  ---------------------------------------

def test_add_single_item():
    rs = RecordStream()
    rec = mkrec("journal", label="a")
    rs.add_record(rec)
    assert len(rs) == 1
    assert list(rs.values()) == [rec]


# --- markers & sections (half-open) ---------------------------------------

def test_push_records_sets_marker_and_returns_half_open_bounds():
    rs = RecordStream()
    a, b, c = mkrec("journal", label="A"), mkrec("patch", label="B"), mkrec("audit", label="C")
    start, end = rs.push_records(a, b, c, marker_type="entry", marker_name="e1")
    # With three records, end should be start+2
    assert end - start == 2
    sec = list(rs.get_section("e1", "entry"))
    assert len(sec) == 3
    assert [r.label for r in sec] == ["A", "B", "C"]
    assert seqs(sec) == [start, start + 1, start + 2]

def test_adjacent_sections_do_not_overlap():
    rs = RecordStream()
    # first entry
    rs.push_records(mkrec("journal", label="e1a"), mkrec("journal", label="e1b"),
                    marker_type="entry", marker_name="e1")
    # second entry
    rs.push_records(mkrec("journal", label="e2a"),
                    marker_type="entry", marker_name="e2")
    s1 = [r.label for r in rs.get_section("e1", "entry")]
    s2 = [r.label for r in rs.get_section("e2", "entry")]
    assert s1 == ["e1a", "e1b"]
    assert s2 == ["e2a"]
    # ensure the first element of s2 is NOT included in s1 (half-open)
    assert "e2a" not in s1

def test_get_section_missing_marker_raises():
    rs = RecordStream()
    with pytest.raises(KeyError):
        list(rs.get_section("nope", "entry"))

# --- slicing with predicate/criteria --------------------------------------

def test_get_slice_with_predicate_and_criteria():
    rs = RecordStream()
    r0 = mkrec("journal", label="a", tags={"channel:journal"})
    r1 = mkrec("patch", label="b", tags={"channel:ops"})
    r2 = mkrec("journal", label="c", tags={"channel:journal"})
    rs.push_records(r0, r1, r2, marker_type="entry", marker_name="e")
    # Half-open: select the middle record only
    mid_seq = rs.max_seq - 1
    sl = list(rs.get_slice(start_seq=mid_seq, end_seq=mid_seq + 1))
    assert len(sl) == 1 and sl[0].label == "b"
    # With predicate: only journal channel
    only_journal = list(rs.get_slice(0, rs.max_seq + 1, predicate=lambda r: r.has_channel("journal")))
    assert [r.label for r in only_journal] == ["a", "c"]

# --- channel & last -------------------------------------------------------

def test_iter_channel_and_last():
    rs = RecordStream()
    rs.add_record(mkrec("journal", label="j1", tags={"channel:journal"}))
    rs.add_record(mkrec("patch", label="p1", tags={"channel:ops"}))
    rs.add_record(mkrec("journal", label="j2", tags={"channel:journal"}))
    ch = list(rs.iter_channel("journal"))
    assert [r.label for r in ch] == ["j1", "j2"]
    last_journal = rs.last(channel="journal")
    assert last_journal.label == "j2"


def test_empty_journal():
    stream = RecordStream()

    assert len(stream) == 0
    assert list(stream.values()) == []
    assert stream.markers == {}

    with pytest.raises(KeyError):
        stream.get_section("notfound")

def test_duplicate_bookmark_raises():
    stream = RecordStream()
    stream.set_marker("chapter1")
    with pytest.raises((KeyError, ValueError)):
        stream.set_marker("chapter1")  # Duplicate name not allowed



# def test_early_stop_section():
#     journal_graph = TestHasJournal()
#     frags1 = make_fragments(2)
#     frags2 = make_fragments(2)
#     journal_graph.add_journal_entry(frags1)
#     journal_graph.start_journal_section("first")
#     journal_graph.add_journal_entry(frags2)
#     journal_graph.start_journal_section("second")
#     # Add another entry (after "second")
#     frags3 = make_fragments(2)
#     journal_graph.add_journal_entry(frags3)
#     # When getting first entry, should stop at "second" section
#     section = journal_graph.get_journal_entry(0)
#     assert len(section) == 2  # Only frags1, as next section is an early stop

