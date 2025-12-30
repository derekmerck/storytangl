import uuid
from tangl.core import Entity


def test_entity_alias() -> None:

    u = uuid.uuid4()
    e = Entity(uid=u, label="test_entity")

    print( e.get_identifiers() )

    assert e.has_alias('test_entity')
    assert e.has_alias(u)
    assert e.has_alias(e.short_uid())
    assert not e.has_alias(uuid.uuid4())