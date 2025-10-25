import pytest
from uuid import uuid4, UUID

from tangl.core import Registry, Node
from tangl.vm.replay import Event, EventType, Patch


def _mk_create(reg_id: UUID, uid: UUID, *, idx: int):
    # CREATE on registry: value must carry a uid
    return Event(event_type=EventType.CREATE, source_id=reg_id, name=None, value={"uid": uid})

def _mk_delete_node(reg_id: UUID, uid: UUID, *, idx: int):
    # Node-level DELETE on registry: name=None, value=uid
    return Event(event_type=EventType.DELETE, source_id=reg_id, name=None, value=uid)

def _mk_update(uid: UUID, name: str, val, *, idx: int):
    # Attribute update on the node: source_id is the node uid
    return Event(event_type=EventType.UPDATE, source_id=uid, name=name, value=val)

def _mk_del_attr(uid: UUID, name: str, *, idx: int):
    return Event(event_type=EventType.DELETE, source_id=uid, name=name, value=None)


def _canon_types(events):
    out = list(Event.canonicalize_events(events))
    return [e.event_type for e in out], out


# ---------- Structural endpoint patterns (same uid) ----------

@pytest.mark.parametrize("pattern, expect_types", [
    ("C",                [EventType.CREATE]),           # keep LAST C
    ("C D",              []),                           # ∅
    ("C D C",            [EventType.CREATE]),           # keep LAST C
    ("C D C D",          []),                           # ∅
    ("D",                [EventType.DELETE]),           # keep FIRST D
    ("D C",              [EventType.DELETE, EventType.CREATE]),  # keep FIRST D, LAST C
    ("D C D",            [EventType.DELETE]),           # keep FIRST D
    ("D C D C",          [EventType.DELETE, EventType.CREATE]),  # keep FIRST D, LAST C
])
def test_structural_patterns(pattern, expect_types):
    reg_id = uuid4()
    uid = uuid4()
    seq = []
    idx = 0
    for tok in pattern.split():
        if tok == "C":
            seq.append(_mk_create(reg_id, uid, idx=idx))
        elif tok == "D":
            seq.append(_mk_delete_node(reg_id, uid, idx=idx))
        else:
            raise AssertionError(f"unknown token {tok}")
        idx += 1

    types, out = _canon_types(seq)
    assert types == expect_types, f"got {[t.value for t in types]} for pattern {pattern}"


# ---------- Updates dropped if node does not exist ----------

@pytest.mark.parametrize("pattern, has_updates", [
    ("C D U", False),  # C D → ∅; updates must be dropped
    ("D U",   False),  # ends with D; no create ever kept
])
def test_updates_dropped_when_final_nonexistent(pattern, has_updates):
    reg_id = uuid4()
    uid = uuid4()
    seq = []
    idx = 0
    for tok in pattern.split():
        if tok == "C":
            seq.append(_mk_create(reg_id, uid, idx=idx))
        elif tok == "D":
            # ambiguous: final D could be node delete or attr delete; we mean node delete
            seq.append(_mk_delete_node(reg_id, uid, idx=idx))
        elif tok == "U":
            seq.append(_mk_update(uid, "x", 1, idx=idx))
        idx += 1

    _, out = _canon_types(seq)
    # Ensure no UPDATEs made it through
    assert all(e.event_type != EventType.UPDATE for e in out)
    # And no attribute DELETEs either
    assert all(not (e.event_type == EventType.DELETE and e.name) for e in out)


# ---------- Updates truncated at/before the last kept CREATE ----------

def test_updates_before_last_create_are_truncated():
    reg_id = uuid4()
    uid = uuid4()

    seq = []
    idx = 0
    # U (pre-create) -> should be dropped
    seq.append(_mk_update(uid, "x", 1, idx=idx)); idx += 1
    # C (kept)
    seq.append(_mk_create(reg_id, uid, idx=idx)); idx += 1
    # U (post-create) -> should survive (last write wins)
    seq.append(_mk_update(uid, "x", 2, idx=idx)); idx += 1

    types, out = _canon_types(seq)
    # Expect CREATE and one UPDATE
    assert types.count(EventType.CREATE) == 1
    updates = [e for e in out if e.event_type == EventType.UPDATE]
    assert len(updates) == 1 and updates[0].name == "x" and updates[0].value == 2


def test_update_coalescing_and_attr_delete_ordering():
    reg_id = uuid4()
    uid = uuid4()
    seq = []
    idx = 0
    # C
    seq.append(_mk_create(reg_id, uid, idx=idx)); idx += 1
    # U: x=1, U: x=2 -> coalesce to x=2
    seq.append(_mk_update(uid, "x", 1, idx=idx)); idx += 1
    seq.append(_mk_update(uid, "x", 2, idx=idx)); idx += 1
    # DELETE attr x overrides any prior UPDATE to x
    seq.append(_mk_del_attr(uid, "x", idx=idx)); idx += 1
    # U: y=9 remains
    seq.append(_mk_update(uid, "y", 9, idx=idx)); idx += 1

    _, out = _canon_types(seq)
    # exactly one attr DELETE for x, and one UPDATE for y
    dels = [e for e in out if e.event_type == EventType.DELETE and e.name == "x"]
    ups  = [e for e in out if e.event_type == EventType.UPDATE and e.name == "y"]
    assert len(dels) == 1 and len(ups) == 1 and ups[0].value == 9


def test_create_delete_then_recreate_with_updates():
    reg_id = uuid4(); uid = uuid4()
    seq = []
    idx = 0
    # C, D, C, U: keep LAST C and post-create U
    seq.append(_mk_create(reg_id, uid, idx=idx)); idx += 1
    seq.append(_mk_delete_node(reg_id, uid, idx=idx)); idx += 1
    seq.append(_mk_create(reg_id, uid, idx=idx)); idx += 1
    seq.append(_mk_update(uid, "x", "ok", idx=idx)); idx += 1

    types, out = _canon_types(seq)
    assert types.count(EventType.CREATE) == 1
    assert all(t != EventType.DELETE for t in types)  # C D C -> D removed
    ups = [e for e in out if e.event_type == EventType.UPDATE and e.name == "x"]
    assert len(ups) == 1 and ups[0].value == "ok"


def test_delete_create_delete_create_endpoints_kept():
    reg_id = uuid4(); uid = uuid4()
    seq = []
    idx = 0
    # D, C, D, C -> keep FIRST D and LAST C
    seq.append(_mk_delete_node(reg_id, uid, idx=idx)); idx += 1
    seq.append(_mk_create(reg_id, uid, idx=idx)); idx += 1
    seq.append(_mk_delete_node(reg_id, uid, idx=idx)); idx += 1
    seq.append(_mk_create(reg_id, uid, idx=idx)); idx += 1

    types, out = _canon_types(seq)
    assert types == [EventType.DELETE, EventType.CREATE]

def test_event_canonicalization_coalesces_updates():
    reg = Registry()
    n = Node(label="X")
    reg.add(n)

    e1 = Event(source_id=n.uid, event_type=EventType.UPDATE, name="label", value="Y", old_value="X")
    e2 = Event(source_id=n.uid, event_type=EventType.UPDATE, name="label", value="Z", old_value="Y")
    patch = Patch(events=[e1, e2])
    reg2 = patch.apply(reg)
    assert reg2.get(n.uid).get_label() == "Z"
