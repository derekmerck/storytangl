from __future__ import annotations

from enum import Enum
from typing import ClassVar

import pytest
from pydantic import Field

from tangl.core import Entity
from tangl.mechanics.assembly import (
    Component,
    ComponentFacet,
    HasSlottedContainer,
    Slot,
    SlotGroup,
    SlottedContainer,
)


class LoadoutTag(Enum):
    SCOUT = "scout"
    ARCANE = "arcane"


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
    slots: ClassVar[dict[str, Slot]] = {
        "alpha": Slot.for_type("alpha", TestComponent, tags={"alpha"}, required=True),
        "beta": Slot.for_tags("beta", tags={"beta"}, max_count=2),
    }
    slot_groups: ClassVar[list[SlotGroup]] = [
        SlotGroup(name="group", slot_names=["alpha", "beta"], min_total=1, max_total=3)
    ]
    tracked_resources: ClassVar[list[str]] = ["power"]

    def _validate_custom(self) -> list[str]:
        errors = super()._validate_custom()
        if any(component.label == "forbidden" for component in self.all_components()):
            errors.append("Forbidden component present")
        return errors


class TestHost(HasSlottedContainer, Entity):
    _container_class = TestContainer
    max_power: float = 2.0


class PrerequisiteContainer(SlottedContainer[TestComponent]):
    slots: ClassVar[dict[str, Slot]] = {
        "chassis": Slot.for_tags("chassis", tags={"chassis"}),
        "powerplant": Slot.for_tags(
            "powerplant",
            tags={"powerplant"},
            prerequisite_slots=["chassis"],
        ),
        "turret": Slot.for_tags(
            "turret",
            tags={"turret"},
            prerequisite_slots=["powerplant"],
        ),
    }


class ConditionalHost(Entity):
    frame_size: str = "small"


class ConditionalContainer(SlottedContainer[TestComponent]):
    slots: ClassVar[dict[str, Slot]] = {
        "turret": Slot.for_tags(
            "turret",
            tags={"turret"},
            required=True,
            enablement_criteria={"frame_size": "large"},
        )
    }


class DefaultLoadoutContainer(SlottedContainer[TestComponent]):
    slots: ClassVar[dict[str, Slot]] = {
        "chassis": Slot.for_tags(
            "chassis",
            tags={"chassis"},
            default_factory=lambda: TestComponent(label="starter-frame", tags={"chassis"}),
        ),
        "powerplant": Slot.for_tags(
            "powerplant",
            tags={"powerplant"},
            prerequisite_slots=["chassis"],
            default_factory=lambda: TestComponent(label="starter-motor", tags={"powerplant"}),
        ),
        "turret": Slot.for_tags(
            "turret",
            tags={"turret"},
            enablement_criteria={"frame_size": "large"},
            default_factory=lambda: TestComponent(label="starter-turret", tags={"turret"}),
        ),
    }


class ShapeComponent(Component):
    weight_cost: float = 0.0

    def get_cost(self, resource: str) -> float:
        if resource == "weight":
            return self.weight_cost
        return 0.0


class ShapeBoard(SlottedContainer[ShapeComponent]):
    slots: ClassVar[dict[str, Slot]] = {
        "star": Slot(
            name="star",
            connector_shape="star",
            connector_polarity="socket",
        ),
        "circle": Slot(
            name="circle",
            connector_shape="circle",
            connector_polarity="socket",
        ),
        "square": Slot(
            name="square",
            connector_shape="square",
            connector_polarity="socket",
        ),
    }
    empty_slot_text: ClassVar[dict[str, str]] = {
        "star": "an empty star-shaped slot",
        "circle": "an empty circular slot",
        "square": "an empty square slot",
    }

    def describe(self) -> str:
        filled_slots = {
            facet.subject_id: str(facet.payload)
            for facet in self.component_facets(channel="prose", facet_type="giver")
        }
        parts = [
            filled_slots.get(slot_name, empty_text)
            for slot_name, empty_text in self.empty_slot_text.items()
        ]
        return f"A board with {parts[0]}, {parts[1]}, and {parts[2]}."

    def challenge_value(self, initial: float = 0.0) -> float:
        result = initial
        for facet in self.component_facets(channel="challenge", facet_type="changer"):
            payload = facet.payload
            if not isinstance(payload, dict):
                raise TypeError("Shape-board challenge facets require dict payloads")

            op = payload["op"]
            value = payload["value"]
            if op == "add":
                result += value
            elif op == "multiply":
                result *= value
            elif op == "subtract":
                result -= value
            else:
                raise ValueError(f"Unsupported shape-board challenge op: {op}")
        return result

    def hits_target(self, target: float, *, initial: float = 0.0) -> bool:
        return self.challenge_value(initial=initial) == target


class WeightedShapeBoard(ShapeBoard):
    tracked_resources: ClassVar[list[str]] = ["weight"]


EMPTY_BOARD_DESCRIPTION = (
    "A board with an empty star-shaped slot, an empty circular slot, "
    "and an empty square slot."
)
FILLED_STAR_BOARD_DESCRIPTION = (
    "A board with a filled star-shaped slot, an empty circular slot, "
    "and an empty square slot."
)


@pytest.fixture
def component_alpha() -> TestComponent:
    return TestComponent(label="alpha", tags={"alpha"}, power_cost=1.0)


@pytest.fixture
def component_beta() -> TestComponent:
    return TestComponent(label="beta", tags={"beta"}, power_cost=0.5)


def shape_plug(
    shape: str,
    *,
    polarity: str = "plug",
    challenge_op: str | None = None,
    challenge_value: float | None = None,
    weight_cost: float = 0.0,
) -> ShapeComponent:
    facets = [
        ComponentFacet(
            channel="prose",
            facet_type="giver",
            payload=f"a filled {shape}-shaped slot",
        )
    ]
    if challenge_op is not None and challenge_value is not None:
        facets.append(
            ComponentFacet(
                channel="challenge",
                facet_type="changer",
                payload={"op": challenge_op, "value": challenge_value},
            )
        )

    return ShapeComponent(
        label=f"{shape}-{polarity}",
        connector_shape=shape,
        connector_polarity=polarity,
        facets=facets,
        weight_cost=weight_cost,
    )


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


def test_get_aggregate_tags_accepts_mixed_tag_values() -> None:
    container = TestContainer(owner=TestHost(label="owner"))
    container.assign(
        "alpha",
        TestComponent(
            label="visor",
            tags={"alpha", 7, LoadoutTag.SCOUT},
        ),
    )
    container.assign(
        "beta",
        TestComponent(
            label="scanner",
            tags={"beta", 11, LoadoutTag.ARCANE},
        ),
    )

    assert container.get_aggregate_tags() == {
        "alpha",
        "beta",
        7,
        11,
        LoadoutTag.SCOUT,
        LoadoutTag.ARCANE,
    }


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


def test_slot_prerequisite_rejects_missing_direct_dependency() -> None:
    container = PrerequisiteContainer()

    with pytest.raises(ValueError, match="Missing prerequisite slots: chassis"):
        container.assign(
            "powerplant",
            TestComponent(label="motor", tags={"powerplant"}),
        )

    container.assign("chassis", TestComponent(label="frame", tags={"chassis"}))
    container.assign("powerplant", TestComponent(label="motor", tags={"powerplant"}))

    assert container.validate() == []


def test_slot_prerequisites_support_chained_dependencies() -> None:
    container = PrerequisiteContainer()

    with pytest.raises(ValueError, match="Missing prerequisite slots: powerplant"):
        container.assign("turret", TestComponent(label="turret", tags={"turret"}))

    container.assign("chassis", TestComponent(label="frame", tags={"chassis"}))
    container.assign("powerplant", TestComponent(label="motor", tags={"powerplant"}))
    container.assign("turret", TestComponent(label="turret", tags={"turret"}))

    assert container.validate() == []


def test_slot_prerequisite_validation_reports_broken_existing_loadout() -> None:
    container = PrerequisiteContainer()
    chassis = TestComponent(label="frame", tags={"chassis"})
    container.assign("chassis", chassis)
    container.assign("powerplant", TestComponent(label="motor", tags={"powerplant"}))
    container.assign("turret", TestComponent(label="turret", tags={"turret"}))

    container.unassign("chassis", chassis)

    assert container.validate() == [
        "Slot 'powerplant' missing prerequisite slot: chassis",
    ]


def test_slot_enablement_rejects_disabled_slot_without_required_empty_error() -> None:
    host = ConditionalHost(label="compact", frame_size="small")
    container = ConditionalContainer(owner=host)

    assert not container.is_slot_enabled("turret")
    assert container.validate() == []

    with pytest.raises(ValueError, match="Slot disabled: turret"):
        container.assign("turret", TestComponent(label="turret", tags={"turret"}))


def test_slot_enablement_allows_required_slot_when_owner_matches() -> None:
    host = ConditionalHost(label="large", frame_size="large")
    container = ConditionalContainer(owner=host)

    assert container.is_slot_enabled("turret")
    assert container.validate() == ["Required slot empty: turret"]

    container.assign("turret", TestComponent(label="turret", tags={"turret"}))

    assert container.validate() == []


def test_slot_enablement_reports_occupied_slot_after_owner_state_changes() -> None:
    host = ConditionalHost(label="large", frame_size="large")
    container = ConditionalContainer(owner=host)
    container.assign("turret", TestComponent(label="turret", tags={"turret"}))

    host.frame_size = "small"

    assert container.validate() == ["Disabled slot occupied: turret"]


def test_materialize_defaults_populates_enabled_empty_slots_in_order() -> None:
    host = ConditionalHost(label="large", frame_size="large")
    container = DefaultLoadoutContainer(owner=host)

    materialized = container.materialize_defaults()

    assert [component.label for component in materialized] == [
        "starter-frame",
        "starter-motor",
        "starter-turret",
    ]
    assert container.get_slot("chassis")[0].label == "starter-frame"
    assert container.get_slot("powerplant")[0].label == "starter-motor"
    assert container.get_slot("turret")[0].label == "starter-turret"


def test_materialize_defaults_skips_disabled_slots_and_keeps_existing_assignments() -> None:
    host = ConditionalHost(label="compact", frame_size="small")
    container = DefaultLoadoutContainer(owner=host)
    custom_frame = TestComponent(label="custom-frame", tags={"chassis"})
    container.assign("chassis", custom_frame)

    materialized = container.materialize_defaults()

    assert [component.label for component in materialized] == ["starter-motor"]
    assert container.get_slot("chassis") == [custom_frame]
    assert container.get_slot("powerplant")[0].label == "starter-motor"
    assert container.get_slot("turret") == []


def test_shape_board_star_plug_seats_in_star_socket() -> None:
    board = ShapeBoard()
    board.assign("star", shape_plug("star"))

    assert board.get_slot("star")[0].label == "star-plug"

    with pytest.raises(ValueError, match="Slot full"):
        board.assign("star", shape_plug("star"))


def test_shape_board_rejects_star_plug_in_circle_socket() -> None:
    board = ShapeBoard()

    with pytest.raises(ValueError, match="Connector shape mismatch"):
        board.assign("circle", shape_plug("star"))


def test_shape_board_rejects_two_sockets() -> None:
    board = ShapeBoard()

    with pytest.raises(ValueError, match="Connector polarity mismatch"):
        board.assign("star", shape_plug("star", polarity="socket"))


def test_shape_board_description_changes_after_assign_unassign() -> None:
    board = ShapeBoard()
    star_plug = shape_plug("star")

    assert board.describe() == EMPTY_BOARD_DESCRIPTION

    board.assign("star", star_plug)

    assert board.describe() == FILLED_STAR_BOARD_DESCRIPTION
    assert board.fold_giver_payloads("prose") == ["a filled star-shaped slot"]

    board.unassign("star", star_plug)

    assert board.describe() == EMPTY_BOARD_DESCRIPTION


def test_shape_board_changer_facets_fold_into_target_check() -> None:
    board = ShapeBoard()
    board.assign("star", shape_plug("star", challenge_op="add", challenge_value=3))
    board.assign("circle", shape_plug("circle", challenge_op="multiply", challenge_value=2))
    board.assign("square", shape_plug("square", challenge_op="subtract", challenge_value=1))

    assert board.challenge_value(initial=4) == 13
    assert board.hits_target(13, initial=4)
    assert not board.hits_target(12, initial=4)


def test_shape_board_discrete_slot_and_continuous_weight_budget_gate_assignment() -> None:
    board = WeightedShapeBoard()

    assert board.budgets is not None
    board.budgets.add_budget("weight", 2.0)
    board.assign("star", shape_plug("star", weight_cost=1.25))

    with pytest.raises(ValueError, match="Slot full"):
        board.assign("star", shape_plug("star"))

    board.assign("circle", shape_plug("circle", weight_cost=0.5))
    assert board.budgets.budgets["weight"].consumed == 1.75

    with pytest.raises(ValueError, match="Insufficient weight"):
        board.assign("square", shape_plug("square", weight_cost=0.5))
