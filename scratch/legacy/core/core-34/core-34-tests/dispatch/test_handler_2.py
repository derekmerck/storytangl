from __future__ import annotations
from typing import Self
import logging

import pytest

from tangl.core.behavior import Handler, HasHandlers, HandlerRegistry
from tangl.core.entity import Entity

logging.basicConfig(level=logging.DEBUG)

on_handle = HandlerRegistry(label="handle")

class A(HasHandlers):

    # Caller-bound instance method
    @on_handle.register()
    def f(self, *, ctx, other=None, **kwargs):
        print(f"caller meth f from caller {self!r}")

    # Class method
    @on_handle.register()
    @classmethod
    def g(cls, caller: Self, *, ctx, **kwargs):
        print(f"cls meth g from caller {caller!r}")

    # Owner-bound instance method
    @on_handle.register()
    def h(self, caller: 'A', *, ctx, other=None, **kwargs):
        print(f"inst meth h from caller {caller!r}")

# Static method
@on_handle.register()
def i(caller: A, *, ctx, **kwargs):
    print(f"static func i from caller {caller!r}")

@pytest.fixture
def caller():
    yield A(label="caller")

def test_caller_bound(caller):
    # caller-bound instance meth
    assert "f" in on_handle.all_labels(), f"meth should be in {on_handle.all_labels()}"
    handler = on_handle.find_one(label="f")
    assert handler.caller_cls is A, f"Should infer caller cls is A {handler.caller_cls} from fqn"
    assert handler.takes_other, "Should infer takes other is true from sig"
    assert not handler.takes_result, "Should infer takes result is false from sig"
    assert handler.matches_caller(caller)
    assert not handler.matches_caller(Entity())
    handler(caller, ctx=None)

def test_cls_meth(caller):
    assert "g" in on_handle.all_labels(), f"cls meth should be in {on_handle.all_labels()}"
    handler = on_handle.find_one(label="g")
    # # todo: this is wrong -- need to skip fqn unless it's a self meth
    assert handler.caller_cls is A, f"Should infer caller cls is A from str annotation {handler.caller_cls}"

    assert handler.matches_caller(caller)
    assert not handler.matches_caller(Entity())
    handler(caller, ctx=None)

def test_owner_bound(caller):
    assert "h" not in on_handle.all_labels(), f"owner meth should not be in {on_handle.all_labels()} yet"
    A(label="my_entity")  # create inst
    handler = on_handle.find_one(label="h@my_entity")
    assert "h@my_entity" in on_handle.all_labels(), f"owner meth should be in {on_handle.all_labels()}"
    assert handler.caller_cls is A, f"Should infer caller cls is A from str annotation {handler.caller_cls}"

    assert handler.matches_caller(caller)
    assert not handler.matches_caller(Entity())
    handler(caller, ctx=None)

def test_static_func(caller):
    assert "i" in on_handle.all_labels(), f"static func should be in {on_handle.all_labels()}"
    handler = on_handle.find_one(label="i")
    assert handler.caller_cls is A, f"Should infer caller cls is A {handler.caller_cls}"
    assert not handler.takes_other, "Should infer takes other is false from sig"

    assert handler.matches_caller(caller)
    assert not handler.matches_caller(Entity())
    handler(caller, ctx=None)

### DOMAIN INSTANCE HANDLERS ###

from tangl.core.entity import Singleton

class Domain(Singleton, HasHandlers):

    # Caller-bound instance method, match anyone declaring _this_ domain
    # Note Entity() will _not_ match b/c it doesn't have a "has_domain" matcher
    @on_handle.register(caller_criteria={'domain': Self})
    def j(self, caller: Entity, *, ctx, other=None, **kwargs):
        print(f"caller meth j from caller {self!r}")

class DomainScoped(Entity):
    domain: Singleton = None

@pytest.fixture
def domain():
    yield Domain(label="my_domain")
    Domain.clear_instances()

@pytest.fixture
def domain_caller(domain):
    entity = DomainScoped(domain=domain)
    yield entity


def test_domain_scoping(domain, domain_caller):

    assert domain_caller.matches(domain=domain)
    handler = on_handle.find_one(label="j@my_domain")
    assert handler is not None
    print(handler)

    assert handler.matches_caller(domain_caller)
    assert not handler.matches_caller(Entity())
    # b/c entity doesn't declare a domain, even though the class matches

    handler(domain_caller, ctx=None)
