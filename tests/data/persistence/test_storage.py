import uuid

import pytest

from tangl.data.persistence.storage import *

def compare_as_strings(val1, val2):
    if isinstance(val1, bytes):
        val1 = val1.decode('utf8')
    if isinstance(val2, bytes):
        val2 = val2.decode('utf8')
    return val1 == val2

def test_storage_put_get(storage):
    test_key = uuid.uuid4()
    test_value = "test_data"

    inserted_value = test_value

    if isinstance(storage, RedisStorage):
         inserted_value = test_value.encode('utf8')

    # Handle BSON serialization and wrap the data payload for MongoDB
    elif isinstance(storage, MongoStorage):
        import bson
        inserted_value = {"data": test_value}

    # Test 'put' (setitem)
    storage[test_key] = inserted_value

    # Test 'get' (getitem)
    retrieved_value = storage[test_key]

    if isinstance(storage, RedisStorage):
        retrieved_value = retrieved_value.decode('utf8')
    elif isinstance(storage, MongoStorage):
        # extract the data payload from the document
        retrieved_value = retrieved_value["data"]

    # Assert the retrieved value matches the stored value
    assert retrieved_value == test_value

    # Clean up (for storages that need it)
    del storage[test_key]

def test_basic_storage_storage_funcs(storage):

    if isinstance(storage, MongoStorage):
        pytest.xfail("MongoDB requires dict datatypes")

    # Assert that storage is empty
    assert not storage, f"The storage storage should be empty ({len(storage)})."

    # Store data in storage
    storage["test"] = "data"
    assert storage

    # Assert that data is in storage

    if isinstance(storage, FileStorage):
        fn = storage.get_fn("test")
        print( fn )
        fp = storage.base_path / storage.get_fn("test")
        print( fp, fp.exists() )

    assert "test" in storage, "key should be in db"
    assert compare_as_strings(storage["test"], "data"), "value should be as set"

    # Assert that getting non-existing data raises KeyError
    with pytest.raises(KeyError):
        storage["non-existing"]

    # Delete data
    del storage["test"]

    # Assert that data is not in storage anymore
    assert "test" not in storage
    assert not storage

    # Assert that deleting non-existing data raises KeyError
    with pytest.raises(KeyError):
        del storage["non-existing"]

def test_data_mutability(storage):

    if isinstance(storage, MongoStorage):
        pytest.xfail("MongoDB requires dict datatypes")

    # Store data in storage
    storage["test"] = "value"

    # Mutate data
    storage["test"] = "mutated_value"

    # Assert that data is updated in storage
    assert compare_as_strings(storage["test"], "mutated_value"), "Data should be updated in storage"
