import pytest
from uuid import uuid4, UUID
from pydantic import Field
from tangl.utils.base_model_plus import BaseModelPlus
from tangl.type_hints import Tag

from tangl.core.entity import Entity
from tangl.core.entity import is_identifier

# class Entity(BaseModelPlus):
#     uid: str = Field(default_factory=lambda: str(uuid4()), json_schema_extra={'is_identifier': True})
#     label_: str = Field(None, alias="label")
#     tags: set[Tag] = Field(default_factory=set)
#
#     @identifier_property
#     def label(self):
#         return self.label_ or "unlabeled"
#
#     def iter_aliases(self):
#         def _iter_annotated_field_values():
#             for field in self.model_fields.values():
#                 if field.json_schema_extra.get("is_identifier", False):
#                     yield getattr(self, field.name)
#
#         def _iter_annotated_class_values():
#             for v in vars(self.__class__).values():
#                 if getattr(v, "_is_identifier", False):
#                     if isinstance(v, property):
#                         yield v.fget(self)
#                     elif callable(v):
#                         yield v(self)
#                     else:
#                         yield v
#
#         yield from _iter_annotated_field_values()
#         yield from _iter_annotated_class_values()
#
#     def has_identifier(self, *alias):
#         identifiers = set(self.iter_aliases())
#         return any(a in identifiers for a in alias)

# Subclass with new field and property aliases
class Character(Entity):
    name: str = Field(..., json_schema_extra={'is_identifier': True})

    @is_identifier
    def nickname(self):
        return f"nick_{self.name.lower()}"

def test_entity_field_and_property_alias():
    uid = UUID(bytes=b"abcd"*4)
    e = Entity(uid=uid, label="hello")
    aliases = set(e.get_identifiers())
    # Should include uid and label property value
    assert uid in aliases
    assert "hello" in aliases
    # Negative test
    assert not e.has_identifier("doesnotexist")
    # Positive test
    assert e.has_identifier(uid)
    assert e.has_identifier("hello")

def test_character_inherits_and_extends_aliases():
    uid = UUID(bytes=b"efgh"*4)
    c = Character(uid=uid, label="main", name="Alice")
    aliases = set(c.get_identifiers())
    # Should include base (uid, label), plus field (name) and property (nickname)
    assert uid in aliases
    assert "main" in aliases
    assert "Alice" in aliases
    assert "nick_alice" in aliases
    # Positive tests
    assert c.has_identifier(uid)
    assert c.has_identifier("Alice")
    assert c.has_identifier("nick_alice")
    # Negative
    assert not c.has_identifier("not_found")

def test_subclass_override_and_negative_cases():
    class Agent(Character):
        callsign: str = Field("BRAVO", json_schema_extra={'is_identifier': True})

        @is_identifier
        def agent_tag(self):
            return f"AGENT-{self.callsign}"

    uid = UUID(bytes=b"ijkl"*4)
    a = Agent(uid=uid, label="undercover", name="Bob", callsign="ECHO")
    aliases = set(a.get_identifiers())
    assert uid in aliases
    assert "undercover" in aliases
    assert "Bob" in aliases
    assert "nick_bob" in aliases
    assert "ECHO" in aliases
    assert "AGENT-ECHO" in aliases
    # All identifiers should match
    assert a.has_identifier("ECHO")
    assert a.has_identifier("AGENT-ECHO")
    # Negative
    assert not a.has_identifier("not-an-alias")