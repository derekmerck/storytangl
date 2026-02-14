"""Contract tests for ``tangl.core38.record``."""

from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError

from tangl.core38.entity import Entity
from tangl.core38.record import OrderedRegistry, Record
from tangl.core38.registry import Registry
from tangl.core38.selector import Selector

from conftest import CustomRecord, PayloadRecord, PriorityRecord, SimpleRecord


class DataRecord(Record):
    data: dict = {"k": 1}


class EmptyRecord(Record):
    pass


class TestRecordCreation:
    def test_create_with_content(self) -> None:
        record = SimpleRecord(content="foo")
        assert record.content == "foo"

    def test_frozen(self) -> None:
        record = SimpleRecord(content="foo")
        with pytest.raises(ValidationError):
            record.content = "bar"

    def test_auto_seq_assigned(self) -> None:
        record = SimpleRecord(content="foo")
        assert isinstance(record.seq, int)

    def test_seq_monotonic(self) -> None:
        a = SimpleRecord(content="a")
        b = SimpleRecord(content="b")
        assert a.seq < b.seq

    def test_origin_id_optional(self) -> None:
        record = SimpleRecord(content="foo")
        assert record.origin_id is None

    def test_origin_id_set(self) -> None:
        origin_id = uuid4()
        record = SimpleRecord(content="foo", origin_id=origin_id)
        assert record.origin_id == origin_id

    def test_extra_fields_allowed(self) -> None:
        record = CustomRecord(foo="bar")
        assert record.foo == "bar"


class TestRecordIdentity:
    def test_eq_by_content_same(self) -> None:
        assert SimpleRecord(content="x") == SimpleRecord(content="x")

    def test_eq_by_content_different(self) -> None:
        assert SimpleRecord(content="x") != SimpleRecord(content="y")

    def test_eq_by_content_ignores_uid(self) -> None:
        a = SimpleRecord(content="x", uid=uuid4())
        b = SimpleRecord(content="x", uid=uuid4())
        assert a == b

    def test_eq_by_content_ignores_seq(self) -> None:
        a = SimpleRecord(content="x", seq=1)
        b = SimpleRecord(content="x", seq=999)
        assert a == b

    def test_content_hash_stable(self) -> None:
        assert SimpleRecord(content="x").content_hash() == SimpleRecord(content="x").content_hash()

    def test_content_hash_differs(self) -> None:
        assert SimpleRecord(content="x").content_hash() != SimpleRecord(content="y").content_hash()

    def test_ordering_by_seq(self) -> None:
        a = SimpleRecord(content="a", seq=1)
        b = SimpleRecord(content="b", seq=2)
        assert a < b

    def test_sort_key_returns_seq(self) -> None:
        record = SimpleRecord(content="x")
        assert record.sort_key() == record.seq


class TestRecordContentAccess:
    def test_hashable_content_from_content_field(self) -> None:
        assert SimpleRecord(content="foo").get_hashable_content() == "foo"

    def test_hashable_content_from_payload_field(self) -> None:
        payload = {"ok": True}
        assert PayloadRecord(payload=payload).get_hashable_content() == payload

    def test_hashable_content_fallback_to_data(self) -> None:
        assert DataRecord().get_hashable_content() == {"k": 1}

    def test_hashable_content_missing_raises(self) -> None:
        with pytest.raises(AttributeError):
            EmptyRecord().get_hashable_content()

    def test_origin_deref(self) -> None:
        reg = Registry()
        origin = Entity(label="source")
        reg.add(origin)
        record = SimpleRecord(content="foo", origin_id=origin.uid)
        assert record.origin(reg) is origin


class TestRecordSerialization:
    def test_unstructure_includes_content(self) -> None:
        data = SimpleRecord(content="foo").unstructure()
        assert data["content"] == "foo"

    def test_structure_roundtrip(self) -> None:
        record = SimpleRecord(content="foo")
        assert SimpleRecord.structure(record.unstructure()) == record

    def test_extra_fields_survive_roundtrip(self) -> None:
        record = CustomRecord(foo="bar")
        restored = CustomRecord.structure(record.unstructure())
        assert restored.foo == "bar"

    def test_frozen_after_structure(self) -> None:
        record = SimpleRecord.structure(SimpleRecord(content="foo").unstructure())
        with pytest.raises(ValidationError):
            record.content = "bar"


class TestOrderedRegistryBasics:
    def test_append_adds_record(self) -> None:
        reg = OrderedRegistry()
        rec = SimpleRecord(content="a")
        reg.append(rec)
        assert len(reg) == 1

    def test_extend_adds_multiple(self) -> None:
        reg = OrderedRegistry()
        reg.extend([SimpleRecord(content="a"), SimpleRecord(content="b")])
        assert len(reg) == 2

    def test_remove_raises(self) -> None:
        reg = OrderedRegistry()
        rec = SimpleRecord(content="a")
        reg.append(rec)
        with pytest.raises(NotImplementedError):
            reg.remove(rec.uid)

    def test_find_all_default_unsorted(self) -> None:
        reg = OrderedRegistry()
        recs = [SimpleRecord(content="a"), SimpleRecord(content="b")]
        reg.extend(recs)
        assert list(reg.find_all()) == recs

    def test_find_all_sorted_by_sort_key(self) -> None:
        reg = OrderedRegistry()
        a = SimpleRecord(content="a", seq=10)
        b = SimpleRecord(content="b", seq=1)
        reg.extend([a, b])
        assert list(reg.find_all(sort_key=lambda m: m.sort_key())) == [b, a]

    def test_find_all_with_selector(self) -> None:
        reg = OrderedRegistry()
        a = SimpleRecord(content="a", tags={"x"})
        b = SimpleRecord(content="b")
        reg.extend([a, b])
        assert list(reg.find_all(Selector(has_tags={"x"}))) == [a]

    def test_append_out_of_order_sorts_correctly(self) -> None:
        reg = OrderedRegistry()
        a = SimpleRecord(content="a", seq=3)
        b = SimpleRecord(content="b", seq=1)
        c = SimpleRecord(content="c", seq=2)
        reg.extend([a, b, c])
        assert [r.seq for r in reg.find_all(sort_key=lambda m: m.sort_key())] == [1, 2, 3]

    def test_inherits_registry_api(self) -> None:
        reg = OrderedRegistry()
        rec = SimpleRecord(content="a")
        reg.append(rec)
        assert bool(reg)
        assert rec in reg
        assert reg.get(rec.uid) is rec


class TestOrderedRegistryKeyAccessors:
    def test_max_key_empty_returns_none(self) -> None:
        assert OrderedRegistry().max_key() is None

    def test_min_key_empty_returns_none(self) -> None:
        assert OrderedRegistry().min_key() is None

    def test_max_key_returns_highest_sort_key(self) -> None:
        reg = OrderedRegistry()
        reg.extend([SimpleRecord(content="a", seq=1), SimpleRecord(content="b", seq=9)])
        assert reg.max_key() == 9

    def test_min_key_returns_lowest_sort_key(self) -> None:
        reg = OrderedRegistry()
        reg.extend([SimpleRecord(content="a", seq=1), SimpleRecord(content="b", seq=9)])
        assert reg.min_key() == 1

    def test_max_key_custom_sort_key(self) -> None:
        reg = OrderedRegistry()
        reg.extend([SimpleRecord(label="a", content="x"), SimpleRecord(label="z", content="y")])
        assert reg.max_key(sort_key=lambda r: r.label) == "z"

    def test_min_key_custom_sort_key(self) -> None:
        reg = OrderedRegistry()
        reg.extend([SimpleRecord(label="a", content="x"), SimpleRecord(label="z", content="y")])
        assert reg.min_key(sort_key=lambda r: r.label) == "a"

    def test_key_accessors_single_member(self) -> None:
        reg = OrderedRegistry()
        rec = SimpleRecord(content="x")
        reg.append(rec)
        assert reg.min_key() == reg.max_key() == rec.sort_key()

    def test_key_accessors_track_appends(self) -> None:
        reg = OrderedRegistry()
        reg.append(SimpleRecord(content="a", seq=5))
        assert reg.max_key() == 5
        reg.append(SimpleRecord(content="b", seq=6))
        assert reg.max_key() == 6


class TestOrderedRegistryGetSlice:
    def _build(self) -> tuple[OrderedRegistry, list[SimpleRecord]]:
        reg = OrderedRegistry()
        records = [
            SimpleRecord(content="a", seq=1, tags={"x"}),
            SimpleRecord(content="b", seq=2),
            SimpleRecord(content="c", seq=3, tags={"x"}),
            SimpleRecord(content="d", seq=4),
        ]
        reg.extend(records)
        return reg, records

    def test_slice_returns_records_in_range(self) -> None:
        reg, recs = self._build()
        assert list(reg.get_slice(start_key=2, stop_key=4)) == recs[1:3]

    def test_slice_half_open_includes_start(self) -> None:
        reg, recs = self._build()
        assert recs[1] in list(reg.get_slice(start_key=2, stop_key=3))

    def test_slice_half_open_excludes_stop(self) -> None:
        reg, recs = self._build()
        assert recs[2] not in list(reg.get_slice(start_key=1, stop_key=3))

    def test_slice_none_start_unbounded(self) -> None:
        reg, recs = self._build()
        assert list(reg.get_slice(stop_key=3)) == recs[:2]

    def test_slice_none_stop_unbounded(self) -> None:
        reg, recs = self._build()
        assert list(reg.get_slice(start_key=3)) == recs[2:]

    def test_slice_both_none_returns_all(self) -> None:
        reg, recs = self._build()
        assert list(reg.get_slice()) == recs

    def test_slice_empty_range(self) -> None:
        reg, _ = self._build()
        assert list(reg.get_slice(start_key=10, stop_key=20)) == []

    def test_slice_results_sorted(self) -> None:
        reg = OrderedRegistry()
        reg.extend([SimpleRecord(content="c", seq=3), SimpleRecord(content="a", seq=1)])
        assert [r.seq for r in reg.get_slice()] == [1, 3]

    def test_slice_with_selector(self) -> None:
        reg, recs = self._build()
        assert list(reg.get_slice(start_key=1, stop_key=4, selector=Selector(has_tags={"x"}))) == [recs[0], recs[2]]

    def test_slice_custom_sort_key(self) -> None:
        reg = OrderedRegistry()
        a = SimpleRecord(label="a", content="x")
        z = SimpleRecord(label="z", content="y")
        reg.extend([z, a])
        result = list(reg.get_slice(start_key="a", stop_key="m", sort_key=lambda r: r.label))
        assert result == [a]

    def test_slice_with_composite_sort_key(self) -> None:
        reg = OrderedRegistry()
        low = PriorityRecord(content="low", priority=1, seq=2)
        high = PriorityRecord(content="high", priority=2, seq=1)
        reg.extend([high, low])
        assert list(reg.get_slice(start_key=(1, 0), stop_key=(2, 0))) == [low]

    def test_slice_does_not_mutate_registry(self) -> None:
        reg, _ = self._build()
        before = len(reg)
        _ = list(reg.get_slice(start_key=2, stop_key=3))
        assert len(reg) == before
