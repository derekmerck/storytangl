# tests/persistence/test_sqlite_storage.py
"""
Tests specific to SQLiteStorage backend.

The generic storage tests in conftest.py parametrize over all backends,
but SQLite has some specific behaviors worth testing.
"""
import tempfile
import uuid
from pathlib import Path

import pytest

from tangl.persistence.storage.sqlite_storage import SQLiteStorage


class TestSQLiteStorageBasics:
    """Basic CRUD operations."""
    
    def test_text_storage_roundtrip(self, tmp_path):
        storage = SQLiteStorage(path=tmp_path / "test.db", binary_rw=False)
        key = uuid.uuid4()
        value = '{"test": "data"}'
        
        storage[key] = value
        assert storage[key] == value
        assert key in storage
        
        del storage[key]
        assert key not in storage
    
    def test_binary_storage_roundtrip(self, tmp_path):
        storage = SQLiteStorage(path=tmp_path / "test.db", binary_rw=True)
        key = uuid.uuid4()
        value = b'\x80\x04\x95\x0c\x00\x00\x00'  # pickle header bytes
        
        storage[key] = value
        retrieved = storage[key]
        
        assert retrieved == value
        assert isinstance(retrieved, bytes)
    
    def test_missing_key_raises(self, tmp_path):
        storage = SQLiteStorage(path=tmp_path / "test.db")
        
        with pytest.raises(KeyError):
            _ = storage[uuid.uuid4()]
    
    def test_delete_missing_key_raises(self, tmp_path):
        storage = SQLiteStorage(path=tmp_path / "test.db")
        
        with pytest.raises(KeyError):
            del storage[uuid.uuid4()]
    
    def test_overwrite_existing_key(self, tmp_path):
        storage = SQLiteStorage(path=tmp_path / "test.db", binary_rw=False)
        key = uuid.uuid4()
        
        storage[key] = "first"
        storage[key] = "second"
        
        assert storage[key] == "second"
        assert len(storage) == 1


class TestSQLiteStorageEnumeration:
    """Collection operations: len, iter, clear."""
    
    def test_len_empty(self, tmp_path):
        storage = SQLiteStorage(path=tmp_path / "test.db")
        assert len(storage) == 0
        assert not storage
    
    def test_len_with_items(self, tmp_path):
        storage = SQLiteStorage(path=tmp_path / "test.db", binary_rw=False)
        
        for i in range(5):
            storage[uuid.uuid4()] = f"value_{i}"
        
        assert len(storage) == 5
        assert storage
    
    def test_iter_keys(self, tmp_path):
        storage = SQLiteStorage(path=tmp_path / "test.db", binary_rw=False)
        keys = [uuid.uuid4() for _ in range(3)]
        
        for key in keys:
            storage[key] = "value"
        
        retrieved_keys = set(storage)
        assert retrieved_keys == set(keys)
    
    def test_clear(self, tmp_path):
        storage = SQLiteStorage(path=tmp_path / "test.db", binary_rw=False)
        
        for i in range(3):
            storage[uuid.uuid4()] = f"value_{i}"
        
        assert len(storage) == 3
        storage.clear()
        assert len(storage) == 0
    
    def test_items_iteration(self, tmp_path):
        storage = SQLiteStorage(path=tmp_path / "test.db", binary_rw=False)
        expected = {uuid.uuid4(): f"value_{i}" for i in range(3)}
        
        for k, v in expected.items():
            storage[k] = v
        
        retrieved = dict(storage.items())
        assert retrieved == expected


class TestSQLiteStoragePersistence:
    """Verify data survives reconnection."""
    
    def test_data_persists_after_reconnect(self, tmp_path):
        db_path = tmp_path / "persistent.db"
        key = uuid.uuid4()
        value = "persistent_data"
        
        # Write with first connection
        storage1 = SQLiteStorage(path=db_path, binary_rw=False)
        storage1[key] = value
        del storage1
        
        # Read with new connection
        storage2 = SQLiteStorage(path=db_path, binary_rw=False)
        assert storage2[key] == value
    
    def test_creates_parent_directories(self, tmp_path):
        deep_path = tmp_path / "a" / "b" / "c" / "test.db"
        
        storage = SQLiteStorage(path=deep_path, binary_rw=False)
        storage[uuid.uuid4()] = "test"
        
        assert deep_path.exists()


class TestSQLiteStorageInMemory:
    """In-memory mode for testing."""
    
    def test_in_memory_mode(self):
        storage = SQLiteStorage(path=":memory:", binary_rw=False)
        key = uuid.uuid4()
        
        storage[key] = "ephemeral"
        assert storage[key] == "ephemeral"
        # Data is lost when storage goes out of scope


class TestSQLiteStorageEdgeCases:
    """Edge cases and binary/text mode interactions."""
    
    def test_text_mode_handles_unicode(self, tmp_path):
        storage = SQLiteStorage(path=tmp_path / "test.db", binary_rw=False)
        key = uuid.uuid4()
        value = '{"emoji": "🎲", "chinese": "故事"}'
        
        storage[key] = value
        assert storage[key] == value
    
    def test_binary_mode_returns_bytes(self, tmp_path):
        storage = SQLiteStorage(path=tmp_path / "test.db", binary_rw=True)
        key = uuid.uuid4()
        
        # Store text in binary mode - should come back as bytes
        storage[key] = b"text_as_bytes"
        result = storage[key]
        
        assert isinstance(result, bytes)
    
    def test_contains_non_uuid_returns_false(self, tmp_path):
        storage = SQLiteStorage(path=tmp_path / "test.db")
        
        assert "not-a-uuid" not in storage
        assert 12345 not in storage
        assert None not in storage
