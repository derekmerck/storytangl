from enum import Enum

import pytest

from legacy.utils.set_dict import SetDict, EnumdSetDict

def test_init():
    pd = SetDict()
    assert isinstance(pd, SetDict)
    assert pd.default_factory == set, "Default factory should be set"

    sd = SetDict(key1=['abc', 'def'])
    assert sd['key1'] == {'abc', 'def'}, "Should cast initial args to a set"


def test_setitem():
    pd = SetDict()
    pd['fruit'] = 'apple'
    assert 'apple' in pd['fruit']
    pd['numbers'] = ['one', 'two']
    assert 'one' in pd['numbers'] and 'two' in pd['numbers']

def test_pick():
    pd = SetDict()
    pd['colors'] = {'red', 'blue'}
    assert pd.choice('colors') in {'red', 'blue'}
    pd['colors'] = 'green'  # Single item set
    assert pd.choice('colors') == 'green'
    assert pd.choice('empty') is None, "Non-existent key"

def test_init_with_dict():
    initial_dict = {'letters': {'a', 'b', 'c'}}
    pd = SetDict(initial_dict)
    assert pd['letters'] == {'a', 'b', 'c'}

def test_set_dict_pickles():
    from pickle import loads, dumps
    sd = SetDict()
    pkl = dumps(sd)
    res = loads(pkl)
    assert res == sd

    sd['key1'] = 'value1'
    sd['key2'] = ['value2a', 'value2b']
    print(f"Original: {sd}")
    assert sd['key2'] == {'value2a', 'value2b'}
    print( sd.__dict__ )

    # Pickle
    pickled_sd = dumps(sd)

    # Unpickle
    unpickled_sd = loads(pickled_sd)
    print(f"Unpickled: {unpickled_sd}")

    assert sd == unpickled_sd


class TestEnum(Enum):
    KEY1 = 'key1'
    KEY2 = 'key2'

def test_enumkey_init():
    ekpd = EnumdSetDict()
    assert isinstance(ekpd, EnumdSetDict)
    assert ekpd.default_factory == set

def test_enumkey_setitem():
    ekpd = EnumdSetDict()
    ekpd[TestEnum.KEY1] = 'value1'
    assert 'value1' in ekpd[TestEnum.KEY1]
    ekpd['KEY2'] = {'value2', 'value3'}
    assert 'value2' in ekpd[TestEnum.KEY2] and 'value3' in ekpd[TestEnum.KEY2]

def test_enumkey_pick():
    ekpd = EnumdSetDict()
    ekpd['KEY1'] = {'item1', 'item2'}
    assert ekpd.choice('KEY1') in {'item1', 'item2'}
    assert ekpd.choice(TestEnum.KEY1) in {'item1', 'item2'}

def test_bad_key():
    ekpd = EnumdSetDict()
    assert ekpd['nonexistent'] == set()

def test_ekpd_pickles():
    from pickle import loads, dumps
    ekpd = EnumdSetDict()
    pkl = dumps(ekpd)
    res = loads(pkl)
    assert res == ekpd

    ekpd['key1'] = 'value1'
    ekpd['key2'] = ['value2a', 'value2b']
    print(f"Original: {ekpd}")

    # Pickle
    pickled_sd = dumps(ekpd)

    # Unpickle
    unpickled_sd = loads(pickled_sd)
    print(f"Unpickled: {unpickled_sd}")

    assert unpickled_sd == ekpd
