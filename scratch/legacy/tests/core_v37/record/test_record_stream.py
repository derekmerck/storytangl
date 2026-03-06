import logging
from typing import Type

import pytest

from tangl.core import BaseFragment, Graph
from tangl.core.behavior import CallReceipt
from tangl.core.entity import Entity
from tangl.core.record import Record, Snapshot, StreamRegistry as RecordStream
from tangl.core.registry import Registry
from tangl.vm.replay.event import Event, EventType
from tangl.vm.replay.patch import Patch

# --- helpers ---------------------------------------------------------------

def mkrec(obj_cls: Type[Record] = Record, **kw) -> Record:
    # extra fields are allowed (frozen, extra="allow"); we commonly use tags/label
    return obj_cls.structure(kw)

def seqs(it):
    return [r.seq for r in it]

@pytest.fixture(autouse=True)
def _reset_seq():
    Record._reset_instance_count()

class Patch(Record): ...
class Audit(Record): ...
class Journal(Record): ...

# --- basic record behavior -------------------------------------------------

def test_record_is_frozen_and_immutable():
    r = mkrec(Patch, label="p1")
    with pytest.raises((AttributeError, TypeError, ValueError)):
        r.label = "mutate"

class Dummy(Entity):
    value: int = 0

def test_record_blame_dereferences_entity():

    registry: Registry = Registry()
    blamed = Dummy(label="blamed", value=7)
    registry.add(blamed)

    record = mkrec(Audit, label="audit1", origin_id=blamed.uid)
    assert record.origin(registry) is blamed

def test_has_channel_matches_type_and_tag():
    r1 = mkrec(Patch, tags={"channel:journal"})
    # assert r1.has_channel("patch") is True
    assert isinstance(r1, Patch)
    assert r1.has_channel("journal") is True
    assert r1.has_channel("audit") is False

def test_structure_from_dict_uses_alias_type():
    d = {"obj_cls": Journal, "label": "j1", "tags": {"x", "channel:journal"}}
    r = Record.structure(d)
    assert isinstance(r, Record)
    assert r.has_channel("journal")

# --- stream: seq assignment & add -----------------------------------------

def test_add_record_assigns_monotonic_seq():
    rs = RecordStream()
    rs.add_record(mkrec(Journal, label="a"))
    rs.add_record(mkrec(Journal, label="b"))
    items = list(rs.find_all())
    assert len(items) == 2
    assert items[0].seq < items[1].seq

def test_add_record_normalizes_missing_and_negative_seq():
    rs = RecordStream()
    negative = mkrec(Journal, label="neg").model_copy(update={"seq": -10})
    missing = mkrec(Journal, label="missing").model_copy(update={"seq": None})

    rs.add_record(negative)
    rs.add_record(missing)

    ordered = list(rs.find_all())
    assert ordered[0].seq < ordered[1].seq
    assert [rec.label for rec in ordered] == ["neg", "missing"]

def test_add_record_accepts_dict_and_assigns_seq():
    rs = RecordStream()
    rs.add_record({"obj_cls": Patch, "label": "p"})
    last = rs.last()
    assert last is not None and isinstance(last, Patch)

def test_add_record_reassigns_duplicate_or_invalid_seq():
    rs = RecordStream()
    first = mkrec(Journal, label="a")
    rs.add_record(first)

    duplicate = mkrec(Journal, label="b").model_copy(update={"seq": 0})
    rs.add_record(duplicate)

    ordered = list( rs.find_all() )
    assert ordered[0].seq < ordered[1].seq
    assert [r.get_label() for r in ordered] == ["a", "b"]
    # assert rs.max_seq ==  1

# --- stream  ---------------------------------------

def test_add_single_item():
    rs = RecordStream()
    rec = mkrec(Journal, label="a")
    rs.add_record(rec)
    assert len(rs) == 1
    assert list(rs.values()) == [rec]


def test_add_record_validation_and_push_behaviors(caplog):
    rs = RecordStream()

    with pytest.raises(ValueError):
        rs.add_record(object())

    with caplog.at_level(logging.WARNING):
        start_end = rs.push_records()
    assert start_end == (-1, -1)
    assert "No-op push to record stream." in caplog.text

    rs.push_records({"obj_cls": Journal, "label": "dict"})
    last = rs.last()
    assert last is not None and isinstance(last, Journal) and last.label == "dict"


# --- markers & sections (half-open) ---------------------------------------

def test_push_records_sets_marker_and_returns_half_open_bounds():
    rs = RecordStream()
    a, b, c = mkrec(Journal, label="A"), mkrec(Patch, label="B"), mkrec(Audit, label="C")
    start, end = rs.push_records(a, b, c, marker_type="entry", marker_name="e1")
    # # With three records, end should be start+2
    # assert end - start == 2
    sec = list(rs.get_section("e1", "entry"))
    assert len(sec) == 3
    assert [r.label for r in sec] == ["A", "B", "C"]
    # assert seqs(sec) == [start, start + 1, start + 2]

def test_adjacent_sections_do_not_overlap():
    rs = RecordStream()
    # first entry
    rs.push_records(mkrec(Journal, label="e1a"), mkrec(Journal, label="e1b"),
                    marker_type="entry", marker_name="e1")
    # second entry
    rs.push_records(mkrec(Journal, label="e2a"),
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
    r0 = mkrec(Journal, label="a", tags={"channel:journal"})
    r1 = mkrec(Patch, label="b", tags={"channel:ops"})
    r2 = mkrec(Journal, label="c", tags={"channel:journal"})
    rs.push_records(r0, r1, r2, marker_type="entry", marker_name="e")
    # Half-open: select the middle record only
    mid_seq = rs.max_seq - 1
    sl = list(rs.get_slice(start_seq=mid_seq, end_seq=mid_seq + 1))
    assert len(sl) == 1 and sl[0].label == "b"
    # With predicate: only journal channel
    only_journal = list(rs.get_slice(0, rs.max_seq + 1, predicate=lambda r: isinstance(r, Journal)))
    assert [r.label for r in only_journal] == ["a", "c"]

# --- channel & last -------------------------------------------------------

def test_iter_channel_and_last():
    rs = RecordStream()
    rs.add_record(mkrec(Journal, label="j1", tags={"channel:journal"}))
    rs.add_record(mkrec(Patch, label="p1", tags={"channel:ops"}))
    rs.add_record(mkrec(Journal, label="j2", tags={"channel:journal"}))
    ch = list(rs.find_all(has_channel="journal"))
    assert [r.label for r in ch] == ["j1", "j2"]
    last_journal = rs.last(has_channel="journal")
    assert last_journal.label == "j2"


def test_iter_channel_none_and_last_with_no_matches():
    rs = RecordStream()
    rs.push_records(mkrec(Journal, label="entry"))

    assert list(rs.find_all(label="missing")) == []
    assert rs.last(label="missing") is None

    with pytest.raises(NotImplementedError):
        rs.remove("anything")


def test_empty_journal():
    stream = RecordStream()

    assert len(stream) == 0
    assert list(stream.values()) == []


def test_channel_sections_iterate_independently():
    stream = RecordStream()
    graph = Graph(label="channels")
    node = graph.add_node(label="anchor")

    snapshot = Snapshot.from_item(graph)
    stream.push_records(snapshot, marker_type="snapshot", marker_name="snap-0")

    base_hash = graph._state_hash()
    patch = Patch(
        events=[
            Event(
                event_type=EventType.UPDATE,
                source_id=node.uid,
                name="label",
                value="patched",
            )
        ],
        registry_id=graph.uid,
        registry_state_hash=base_hash,
    )
    stream.push_records(patch, marker_type="patch", marker_name="patch-0")

    fragment = BaseFragment(fragment_type="text", content="hello")
    stream.push_records(fragment, marker_type="fragment", marker_name="frag-0")

    receipt = CallReceipt(behavior_id=node.uid, result="ok")
    stream.push_records(receipt, marker_type="call_receipt", marker_name="job-0")

    snap_section = list(stream.get_section("snap-0", "snapshot", is_instance=Snapshot))
    assert snap_section and all([isinstance(record, Snapshot) for record in snap_section])

    patch_section = list(stream.get_section("patch-0", "patch", is_instance=Patch))
    assert patch_section and all([isinstance(record, Patch) for record in patch_section])

    fragment_section = list(stream.get_section("frag-0", "fragment", is_instance=BaseFragment))
    assert fragment_section and all([isinstance(fragment, BaseFragment) for fragment in fragment_section])

    receipt_section = list(stream.get_section("job-0", "call_receipt", is_instance=CallReceipt))
    assert receipt_section and all([isinstance(receipt, CallReceipt) for receipt in receipt_section])

    assert stream.markers == {
        "snapshot": {"snap-0": snap_section[0].seq},
        "patch": {"patch-0": patch_section[0].seq},
        "fragment": {"frag-0": fragment_section[0].seq},
        "call_receipt": {"job-0": receipt_section[0].seq},
    }

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

