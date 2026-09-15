"""Find sprite sheets among indexed media and attach them to their stills.

Indexing is file by file, and a sheet names its still in its own filename
(``master_sprite-idle-4x1.png`` belongs to ``master_sprite``). Which file happens
to be indexed first is an accident of sorting -- ``-`` sorts before ``.``, so a
sheet is always seen before its still -- so linking cannot happen per file. It runs
once over everything a pass indexed, and rebuilds every still's list from scratch,
so running it again is harmless.

A malformed sheet fails here, loudly, at world load. A sheet that is merely
unused -- no still of its name -- is not an error: it is inert, like a map region
no location claims.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import ValidationError

from tangl.media.media_data_type import MediaDataType
from tangl.presentation.sprite_sheet import SheetName, SpriteSheetManifest

from .sprite_sheet_ref import SpriteSheetRef

if TYPE_CHECKING:
    from .media_resource_inv_tag import MediaResourceInventoryTag as MediaRIT


class SpriteSheetError(ValueError):
    """A sheet whose manifest, name and image cannot all be true at once."""


def load_sheet_manifest(path: Path, name: SheetName) -> SpriteSheetManifest:
    """The manifest for one sheet image: its sidecar export, or its name expanded.

    A sidecar is authoritative, but it cannot contradict what the filename states:
    grid, clip and total are each checked, because two declarations of one fact
    that disagree would otherwise be settled by whichever a client happened to read.
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
        manifest = SpriteSheetManifest.model_validate_json(sidecar.read_text(encoding="utf-8"))
    except ValidationError as exc:
        raise SpriteSheetError(f"{sidecar.name} is not a usable sprite-sheet export: {exc}") from exc

    problems: list[str] = []
    if (manifest.meta.size.w, manifest.meta.size.h) != size:
        problems.append(f"declares {manifest.meta.size.w}x{manifest.meta.size.h} but the image is {size[0]}x{size[1]}")
    if manifest.meta.image != path.name:
        problems.append(f"names image {manifest.meta.image!r}, not {path.name!r}")
    try:
        manifest.check_grid(name.cols, name.rows)
    except ValueError as exc:
        problems.append(str(exc))
    if name.clip is not None and name.clip not in manifest.clip_names():
        problems.append(f"the filename names clip {name.clip!r}, which the export does not tag")
    if name.total_ms is not None and sum(f.duration for f in manifest.frames) != name.total_ms:
        problems.append(
            f"the filename says {name.total_ms} ms, the export's frames last "
            f"{sum(f.duration for f in manifest.frames)} ms"
        )
    if problems:
        raise SpriteSheetError(f"{sidecar.name} disagrees with {path.name}: " + "; ".join(problems))
    return manifest


def _hex(record: "MediaRIT") -> str:
    digest = record.content_hash()
    return digest.hex() if isinstance(digest, bytes) else str(digest)


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

    for group in stills.values():
        for still in group:
            still.sprite_sheets = []

    for record, name in sorted(sheets, key=lambda pair: pair[0].path.name):
        manifest = load_sheet_manifest(record.path, name)
        record.sprite_sheet = manifest
        ref = SpriteSheetRef(path=record.path, rit_id=record.uid, content_hash=_hex(record), manifest=manifest)
        for still in stills.get(name.root, []):
            claimed = {clip for existing in still.sprite_sheets for clip in existing.manifest.clip_names()}
            clash = claimed & set(manifest.clip_names())
            if clash:
                raise SpriteSheetError(
                    f"{record.path.name} and another sheet for {name.root!r} both define "
                    f"clip(s) {sorted(clash)}; a client asked for one could not tell which to play"
                )
            still.sprite_sheets = [*still.sprite_sheets, ref]


__all__ = ["SpriteSheetError", "link_sprite_sheets", "load_sheet_manifest"]
