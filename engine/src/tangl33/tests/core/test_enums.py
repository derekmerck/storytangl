from tangl33.core.enums import Phase, Tier, Service

def test_enums_correct_length():

    assert len(list(Service)) == 7
    assert len(list(Tier)) == 8
    assert len(list(Phase)) == 4
