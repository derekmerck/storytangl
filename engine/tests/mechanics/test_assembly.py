from __future__ import annotations

import pytest
from pydantic import Field

from tangl.core import Entity
from tangl.mechanics.assembly import HasSlottedContainer, Slot, SlotGroup, SlottedContainer


class TestComponent(Entity):
    power_cost: float = 0.0
    weight_cost: float = 0.0
    defense_bonus: float = 0.0
    capabilities: set[str] = Field(default_factory=set)
    status_text: str | None = None

    def get_cost(self, resource: str) -> float:
        if resource == "power":
            return self.power_cost
        if resource == "weight":
            return self.weight_cost
        return 0.0


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


def test_get_aggregate_sums_numeric_attributes() -> None:
    container = TestContainer(owner=TestHost(label="owner"))
    container.assign("alpha", TestComponent(label="shield", tags={"alpha"}, defense_bonus=2.5))
    container.assign("beta", TestComponent(label="cloak", tags={"beta"}, defense_bonus=1.5))

    assert container.get_aggregate("defense_bonus") == 4.0


def test_get_aggregate_cost_sums_named_resource_costs() -> None:
    container = TestContainer(owner=TestHost(label="owner"))
    container.assign("alpha", TestComponent(label="armor", tags={"alpha"}, weight_cost=3.0))
    container.assign("beta", TestComponent(label="pack", tags={"beta"}, weight_cost=1.5))

    assert container.get_aggregate_cost("weight") == 4.5


def test_get_aggregate_tags_unions_string_collections() -> None:
    container = TestContainer(owner=TestHost(label="owner"))
    container.assign(
        "alpha",
        TestComponent(
            label="visor",
            tags={"alpha"},
            capabilities={"vision", "targeting"},
        ),
    )
    container.assign(
        "beta",
        TestComponent(
            label="scanner",
            tags={"beta"},
            capabilities={"targeting", "mapping"},
        ),
    )

    assert container.get_aggregate_tags("capabilities") == {"mapping", "targeting", "vision"}


def test_get_aggregate_defaults_for_empty_container() -> None:
    container = TestContainer(owner=TestHost(label="owner"))

    assert container.get_aggregate("defense_bonus", default=1.0) == 1.0
    assert container.get_aggregate_cost("weight", default=2.0) == 2.0
    assert container.get_aggregate_tags("capabilities") == set()


def test_get_aggregate_raises_for_non_numeric_present_values() -> None:
    container = TestContainer(owner=TestHost(label="owner"))
    container.assign("alpha", TestComponent(label="badge", tags={"alpha"}, status_text="boosted"))

    with pytest.raises(TypeError, match="expected numeric values"):
        container.get_aggregate("status_text")
