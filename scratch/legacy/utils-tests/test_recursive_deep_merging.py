from legacy.utils.recursive_deep_merging import RecursiveChainMap, get_nested_value, DereferencingDict

def test_get_nested_val():
    data = {
        'x': {
            'y': {
                'z': 'value'
            }
        }
    }

    # Accessing nested key
    value = get_nested_value(data, 'x.y.z')
    print(value)  # Outputs: value
    assert value == "value"

    # Attempting to access a non-existent key
    not_found = get_nested_value(data, 'x.y.z.w')
    print(not_found)  # Outputs: None
    assert not_found is None

def test_recursive_chainmap():
    config1 = {'key1': {'key2': {'key3': 'value1', 'anotherKey': 'overWrittenValue'}}}
    config2 = {'key1': {'key2': {'key3': 'value2', 'anotherKey': 'anotherValue'}}}
    config3 = {'key1': {'key2': {'key3': 'value3'}}}
    rcm = RecursiveChainMap(config3, config2, config1)
    result = rcm.get_by_path('key1.key2.key3')
    assert result == "value3", "key2.key3 from config3"
    result = rcm.get_by_path('key1.key2.anotherKey')
    assert result == "anotherValue", "key2.anotherKey from config2"

def test_basic_dereferencing():
    ddict = DereferencingDict()
    ddict['a'] = 'value'
    ddict['b'] = '$a'
    assert ddict['b'] == 'value'

def test_missing_reference():
    ddict = DereferencingDict()
    ddict['a'] = '$b'
    assert ddict['a'] == '$b', "Should retain original value if reference is unresolved"

def test_non_string_key_handling():
    ddict = DereferencingDict()
    ddict['a'] = 10
    ddict['b'] = 20
    ddict['c'] = '$b'
    assert ddict['c'] == 20, "Should handle non-string dereferences correctly"
