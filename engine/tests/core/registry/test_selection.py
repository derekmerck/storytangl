import pytest
from uuid import uuid4

from tangl.core import Entity, Registry
from tangl.core.entity import Selectable


class Provider(Selectable, Entity):
    # providers declare criteria the selector must match
    selection_criteria: dict = {}

    def get_selection_criteria(self) -> dict:
        # allow dynamic criteria
        return dict(self.selection_criteria)


class Consumer(Entity):
    kind: str | None = None
    tier: int | None = None


def test_selectable_satisfies_and_filter_for_selector():
    # providers describe what they satisfy
    p1 = Provider(label="p1", selection_criteria={"kind": "k1"})
    p2 = Provider(label="p2", selection_criteria={"kind": "k2", "tier": 2})

    # consumer must match provider's criteria
    c = Consumer(label="c", kind="k2", tier=2)

    assert p2.satisfies(c) is True
    assert p1.satisfies(c) is False

    values = list(Provider.filter_by_criteria([p1, p2], selector=c))
    assert values == [p2]


def test_registry_select_for_and_chain_find():
    reg1: Registry[Provider] = Registry(label="reg1")
    reg2: Registry[Provider] = Registry(label="reg2")

    a = Provider(label="a", selection_criteria={"kind": "gear"})
    b = Provider(label="b", selection_criteria={"kind": "wand", "tier": 3})
    c = Provider(label="c", selection_criteria={"kind": "wand", "tier": 2})

    reg1.add(a); reg1.add(b); reg2.add(c)

    seeker = Consumer(label="wizard", kind="wand", tier=2)

    # select_for searches a single registry
    got1 = list(reg1.find_all(selector=seeker))
    assert got1 == [], 'only c satisfies seeker, c not in r1'

    got2 = list(reg2.find_all(selector=seeker))
    assert got2 == [c], 'only c satisfies seeker, c in r2'

    # chain across registries
    got = list(Registry.chain_find_all(reg1, reg2, selector=seeker))
    assert got == [c]

    # chain_find_one yields the first in the chained ordering
    one = Registry.chain_find_one(reg1, reg2, selector=seeker)
    assert one is c
