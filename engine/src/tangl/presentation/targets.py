"""Explicit presentation addresses, independent of journal or device state."""

from __future__ import annotations

from typing import Annotated, Literal, TypeAlias
from uuid import UUID

from pydantic import ConfigDict, Field

from tangl.core.bases import Unstructurable


class FragmentTarget(Unstructurable):
    """One exact journal occurrence, not its source entity."""
    model_config = ConfigDict(extra="forbid")
    kind: Literal["fragment"] = "fragment"
    fragment_id: UUID


class RitTarget(Unstructurable):
    """Current presentations of one resource."""
    model_config = ConfigDict(extra="forbid")
    kind: Literal["rit"] = "rit"
    rit_id: UUID


class RoleTarget(Unstructurable):
    """Current presentations in a screen role/slot."""
    model_config = ConfigDict(extra="forbid")
    kind: Literal["role"] = "role"
    media_role: str = Field(min_length=1)


class HandleTarget(Unstructurable):
    """A stable authored binding, independent of resource identity."""
    model_config = ConfigDict(extra="forbid")
    kind: Literal["handle"] = "handle"
    handle: str = Field(min_length=1)


PresentationTarget: TypeAlias = Annotated[
    FragmentTarget | RitTarget | RoleTarget | HandleTarget, Field(discriminator="kind"),
]
