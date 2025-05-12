from tangl33.core.enums import CoreScope, CoreService

def test_enums_correct_length():

    assert len(list(CoreService)) == 7
    assert len(list(CoreScope)) == 8
