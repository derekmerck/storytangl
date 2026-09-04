"""Typed interaction and key/value intent contracts for journal fragments."""

from __future__ import annotations

from typing import Annotated, Any, Literal, TypeAlias

from pydantic import ConfigDict, Field

from tangl.core.bases import Unstructurable


PrimitiveValue: TypeAlias = str | int | float | bool


class IntentModel(Unstructurable):
    """Base for UI-facing intent models with forward-compatible extra fields.

    Constructor-form capable so that fields holding these value objects can opt
    into recursion with ``json_schema_extra={"unstructurable": True}``. That
    matters for the discriminated unions below: ``unstructure()`` elides
    defaults, and a union tag such as ``kind: Literal["pick"] = "pick"`` is
    indistinguishable from a default, so a flat ``model_dump`` drops it and the
    payload can no longer be re-validated against its union. Constructor form
    carries its own discriminator -- ``kind`` holds the class -- so recursing
    keeps the tag without re-admitting every other default.

    The DTO projection is a separate path (:func:`tangl.journal.fragments.
    fragment_to_dto`) and keeps the string ``kind`` literal for wire consumers.
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class KvRow(IntentModel):
    """Unified key/value row for scene-bound and projected-state surfaces."""

    key: str
    value: PrimitiveValue
    max: PrimitiveValue | None = None
    delta: int | float | None = None
    unit: str | None = None
    hint: Literal["bar", "fraction", "delta", "tag"] | None = None
    emphasis: Literal["ok", "warn", "danger", "subtle"] | None = None
    presentation_hints: dict[str, Any] | None = Field(None, alias="hints")


class CostPreview(IntentModel):
    """Advisory cost display. Backend validation remains authoritative."""

    ledger_key: str
    delta: int | float
    unit: str | None = None


class Blocker(IntentModel):
    """Player-facing explanation for an unavailable choice."""

    code: str
    message: str
    refs: list[str] = Field(default_factory=list)


class PieceConstraints(IntentModel):
    """Constraints on a ``pieces`` or ``place`` selection."""

    same_property: list[str] | None = None
    different_property: list[str] | None = None
    target_zone_ref: str | None = None
    source_zone_ref: str | None = None
    target_kind: list[str] | None = None
    predicate_ref: str | None = None


class LengthValidator(IntentModel):
    kind: Literal["length"] = "length"
    min: int | None = None
    max: int | None = None


class RegexValidator(IntentModel):
    kind: Literal["regex"] = "regex"
    pattern: str
    flags: str | None = None
    message: str | None = None


class EnumValidator(IntentModel):
    kind: Literal["enum"] = "enum"
    values: list[str]
    case_sensitive: bool = False


class BackendValidator(IntentModel):
    """Opaque marker. Only the backend can evaluate this validator."""

    kind: Literal["backend"] = "backend"


Validator: TypeAlias = Annotated[
    LengthValidator | RegexValidator | EnumValidator | BackendValidator,
    Field(discriminator="kind"),
]


class PickAccepts(IntentModel):
    kind: Literal["pick"] = "pick"
    cost_previews: list[CostPreview] = Field(default_factory=list)


class TextAccepts(IntentModel):
    kind: Literal["text"] = "text"
    required: bool = True
    placeholder: str | None = None
    validators: list[Validator] = Field(
        default_factory=list, json_schema_extra={"unstructurable": True}
    )


class QuantityAccepts(IntentModel):
    kind: Literal["quantity"] = "quantity"
    required: bool = True
    min: int | None = None
    max: int | None = None
    step: int = 1
    unit: str | None = None
    ledger_ref: str | None = None
    cost_previews: list[CostPreview] = Field(default_factory=list)


class PiecesAccepts(IntentModel):
    kind: Literal["pieces"] = "pieces"
    min: int = 1
    max: int = 1
    constraints: PieceConstraints | None = None


class PlaceAccepts(IntentModel):
    kind: Literal["place"] = "place"
    source_zone_ref: str | None = None
    target_zone_ref: str | None = None
    edge_ref: str | None = None
    predicate_ref: str | None = None
    source_constraints: PieceConstraints | None = None
    required: bool = True


NonComposeAccepts: TypeAlias = Annotated[
    PickAccepts
    | TextAccepts
    | QuantityAccepts
    | PiecesAccepts
    | PlaceAccepts,
    Field(discriminator="kind"),
]


class ComposePart(IntentModel):
    role: str
    accepts: NonComposeAccepts = Field(..., json_schema_extra={"unstructurable": True})


class ComposeAccepts(IntentModel):
    kind: Literal["compose"] = "compose"
    parts: list[ComposePart] = Field(..., json_schema_extra={"unstructurable": True})


Accepts: TypeAlias = Annotated[
    PickAccepts
    | TextAccepts
    | QuantityAccepts
    | PiecesAccepts
    | PlaceAccepts
    | ComposeAccepts,
    Field(discriminator="kind"),
]


class UIHints(IntentModel):
    """Advisory renderer hints for choices."""

    hotkey: str | None = None
    icon: str | None = None
    emphasis: Literal["primary", "subtle", "warning", "danger"] | None = None
    widget: str | None = None
    source_kind: str | None = None
    contribution: str | None = None
    direction: str | None = None
    time_delta: Any = None
    cost_previews: list[CostPreview] = Field(default_factory=list)


__all__ = [
    "Accepts",
    "BackendValidator",
    "Blocker",
    "ComposeAccepts",
    "ComposePart",
    "CostPreview",
    "EnumValidator",
    "KvRow",
    "LengthValidator",
    "NonComposeAccepts",
    "PickAccepts",
    "PieceConstraints",
    "PiecesAccepts",
    "PlaceAccepts",
    "PrimitiveValue",
    "QuantityAccepts",
    "RegexValidator",
    "TextAccepts",
    "UIHints",
    "Validator",
]
