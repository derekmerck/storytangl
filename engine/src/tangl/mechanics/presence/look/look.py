"""Appearance profile and author-facing facet surfaces for presence mechanics.

This module gives the ``presence/look`` family a first explicit contract:

- ``Look`` stores body-trait state and produces deterministic appearance summaries.
- ``LookMediaPayload`` is a structured adapter artifact for downstream media hooks.
- ``HasLook`` is the thin author-facing facade that binds look, outfit, and
  ornaments into namespace-friendly story surfaces.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import AliasChoices, Field, field_validator, model_validator

from tangl.lang.age_range import AgeRange
from tangl.core import Entity, contribute_ns
from tangl.lang.gens import Gens
from tangl.lang.helpers import oxford_join
from tangl.utils.base_model_plus import BaseModelPlus

from .enums import HairColor, HairStyle, BodyPhenotype, SkinTone, EyeColor
from ..ornaments import Ornamentation
from ..outfit import OutfitManager


def _ctx_value(ctx: Any, key: str) -> Any:
    if ctx is None:
        return None
    if isinstance(ctx, dict):
        return ctx.get(key)
    return getattr(ctx, key, None)


def _enum_name_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, Enum):
        return value.name.lower().replace("_", " ")
    if isinstance(value, str):
        return value.replace("_", " ")
    return str(value)


def _string_value_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, Enum) and isinstance(value.value, str):
        return value.value.replace("_", " ")
    return _enum_name_text(value)


def _raw_value_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, Enum) and isinstance(value.value, str):
        return value.value
    if isinstance(value, str):
        return value
    return str(value)


class LookMediaPayload(BaseModelPlus):
    """Structured appearance payload for media adaptation.

    Why
    ----
    ``LookMediaPayload`` is the first explicit runtime artifact for the
    ``presence/look`` render boundary. It lets world or engine media adapters
    consume a stable appearance payload without reaching back into author models
    ad hoc.
    """

    description: str = ""
    traits: dict[str, Any] = Field(default_factory=dict)
    outfit_tokens: list[str] = Field(default_factory=list)
    ornament_tokens: list[str] = Field(default_factory=list)
    pose: str | None = None
    attitude: str | None = None
    media_role: str | None = None


class Look(Entity):
    """Look()

    Deterministic body-trait profile for appearance-oriented mechanics.

    Why
    ----
    ``Look`` stores the reusable physical-profile state that presence-oriented
    facets and media adapters can project into prose, prompt context, or richer
    rendering later on.

    Key Features
    ------------
    - Stores stable body-trait and presentation-vector fields.
    - Produces concise, deterministic descriptive fragments.
    - Adapts body traits into a structured media payload without depending on
      a specific image or audio backend.
    """

    # default_reduce_flag: ClassVar[bool] = True

    hair_color: HairColor = None
    eye_color: EyeColor = None
    body_phenotype: BodyPhenotype = Field(
        None,
        alias="phenotype",
        validation_alias=AliasChoices("body_phenotype", "phenotype"),
    )
    skin_tone: SkinTone = None
    hair_style: HairStyle = None
    apparent_age: AgeRange = None

    @field_validator("skin_tone", "hair_color", "hair_style", mode="before")
    @classmethod
    def _replace_spaces(cls, value: Any) -> Any:
        if isinstance(value, str):
            value = value.replace(" skin", "")
            value = value.replace(" hair", "")
        return value

    # body type vector for more specific stats:
    sz: float = 0.5      # size scalar for relative renders, f: (0-0.7), m: (0.3-1.0)
    fit: float = 0.5     # average bmi, fit < 0.3, heavy > 0.7

    # face
    f2m: float = 0.5          # fem < 0.4, masc > 0.6
    aesthetics: float = 0.5   # average

    @property
    def apparent_gender(self) -> Gens:
        if self.f2m <= 0.4:
            return Gens.XX
        elif self.f2m <= 0.6:
            return Gens.X_
        return Gens.XY

    reference_model: str = None

    preg: bool = False

    # todo: handle makeup similar to ornament?

    def trait_tokens(self) -> list[str]:
        """Return concise visible-trait phrases for prose or prompt use."""
        traits: list[str] = []

        if self.skin_tone is not None:
            traits.append(f"{_enum_name_text(self.skin_tone)} skin")
        if self.eye_color is not None:
            traits.append(f"{_enum_name_text(self.eye_color)} eyes")
        if self.hair_style is HairStyle.BALD:
            traits.append("a bald head")
        else:
            hair_bits = [
                bit
                for bit in (
                    _enum_name_text(self.hair_color),
                    _enum_name_text(self.hair_style),
                )
                if bit
            ]
            if hair_bits:
                traits.append(f"{' '.join(hair_bits)} hair")
        if self.body_phenotype is not None:
            traits.append(f"{_enum_name_text(self.body_phenotype)} build")

        return traits

    def media_traits(self) -> dict[str, Any]:
        """Return structured appearance traits for adapter layers."""
        payload: dict[str, Any] = {
            "apparent_gender": self.apparent_gender.value,
            "sz": self.sz,
            "fit": self.fit,
            "f2m": self.f2m,
            "aesthetics": self.aesthetics,
            "pregnant": self.preg,
        }

        if self.hair_color is not None:
            payload["hair_color"] = _enum_name_text(self.hair_color)
        if self.eye_color is not None:
            payload["eye_color"] = _enum_name_text(self.eye_color)
        if self.body_phenotype is not None:
            payload["body_phenotype"] = _enum_name_text(self.body_phenotype)
        if self.skin_tone is not None:
            payload["skin_tone"] = _enum_name_text(self.skin_tone)
        if self.hair_style is not None:
            payload["hair_style"] = _enum_name_text(self.hair_style)
        if self.apparent_age is not None:
            payload["apparent_age"] = _enum_name_text(self.apparent_age)
        if self.reference_model:
            payload["reference_model"] = self.reference_model

        return payload

    def describe(
        self,
        *,
        ctx: Any = None,
        outfit: OutfitManager | None = None,
        ornamentation: Ornamentation | None = None,
        attitude: Any = None,
        pose: Any = None,
        subject: str | None = None,
        **_: Any,
    ) -> str:
        """Return a concise deterministic appearance phrase."""
        outfit = outfit or _ctx_value(ctx, "outfit")
        ornamentation = ornamentation or _ctx_value(ctx, "ornamentation")
        attitude = attitude or _ctx_value(ctx, "attitude")
        pose = pose or _ctx_value(ctx, "pose")

        modifiers: list[str] = []
        trait_summary = oxford_join(self.trait_tokens())
        if trait_summary:
            modifiers.append(f"with {trait_summary}")

        outfit_description = outfit.describe() if outfit is not None else ""
        if outfit_description:
            modifiers.append(f"wearing {outfit_description}")

        ornament_description = (
            ornamentation.describe_summary(possessive="their")
            if ornamentation is not None
            else ""
        )
        if ornament_description:
            modifiers.append(f"marked by {ornament_description}")

        attitude_text = _string_value_text(attitude)
        if attitude_text:
            modifiers.append(f"with a {attitude_text} demeanor")

        pose_text = _string_value_text(pose)
        if pose_text:
            modifiers.append(f"in a {pose_text} pose")

        if not modifiers:
            return subject or ""

        if subject:
            description = f"{subject} {modifiers[0]}"
        else:
            description = modifiers[0]
        for modifier in modifiers[1:]:
            description = f"{description}, {modifier}"
        return description

    def adapt_media_spec(
        self,
        *,
        ctx: Any = None,
        outfit: OutfitManager | None = None,
        ornamentation: Ornamentation | None = None,
        media_role: Any = None,
        attitude: Any = None,
        pose: Any = None,
        **_: Any,
    ) -> LookMediaPayload:
        """Build a structured appearance payload for media adapters."""
        outfit = outfit or _ctx_value(ctx, "outfit")
        ornamentation = ornamentation or _ctx_value(ctx, "ornamentation")
        media_role = media_role or _ctx_value(ctx, "media_role")
        attitude = attitude or _ctx_value(ctx, "attitude")
        pose = pose or _ctx_value(ctx, "pose")

        return LookMediaPayload(
            description=self.describe(
                ctx=ctx,
                outfit=outfit,
                ornamentation=ornamentation,
                attitude=attitude,
                pose=pose,
            ),
            traits=self.media_traits(),
            outfit_tokens=outfit.describe_items() if outfit is not None else [],
            ornament_tokens=(
                ornamentation.describe_items(possessive="their")
                if ornamentation is not None
                else []
            ),
            pose=_string_value_text(pose),
            attitude=_string_value_text(attitude),
            media_role=_raw_value_text(media_role),
        )


class HasLook(Entity):
    """HasLook()

    Thin facade exposing look, outfit, and ornaments on story-capable entities.

    Why
    ----
    ``HasLook`` is the author-facing surface for the ``presence/look`` family.
    It keeps attachment points explicit by contributing appearance symbols to the
    local namespace and by exposing deterministic description/media helpers.
    """

    look: Look = Field(default_factory=Look)
    outfit: OutfitManager = Field(default_factory=OutfitManager)
    ornamentation: Ornamentation = Field(default_factory=Ornamentation)

    @model_validator(mode="after")
    def _bind_presence_owner(self) -> "HasLook":
        if self.outfit.owner is None:
            self.outfit.owner = self
        return self

    def describe_look(
        self,
        *,
        ctx: Any = None,
        subject: str | None = None,
        attitude: Any = None,
        pose: Any = None,
    ) -> str:
        """Return a deterministic appearance phrase for this entity."""
        return self.look.describe(
            ctx=ctx,
            subject=subject,
            outfit=self.outfit,
            ornamentation=self.ornamentation,
            attitude=attitude,
            pose=pose,
        )

    def adapt_look_media_spec(
        self,
        *,
        ctx: Any = None,
        media_role: Any = None,
        attitude: Any = None,
        pose: Any = None,
    ) -> LookMediaPayload:
        """Return the structured appearance payload for media adapters."""
        return self.look.adapt_media_spec(
            ctx=ctx,
            outfit=self.outfit,
            ornamentation=self.ornamentation,
            media_role=media_role,
            attitude=attitude,
            pose=pose,
        )

    @contribute_ns
    def provide_look_symbols(self) -> dict[str, Any]:
        """Publish appearance symbols into the entity-local namespace."""
        payload: dict[str, Any] = {
            "look": self.look,
            "look_description": self.describe_look(),
            "look_media_payload": self.adapt_look_media_spec(),
            "outfit": self.outfit,
            "ornamentation": self.ornamentation,
            "apparent_gender": self.look.apparent_gender,
        }

        outfit_description = self.outfit.describe()
        if outfit_description:
            payload["outfit_description"] = outfit_description

        ornament_description = self.ornamentation.describe_summary(possessive="their")
        if ornament_description:
            payload["ornament_description"] = ornament_description

        if self.look.apparent_age is not None:
            payload["apparent_age"] = self.look.apparent_age

        return payload

    def _provide_look_desc(self) -> dict[str, str]:
        """Compatibility helper for older code paths expecting a look map."""
        return {"look": self.describe_look()}

    def _provide_media_spec(self) -> LookMediaPayload:
        """Compatibility helper returning the structured look media payload."""
        return self.adapt_look_media_spec()
