from __future__ import annotations

from pydantic import Field

from tangl.mechanics.presence.look import (
    BodyPhenotype,
    EyeColor,
    HairColor,
    HairStyle,
    Look,
    SkinTone,
)
from tangl.mechanics.presence.look.look import HasLook
from tangl.story import Actor


class RenPyGuide(Actor, HasLook):
    """Guide actor with simple dialog styling and visual presence data."""

    look: Look = Field(
        default_factory=lambda: Look(
            hair_color=HairColor.DARK,
            hair_style=HairStyle.MESSY,
            eye_color=EyeColor.GRAY,
            skin_tone=SkinTone.OLIVE,
            body_phenotype=BodyPhenotype.FIT,
        )
    )

    def goes_by(self, alias: str) -> bool:
        normalized = alias.strip().casefold()
        return normalized in {
            "guide",
            self.name.casefold(),
            self.get_label().casefold(),
        }

    def get_dialog_style(self, dialog_class: str | None = None) -> dict[str, str]:
        if dialog_class and dialog_class.lower().endswith(".concerned"):
            return {"font-weight": "700", "letter-spacing": "0.02em"}
        return {"font-weight": "600"}
