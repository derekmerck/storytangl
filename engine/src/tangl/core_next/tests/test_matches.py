from tangl.core_next import Entity
def test_matches():
    e = Entity(label="hero", tags={"pc"}, locals={"hp": 10})
    assert e.matches(label="hero")
    assert not e.matches(label="villain")
    assert e.matches(tags={"pc"})
