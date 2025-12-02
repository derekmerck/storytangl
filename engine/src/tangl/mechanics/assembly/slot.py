from __future__ import annotations

from typing import Any, Callable, Optional

from pydantic import BaseModel, Field

from tangl.core import Entity


class Slot(BaseModel):
    """Slot(name: str, selection_criteria: dict[str, Any], max_count: int = 1, required: bool = False)

    Container slot that delegates eligibility checks to :meth:`tangl.core.entity.Entity.matches`.

    Key Features
    ------------
    * **Declarative selection** – ``selection_criteria`` mirrors the keyword arguments accepted by
      :meth:`~tangl.core.entity.Entity.matches`, including ``is_instance``, ``has_tags``,
      ``predicate``, and direct attribute comparisons.
    * **Capacity limits** – ``max_count`` constrains how many components may occupy the slot.
    * **Required slots** – ``required`` marks slots that must be populated during validation.

    API
    ---
    - :meth:`selects_for` – check whether a component is eligible for the slot.
    - :meth:`for_type` – convenience constructor keyed on a component type and optional tags.
    - :meth:`for_tags` – convenience constructor keyed on required tags.
    - :meth:`for_predicate` – convenience constructor keyed on an arbitrary predicate.
    """

    name: str
    selection_criteria: dict[str, Any] = Field(default_factory=dict)
    max_count: int = 1
    required: bool = False

    def selects_for(self, component: Entity) -> tuple[bool, str]:
        """Return whether ``component`` satisfies the slot's criteria.

        Parameters
        ----------
        component:
            Entity candidate to evaluate.

        Returns
        -------
        tuple[bool, str]
            ``True`` with an empty reason when the component matches; otherwise ``False`` with
            a human-readable explanation.
        """

        try:
            if component.matches(**self.selection_criteria):
                return True, ""
            return False, f"Component doesn't match criteria: {self.selection_criteria}"
        except Exception as exc:  # pragma: no cover - defensive logging
            return False, f"Error matching: {exc}"

    @classmethod
    def for_type(
        cls,
        name: str,
        component_type: type,
        tags: Optional[set[str]] = None,
        **kwargs: Any,
    ) -> "Slot":
        """Create a type-gated slot.

        Parameters
        ----------
        name:
            Slot identifier.
        component_type:
            Concrete ``Entity`` subclass required for membership.
        tags:
            Optional tag set to include in the selection criteria.
        **kwargs:
            Additional :class:`Slot` constructor kwargs.
        """

        criteria: dict[str, Any] = {"is_instance": component_type}
        if tags:
            criteria["has_tags"] = tags
        return cls(name=name, selection_criteria=criteria, **kwargs)

    @classmethod
    def for_tags(cls, name: str, tags: set[str], **kwargs: Any) -> "Slot":
        """Create a tag-gated slot using :meth:`Entity.has_tags` semantics."""

        return cls(name=name, selection_criteria={"has_tags": tags}, **kwargs)

    @classmethod
    def for_predicate(
        cls,
        name: str,
        predicate: Callable[[Entity], bool],
        **kwargs: Any,
    ) -> "Slot":
        """Create a predicate-gated slot."""

        return cls(name=name, selection_criteria={"predicate": predicate}, **kwargs)


class SlotGroup(BaseModel):
    """Aggregate validation constraints across multiple slots."""

    name: str
    slot_names: list[str]
    min_total: Optional[int] = None
    max_total: Optional[int] = None
