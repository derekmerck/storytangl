# No longer supported

def test_runtime_consumes_str():

    c = RuntimeNode(
        conditions=["1 + 2 == 3", "True"]
    )
    assert c.avail()
    print( c.conditions )

    c = RuntimeNode(
        conditions=["1 + 2 == 4", "True"]
    )
    assert not c.avail()

    a = RuntimeNode(
        effects=["print('hello')", "import math"]
    )
    assert isinstance( a.effects[0], Effect )
    assert isinstance( a.effects[1], Effect )
    print( a.effects )
