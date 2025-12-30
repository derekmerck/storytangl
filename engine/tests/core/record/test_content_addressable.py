"""Tests for :mod:`tangl.core.content_addressable`."""

from __future__ import annotations

from typing import Any

from pydantic import Field
from tangl.core import ContentAddressable
from tangl.core.record import Record
from tangl.utils.hashing import hashing_func


class SimpleContentRecord(Record, ContentAddressable):
    """Minimal test record using default hashing."""
    name: str
    value: int


class CustomContentRecord(Record, ContentAddressable):
    """Test record with custom hash computation."""
    name: str
    metadata: str

    @classmethod
    def _get_hashable_content(cls, data: dict) -> dict:
        return {"name": data.get("name")}


class NoHashRecord(Record, ContentAddressable):
    """Test record that explicitly skips hashing."""
    name: str

    @classmethod
    def _get_hashable_content(cls, data: dict) -> Any:
        return None


def test_content_hash_auto_computed_on_construction():
    record = SimpleContentRecord(name="test", value=42)

    assert record.content_hash is not None
    assert isinstance(record.content_hash, bytes)
    assert record.content_hash


def test_content_hash_deterministic():
    record1 = SimpleContentRecord(name="test", value=42)
    record2 = SimpleContentRecord(name="test", value=42)

    assert record1.content_hash == record2.content_hash
    assert record1.uid != record2.uid


def test_content_hash_different_for_different_content():
    record1 = SimpleContentRecord(name="test", value=42)
    record2 = SimpleContentRecord(name="test", value=99)

    assert record1.content_hash != record2.content_hash


def test_content_hash_excludes_uid_by_default():
    record1 = SimpleContentRecord(name="test", value=42)
    record2 = SimpleContentRecord(name="test", value=42)

    assert record1.content_hash == record2.content_hash


def test_custom_hashable_content():
    record1 = CustomContentRecord(name="alice", metadata="v1")
    record2 = CustomContentRecord(name="alice", metadata="v2")

    assert record1.content_hash == record2.content_hash

    record3 = CustomContentRecord(name="bob", metadata="v1")
    assert record3.content_hash != record1.content_hash


def test_explicit_content_hash_not_overridden():
    explicit_hash = b"explicit_test_hash"
    record = SimpleContentRecord(name="test", value=42, content_hash=explicit_hash)

    assert record.content_hash == explicit_hash


def test_no_hash_when_get_hashable_content_returns_none():
    record = NoHashRecord(name="test")

    assert record.content_hash is None

import logging

def test_get_content_identifier_with_hash():
    record = SimpleContentRecord(name="test", value=42)

    identifier = record.content_identifier()
    assert len(identifier) == 16
    assert identifier == record.content_hash.hex()[:16]


def test_get_content_identifier_without_hash():
    record = NoHashRecord(name="test")
    logging.debug(record.content_identifier())
    assert record.content_identifier() == "no-hash"


def test_content_hash_serialization_roundtrip():
    record1 = SimpleContentRecord(name="test", value=42)

    data = record1.model_dump()
    assert "content_hash" in data

    record2 = SimpleContentRecord.model_validate(data)
    assert record2.content_hash == record1.content_hash


def test_content_hash_matches_expected_for_known_input():
    record = SimpleContentRecord(name="test", value=42)

    expected_hashable = {
        "name": "test",
        "value": 42,
    }
    expected_hash = hashing_func(expected_hashable)

    assert record.content_hash == expected_hash


def test_content_hash_is_identifier_flag():
    field_info = SimpleContentRecord.model_fields["content_hash"]

    assert field_info.json_schema_extra is not None
    assert field_info.json_schema_extra.get("is_identifier") is True


def test_construction_succeeds_even_if_hashing_fails():
    class FailingHashRecord(Record, ContentAddressable):
        name: str

        @classmethod
        def _get_hashable_content(cls, data: dict) -> Any:
            raise ValueError("intentional failure")

    record = FailingHashRecord(name="test")
    assert record.content_hash is None
