import pytest

from tangl.core.singleton import Singleton, LabelSingleton, DataSingleton, MutableSingleton

def test_singleton_hashes():
    # These are in subclasses to avoid polluting and resetting the base class instance tables

    Singleton_ = type('Singleton_', (Singleton,), {})
    g = Singleton_(digest=b'abcdefghijklmnop')
    print(g.uid)
    {g}

    LabelSingleton_ = type('LabelSingleton_', (LabelSingleton,), {})
    g = LabelSingleton_(label="my object")
    print(g.uid, g.label)
    {g}
    assert LabelSingleton_.get_instance("my object") is g
    assert LabelSingleton_(label="my object") is g

    DataSingleton_ = type('DataSingleton_', (DataSingleton,), {})
    g = DataSingleton_(data=b'1234567890123456')
    print(g.digest)
    {g}

    MutableSingleton_ = type('MutableSingleton_', (MutableSingleton,), {})
    h = MutableSingleton_(secret="abcdefg")
    print(h.secret)

    with pytest.raises(TypeError):
        {h}

    h.secret = "12345"
    print(h.secret)

    with pytest.raises(TypeError):
        {h}
