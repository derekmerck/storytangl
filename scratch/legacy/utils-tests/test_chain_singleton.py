
from legacy.utils.chain_singleton import SingletonMap, SingletonEntity, ChainSingletonMap

def test_chain_singleton():

    A = ChainSingletonMap( label="A", data={"foo": "bar"} )
    B = ChainSingletonMap( label="B", extends=['A'], data={"hello": "world"} )
    C = ChainSingletonMap( label="C", extends=['B'] )

    assert B['foo'] == 'bar'
    assert B.foo == 'bar'
    assert B.hello == "world"

    import pytest
    with pytest.raises(AttributeError):
        print( B.bar )

    with pytest.raises(KeyError):
        print( B['bar'] )

    assert C.foo == 'bar'
    assert C['foo'] == 'bar'
    assert C.hello == "world"
