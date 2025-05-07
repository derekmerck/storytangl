from tangl.core_next import Entity, Registry, ProvisionKey, Providable
class P(Entity, Providable): pass
def test_provide_index():
    g = Registry()
    k = ProvisionKey("actor","hero")
    g.add(P(label="h1", provides={k}))
    assert g.find_one(provides=k).label == "h1"
