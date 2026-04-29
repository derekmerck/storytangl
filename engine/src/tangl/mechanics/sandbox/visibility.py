"""Visibility projection rules for sandbox locations."""

from __future__ import annotations

from pydantic import BaseModel, Field

from tangl.core.runtime_op import Predicate


class SandboxProjectionState(BaseModel):
    """Result of evaluating sandbox visibility rules for one location."""

    active_rules: list[str] = Field(default_factory=list)
    journal_text: str | None = None
    suppress_location_description: bool = False
    suppress_asset_affordances: bool = False
    suppress_fixture_affordances: bool = False

    @property
    def active(self) -> bool:
        """Return whether any projection rule changed the default view."""
        return bool(self.active_rules)


class SandboxVisibilityRule(BaseModel):
    """Declarative rule that filters sandbox journaling and affordances."""

    label: str = "darkness"
    kind: str = "visibility"
    when: list[Predicate] = Field(
        default_factory=lambda: [
            Predicate(expr="not sandbox_location_lit"),
            Predicate(expr="not sandbox_has_lit_light_source()"),
        ]
    )
    journal_text: str = "It is now pitch dark. If you proceed you will likely fall into a pit."
    suppress_location_description: bool = True
    suppress_asset_affordances: bool = True
    suppress_fixture_affordances: bool = True

    def active_in(self, ns: dict[str, object]) -> bool:
        """Return whether all rule predicates hold in the supplied namespace."""
        return all(predicate.satisfied_by(ns) for predicate in self.when)

    def apply_to(self, state: SandboxProjectionState) -> SandboxProjectionState:
        """Return a projection state with this rule applied."""
        return state.model_copy(
            update={
                "active_rules": [*state.active_rules, self.label],
                "journal_text": self.journal_text or state.journal_text,
                "suppress_location_description": (
                    state.suppress_location_description
                    or self.suppress_location_description
                ),
                "suppress_asset_affordances": (
                    state.suppress_asset_affordances
                    or self.suppress_asset_affordances
                ),
                "suppress_fixture_affordances": (
                    state.suppress_fixture_affordances
                    or self.suppress_fixture_affordances
                ),
            }
        )
