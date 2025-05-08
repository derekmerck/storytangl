from tangl33.core import Entity

def test_matches():
    e = Entity(label="hero", tags={"pc"})
    assert e.matches(label="hero")
    assert not e.matches(label="villain")
    assert e.matches(tags={"pc"})

def test_tags_match():
    e = Entity(label="hero", tags={"pc", "tough"})
    assert e.matches(label="hero")
    assert not e.matches(label="villain")
    assert e.matches(tags={"pc", "tough"})
