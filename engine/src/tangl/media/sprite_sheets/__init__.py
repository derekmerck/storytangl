"""Sprite sheets as media: importing authored sheets and attaching them to stills.

Clients see only :class:`~tangl.presentation.sprite_sheet.SpriteSheetManifest`.
Everything that produces one lives here -- the Aseprite export reader, the
filename and compact shorthands, and the indexing policy that pairs each sheet
with its still -- so the presentation layer stays a vocabulary, not a format library.
"""

from .aseprite import AsepriteExport, read_aseprite_export
from .index import SpriteSheetError, link_sprite_sheets, load_sheet_manifest
from .ref import SpriteSheetRef
from .shorthand import CompactSheet, SheetName

__all__ = [
    "AsepriteExport",
    "CompactSheet",
    "SheetName",
    "SpriteSheetError",
    "SpriteSheetRef",
    "link_sprite_sheets",
    "load_sheet_manifest",
    "read_aseprite_export",
]
