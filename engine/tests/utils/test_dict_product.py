import pytest
from tangl.utils.dict_product import dict_product

def test_dict_product():
    data = {
        'a': [1, 2],
        'b': [3, 4]
    }
    expected_result = [
        {'a': 1, 'b': 3},
        {'a': 1, 'b': 4},
        {'a': 2, 'b': 3},
        {'a': 2, 'b': 4}
    ]

    assert dict_product(data) == expected_result

def test_dict_product_with_ignore():
    data = {
        'a': [1, 2],
        'b': [3, 4],
        'c': [5, 6]
    }
    expected_result = [
        {'a': 1, 'b': 3, 'c': [5, 6]},
        {'a': 1, 'b': 4, 'c': [5, 6]},
        {'a': 2, 'b': 3, 'c': [5, 6]},
        {'a': 2, 'b': 4, 'c': [5, 6]},
    ]

    assert dict_product(data, ignore=['c']) == expected_result
