import pytest
from tangl.utils.reduce_default import reduce_default

def test_integer_range():
    result = reduce_default([1, 10])
    assert isinstance(result, int) and 1 <= result <= 10

def test_random_choice_from_list():
    test_list = [1, 'a', None]
    assert reduce_default(test_list) in test_list
    test_list = [1, 2.5]
    assert reduce_default(test_list) in test_list

def test_weighted_choice_from_dict():
    test_dict = {'a': 1, 'b': 2}
    assert reduce_default(test_dict) in test_dict.keys()

def test_return_value_as_is():
    test_values = [12, 'string', None, [1], {}]
    for value in test_values:
        assert reduce_default(value) == value

def test_empty_list():
    assert reduce_default([]) == []

def test_all_reductions():

    sample_defaults = {
        'int':    [1, 100],                             # int range
        'assign':  "abc",                                # assign
        'pick':    ['a', 'b', 'c', 'd', 'e', 'f', 'g'],  # pick one
        'wt_pick': { 'A': 20, 'B': 20, 'C': 20 }         # weighted choice
    }
    
    assert reduce_default(sample_defaults['int']) in range(1, 101)


