from dataclasses import dataclass
from tangl33.core import Entity, Registry

@dataclass
class P(Entity):
    data: str = None

def test_find_by_feature():
    g = Registry()
    g.add(P(label="h1", data="123"))
    assert g.find_one(data="123").label == "h1"

def test_find_all_by_feature():
    g = Registry()
    g.add(P(label="h1", data="123"))
    g.add(P(label="h2", data="123"))
    assert 'h1' in [ x.label for x in g.find_all(data="123") ]
    assert 'h2' in [ x.label for x in g.find_all(data="123") ]
