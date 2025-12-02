from __future__ import annotations

from typing import Iterable

from pydantic import BaseModel, Field

from tangl.core import Entity


class ResourceBudget(BaseModel):
    """ResourceBudget(name: str, capacity: float)

    Track consumption against a named capacity (power, weight, etc.).
    """

    name: str
    capacity: float
    consumed: float = 0.0

    @property
    def available(self) -> float:
        return self.capacity - self.consumed

    def can_afford(self, cost: float) -> bool:
        return self.consumed + cost <= self.capacity

    def update(self, cost: float) -> None:
        self.consumed = cost


class BudgetTracker(BaseModel):
    """Collection of :class:`ResourceBudget` entries keyed by resource name."""

    budgets: dict[str, ResourceBudget] = Field(default_factory=dict)

    def add_budget(self, name: str, capacity: float) -> None:
        self.budgets[name] = ResourceBudget(name=name, capacity=capacity)

    def recalculate(self, components: Iterable[Entity]) -> None:
        for budget in self.budgets.values():
            total = 0.0
            for component in components:
                if hasattr(component, "get_cost"):
                    total += float(getattr(component, "get_cost")(budget.name))
            budget.update(total)

    def get_errors(self) -> list[str]:
        errors = []
        for budget in self.budgets.values():
            if budget.consumed > budget.capacity:
                errors.append(
                    f"Over budget for {budget.name}: {budget.consumed:.1f}/{budget.capacity:.1f}"
                )
        return errors
