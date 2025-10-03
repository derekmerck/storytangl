# tests/test_vm_collections.py
import pytest
from uuid import uuid4

from tangl.vm.replay.wrapped_collection import WatchedDict, WatchedList, WatchedSet
from tangl.vm.replay.events import Event, EventType


class FakeOwner:
    """
    Minimal stand-in for WatchedEntityProxy:
    - has a uid
    - provides _emit(...) that builds real Event objects
    """
    def __init__(self, uid=None):
        self.uid = uid or uuid4()
        self.emitted: list[Event] = []

    def _emit(self, *, event_type, name, value, old=None):
        self.emitted.append(Event(
            source_id=self.uid,
            event_type=event_type,
            name=name,
            value=value,
            old_value=old,
        ))


# --------------------
# Dict behavior
# --------------------

def test_watched_dict_set_and_del_emit_update():
    owner = FakeOwner()
    wd = WatchedDict(owner, "locals", {})
    wd["x"] = 1
    wd["y"] = 2
    del wd["x"]

    assert len(owner.emitted) == 3
    for ev in owner.emitted:
        assert ev.event_type == EventType.UPDATE
        assert ev.name == "locals"
        assert isinstance(ev.value, dict)

    # last snapshot reflects the final dict
    assert owner.emitted[-1].value == {"y": 2}


def test_watched_dict_nested_wrapping_emits_on_nested_mutation():
    owner = FakeOwner()
    wd = WatchedDict(owner, "locals", {"a": {"b": 0}})
    nested = wd["a"]                  # returns another WatchedDict for same owner/attr
    nested["b"] = 42                  # should bubble an UPDATE("locals")

    assert len(owner.emitted) == 1
    assert owner.emitted[0].name == "locals"
    assert owner.emitted[0].event_type == EventType.UPDATE
    assert owner.emitted[0].value == {"a": {"b": 42}}


def test_watched_dict_default_is_wrapped_and_emits_once():
    owner = FakeOwner()
    wd = WatchedDict(owner, "locals", {})
    inner = wd.setdefault("cfg", {})  # emits because we inserted "cfg"

    assert len(owner.emitted) == 1
    assert isinstance(inner, dict) or getattr(inner, "__class__", None).__name__.startswith("Watched")
    assert owner.emitted[0].value == {"cfg": {}}


def test_watched_dict_deepcopy_snapshot_is_immutable():
    owner = FakeOwner()
    backing = {}
    wd = WatchedDict(owner, "locals", backing)
    wd["x"] = {"y": 1}

    snap = owner.emitted[-1].value
    # mutate backing again; previous snapshot in event must not change
    wd["x"]["y"] = 2  # this goes through nested wrapping and emits again

    assert snap == {"x": {"y": 1}}
    assert owner.emitted[-1].value == {"x": {"y": 2}}


# --------------------
# List behavior
# --------------------

def test_watched_list_mutations_emit_update():
    owner = FakeOwner()
    wl = WatchedList(owner, "items", [])
    wl.append("a")
    wl.extend(["b", "c"])
    wl.insert(1, "X")
    wl.pop()
    wl[0] = "A"
    wl.reverse()
    wl.sort()

    assert len(owner.emitted) == 7
    for ev in owner.emitted:
        assert ev.event_type == EventType.UPDATE
        assert ev.name == "items"
        assert isinstance(ev.value, list)

    # final snapshot is sorted list
    assert owner.emitted[-1].value == ["A", "X", "b"]


def test_watched_list_nested_wrap_on_getitem():
    owner = FakeOwner()
    wl = WatchedList(owner, "rows", [[1], [2, 3]])
    inner = wl[1]    # nested list → returns wrapped list tied to "rows"
    inner.append(4)  # should bubble UPDATE("rows")

    assert len(owner.emitted) == 1
    assert owner.emitted[0].name == "rows"
    assert owner.emitted[0].value == [[1], [2, 3, 4]]


# --------------------
# Set behavior
# --------------------

def test_watched_set_emits_only_on_effective_change():
    owner = FakeOwner()
    ws = WatchedSet(owner, "tags", set())

    ws.add("npc")
    ws.add("npc")        # no-op; should not emit again
    ws.discard("ghost")  # no-op; no emit
    ws.update({"mage"})  # effective union; emits
    ws.update({"mage"})  # no-op; no emit
    ws.clear()           # effective; emits

    # Should be exactly three emits: add npc, update adds mage, clear
    assert len(owner.emitted) == 3
    vals = [ev.value for ev in owner.emitted]
    assert isinstance(vals[0], set) and "npc" in vals[0]
    assert isinstance(vals[1], set) and vals[1] == {"npc", "mage"}
    assert isinstance(vals[2], set) and vals[2] == set()


# --------------------
# Canonicalization with multiple UPDATEs on same (uid, attr)
# --------------------

def test_canonicalize_coalesces_updates_for_same_attr():
    owner = FakeOwner()
    wd = WatchedDict(owner, "locals", {})
    # multiple mutations in one frame
    wd["a"] = 1
    wd["a"] = 2
    wd["b"] = 3

    # The proxies emit 3 UPDATE events; canonicalizer should reduce to 1 (the last snapshot)
    canon = list(Event.canonicalize_events(owner.emitted))
    # Only updates in this test; canonicalization keeps a single UPDATE per (uid, name)
    assert len(canon) == 1
    assert canon[0].event_type == EventType.UPDATE
    assert canon[0].name == "locals"
    assert canon[0].value == {"a": 2, "b": 3}