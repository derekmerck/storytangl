import pytest
from enum import Enum
from tangl.utils.enum_plus import EnumPlusMixin

class TestEnum(EnumPlusMixin, Enum):

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

def test_enum_tag_format():
    assert TestEnum('testenum:foo') == TestEnum.FOO
    assert TestEnum('TestEnum:foo') == TestEnum.FOO
    assert TestEnum('testenum/foo') == TestEnum.FOO
    assert TestEnum('testenum+foo') == TestEnum.FOO

def test_enum_rev_alias():
    print( list( TestEnum ) )
    assert TestEnum('revaliasfoo') == TestEnum.FOO

def test_enum_pick():
    assert isinstance(TestEnum.pick(), TestEnum)

def test_enum_lower():
    assert TestEnum('FOO').lower() == 'foo'

def test_enum_typed_keys():
    input_dict = {'FOO': 1, 'BAR': 2}
    expected_dict = {TestEnum.FOO: 1, TestEnum.BAR: 2}
    assert TestEnum.typed_keys(input_dict) == expected_dict

def test_enum_missing():
    with pytest.raises(ValueError):
        TestEnum('nonexistent')
