from __future__ import annotations

import pytest

from tangl.core import Entity
from tangl.mechanics.assembly import HasSlottedContainer, Slot, SlotGroup, SlottedContainer


class TestComponent(Entity):
    power_cost: float = 0.0

    def get_cost(self, resource: str) -> float:
        return self.power_cost if resource == "power" else 0.0


class TestContainer(SlottedContainer[TestComponent]):
    slots = {
        "alpha": Slot.for_type("alpha", TestComponent, tags={"alpha"}, required=True),
        "beta": Slot.for_tags("beta", tags={"beta"}, max_count=2),
    }
    slot_groups = [SlotGroup(name="group", slot_names=["alpha", "beta"], min_total=1, max_total=3)]
    tracked_resources = ["power"]

    def _validate_custom(self) -> list[str]:
        errors = super()._validate_custom()
        if any(component.label == "forbidden" for component in self.all_components()):
            errors.append("Forbidden component present")
        return errors


class TestHost(HasSlottedContainer, Entity):
    _container_class = TestContainer
    max_power: float = 2.0


@pytest.fixture
def component_alpha() -> TestComponent:
    return TestComponent(label="alpha", tags={"alpha"}, power_cost=1.0)


@pytest.fixture
def component_beta() -> TestComponent:
    return TestComponent(label="beta", tags={"beta"}, power_cost=0.5)


def test_slot_matching(component_alpha: TestComponent, component_beta: TestComponent) -> None:
    alpha_slot = Slot.for_type("alpha", TestComponent, tags={"alpha"})
    beta_slot = Slot.for_tags("beta", tags={"beta"})

    assert alpha_slot.selects_for(component_alpha)[0]
    assert not alpha_slot.selects_for(component_beta)[0]
    assert beta_slot.selects_for(component_beta)[0]


def test_assignment_and_validation(component_alpha: TestComponent, component_beta: TestComponent) -> None:
    container = TestContainer(owner=TestHost(label="owner"))

    container.assign("alpha", component_alpha)
    container.assign("beta", component_beta)

    assert container.is_valid
    assert container.validate() == []


def test_required_slot_and_group_limits(component_beta: TestComponent) -> None:
    container = TestContainer(owner=TestHost(label="owner"))

    errors = container.validate()
    assert "Required slot empty: alpha" in errors

    container.assign("alpha", TestComponent(label="filled", tags={"alpha"}))
    container.assign("beta", component_beta)
    container.assign("beta", TestComponent(label="beta2", tags={"beta"}))

    with pytest.raises(ValueError):
        container.assign("beta", TestComponent(label="beta3", tags={"beta"}))


def test_budget_check(component_alpha: TestComponent) -> None:
    host = TestHost(label="owner", max_power=1.5)
    container = TestContainer(owner=host)

    container.assign("alpha", component_alpha)
    with pytest.raises(ValueError):
        container.assign("beta", TestComponent(label="power_hungry", tags={"beta"}, power_cost=2.0))


def test_custom_validation(component_alpha: TestComponent) -> None:
    container = TestContainer(owner=TestHost(label="owner"))
    forbidden = TestComponent(label="forbidden", tags={"alpha"})
    container.assign("alpha", forbidden)
    errors = container.validate()
    assert "Forbidden component present" in errors


def test_container_serialization(component_alpha: TestComponent) -> None:
    host = TestHost(label="owner")
    host.loadout.assign("alpha", component_alpha)

    dumped = host.model_dump()
    restored = TestHost.model_validate(dumped)

    assert restored.loadout.owner is restored
    assert restored.loadout.get_slot("alpha")[0].label == "alpha"
