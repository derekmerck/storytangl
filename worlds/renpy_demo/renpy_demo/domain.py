from __future__ import annotations

from tangl.story import Actor


class RenPyGuide(Actor):
    """Guide actor with simple dialog styling for the Ren'Py demo."""

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
