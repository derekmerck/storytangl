import pytest
from legacy.utils.deep_merge import deep_merge

def test_deep_merge():
    # Test merge with nested dict
    source = {'key1': {'subkey1': 'value1'}}
    update = {'key1': {'subkey2': 'value2'}}
    deep_merge(source, update)
    assert source == {'key1': {'subkey1': 'value1', 'subkey2': 'value2'}}

    # Test merge with list of dicts
    source = {'key1': [{'subkey1': 'value1'}, {'subkey3': 'value3'}]}
    update = {'key1': [{'subkey2': 'value2'}, {'subkey4': 'value4'}]}
    deep_merge(source, update)
    assert source == {'key1': [{'subkey1': 'value1', 'subkey2': 'value2'}, {'subkey3': 'value3', 'subkey4': 'value4'}]}

    # Test merge with list of simple values
    source = {'key1': ['value1', 'value2']}
    update = {'key1': ['value3', 'value4']}
    deep_merge(source, update)
    assert source == {'key1': ['value1', 'value2', 'value3', 'value4']}

    # Test new key addition
    source = {'key1': 'value1'}
    update = {'key2': 'value2'}
    deep_merge(source, update)
    assert source == {'key1': 'value1', 'key2': 'value2'}
