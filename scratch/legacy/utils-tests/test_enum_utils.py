import pytest
from typing import ClassVar
from enum import Enum
from legacy.utils.enum_utils import EnumUtils

class TestEnum(EnumUtils, Enum):

    FOO = 'foobar'
    BAR = 'barfoo'
    BAZ = 123

    @classmethod
    def aliases(cls):
        return {'aliasfoo': cls.FOO}

    @classmethod
    def rev_aliases(cls):
        return {cls.FOO: ["revaliasfoo"]}

def test_enum_alias():
    assert TestEnum('aliasfoo') == TestEnum.FOO

def test_enum_rev_alias():
    print( list( TestEnum ) )
    assert TestEnum('revaliasfoo') == TestEnum.FOO

def test_enum_case_insensitive():
    assert TestEnum('_FOOBAR') == TestEnum.FOO

def test_enum_pick():
    assert isinstance(TestEnum.pick(), TestEnum)

def test_enum_lower():
    assert TestEnum('FOO').lower() == 'foo'

def test_enum_typed_keys():
    input_dict = {'FOO': 1, 'BAR': 2}
    expected_dict = {TestEnum.FOO: 1, TestEnum.BAR: 2}
    assert TestEnum.typed_keys(input_dict) == expected_dict

def test_enum_int_map():
    TestEnum._int_map = {'foobar': 1, 'barfoo': 2, 123: 3}
    assert int(TestEnum.FOO) == 1
    assert int(TestEnum.BAR) == 2
    assert int(TestEnum.BAZ) == 3

def test_enum_order_comparison():
    TestEnum._int_map = {'foobar': 1, 'barfoo': 2, 123: 3}
    assert TestEnum.BAR > TestEnum.FOO
    assert not TestEnum.FOO > TestEnum.BAZ

def test_enum_missing():
    with pytest.raises(ValueError):
        TestEnum('nonexistent')
