"""Find sprite sheets among indexed media and attach them to their stills.

Indexing is file by file, and a sheet names its still in its own filename
(``master_sprite-idle-4x1.png`` belongs to ``master_sprite``). Which file happens
to be indexed first is an accident of sorting -- ``-`` sorts before ``.``, so a
sheet is always seen before its still -- so linking cannot happen per file. It runs
once over everything a pass indexed, and rebuilds every still's list from scratch,
so running it again is harmless.

A malformed sheet fails here, loudly, at world load, and so does a set of sheets a
client could not choose between. A sheet that is merely unused -- no still of its
name -- is not an error: it is inert, like a map region no location claims.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import TYPE_CHECKING

from tangl.media.media_data_type import MediaDataType
from tangl.presentation.sprite_sheet import SpriteSheetManifest

from .aseprite import read_aseprite_export
from .ref import SpriteSheetRef
from .shorthand import SheetName

if TYPE_CHECKING:
    from tangl.media.media_resource.media_resource_inv_tag import MediaResourceInventoryTag as MediaRIT


class SpriteSheetError(ValueError):
    """A sheet whose manifest, name and image cannot all be true at once."""


def load_sheet_manifest(path: Path, name: SheetName) -> SpriteSheetManifest:
    """The manifest for one sheet image: its Aseprite sidecar, or its name expanded.

    A sidecar is authoritative, but it cannot contradict the image or what the
    filename states, because two declarations of one fact that disagree would
    otherwise be settled by whichever a client happened to read.
    """

    from PIL import Image

    with Image.open(path) as image:
        size = image.size

    sidecar = path.with_suffix(".json")
    if not sidecar.is_file():
        try:
            return name.compact().to_manifest(path.name, size)
        except ValueError as exc:
            raise SpriteSheetError(f"{path.name}: {exc}") from exc

    try:
        manifest = read_aseprite_export(sidecar.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise SpriteSheetError(f"{sidecar.name} is not a usable sprite-sheet export: {exc}") from exc

    problems: list[str] = []
    if (manifest.size.w, manifest.size.h) != size:
        problems.append(f"declares {manifest.size.w}x{manifest.size.h} but the image is {size[0]}x{size[1]}")
    if manifest.image != path.name:
        problems.append(f"names image {manifest.image!r}, not {path.name!r}")
    problems += name.disagreements(manifest)
    if problems:
        raise SpriteSheetError(f"{sidecar.name} disagrees with {path.name}: " + "; ".join(problems))
    return manifest


def _hex(record: "MediaRIT") -> str:
    digest = record.content_hash()
    return digest.hex() if isinstance(digest, bytes) else str(digest)


def _refuse_ambiguity(still: str, refs: list[SpriteSheetRef]) -> None:
    """Every clip name a use could ask for must lead to exactly one sheet.

    A sheet without clips answers to any name, so it can only serve a still alone:
    beside another sheet, a request for a clip the other lacks would reach it by
    elimination, and filename order would decide the rest.
    """

    untagged = [ref.path.name for ref in refs if not ref.manifest.clips]
    if untagged and len(refs) > 1:
        raise SpriteSheetError(
            f"{untagged[0]} has no clips, so it answers to every clip name, and cannot "
            f"share {still!r} with {sorted(ref.path.name for ref in refs if ref.path.name != untagged[0])}"
        )
    claimed: dict[str, str] = {}
    for ref in refs:
        for clip in ref.manifest.clip_names():
            if clip in claimed:
                raise SpriteSheetError(
                    f"{claimed[clip]} and {ref.path.name} both define clip {clip!r} for {still!r}; "
                    "a client asked for it could not tell which to play"
                )
            claimed[clip] = ref.path.name


def link_sprite_sheets(records: Iterable["MediaRIT"]) -> None:
    """Attach manifests to sheets and references to the stills they belong to."""

    stills: dict[str, list["MediaRIT"]] = {}
    sheets: list[tuple["MediaRIT", SheetName]] = []
    for record in records:
        path = getattr(record, "path", None)
        if not isinstance(path, Path) or record.data_type is not MediaDataType.IMAGE:
            continue
        name = SheetName.parse(path.stem)
        if name is None:
            stills.setdefault(path.stem, []).append(record)
        else:
            sheets.append((record, name))

    refs: dict[str, list[SpriteSheetRef]] = {}
    for record, name in sorted(sheets, key=lambda pair: pair[0].path.name):
        manifest = load_sheet_manifest(record.path, name)
        record.sprite_sheet = manifest
        refs.setdefault(name.root, []).append(
            SpriteSheetRef(path=record.path, rit_id=record.uid, content_hash=_hex(record), manifest=manifest)
        )

    for root, group in stills.items():
        attached = refs.get(root, [])
        if attached:
            _refuse_ambiguity(root, attached)
        for still in group:
            still.sprite_sheets = list(attached)


__all__ = ["SpriteSheetError", "link_sprite_sheets", "load_sheet_manifest"]
