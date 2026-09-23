"""Every art pack's manifest must describe the files it actually ships."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml
from PIL import Image

WORLD = Path(__file__).resolve().parents[3] / "worlds" / "repartee_loop"
LOGICAL_SIZE = (320, 200)
PACKS = sorted(p for p in WORLD.glob("media*") if p.is_dir())
MANIFEST_PACKS = [p for p in PACKS if (p / "manifest.json").is_file()]
ASSET_NAMES = {
    "quai_bg", "salon_bg", "warehouse_bg", "quay_map",
    "clerk_sprite", "master_sprite", "worker_sprite",
}


def _entries(pack: Path):
    manifest = json.loads((pack / "manifest.json").read_text())
    return [(pack, name, entry) for name, entry in manifest["assets"].items()]


CASES = [case for pack in MANIFEST_PACKS for case in _entries(pack)]


def test_demo_ships_both_interchangeable_art_packs() -> None:
    assert {pack.name for pack in PACKS} == {"media", "media_spaceport"}


def test_world_declares_the_extent_both_packs_target() -> None:
    world = yaml.safe_load((WORLD / "world.yaml").read_text())

    assert world["metadata"]["stage_extent"] == {
        "width": LOGICAL_SIZE[0],
        "height": LOGICAL_SIZE[1],
    }


LFS_POINTER_MAGIC = b"version https://git-lfs.github.com/spec/v1"


@pytest.mark.parametrize(("pack", "name", "entry"), CASES, ids=lambda v: getattr(v, "name", v))
def test_shipped_assets_are_real_images_not_lfs_pointers(
    pack: Path, name: str, entry: dict
) -> None:
    """Fail legibly when LFS has not materialized.

    Every assertion below this one reads image bytes, so without LFS they fail
    as `UnidentifiedImageError` or a hash mismatch — neither of which names the
    actual problem. These are required assets under root `AGENTS.md` rule 3;
    see `worlds/repartee_loop/AGENTS.md` for why they are binary at all.
    """

    shipped = pack / "images" / entry["file"]
    assert shipped.is_file(), f"{pack.name} declares a missing file"
    head = shipped.read_bytes()[: len(LFS_POINTER_MAGIC)]
    assert head != LFS_POINTER_MAGIC, (
        f"{pack.name}:{name} is an unmaterialized Git LFS pointer. "
        "Run `git lfs pull`, or check out with LFS enabled."
    )


@pytest.mark.parametrize("pack", PACKS, ids=lambda p: p.name)
def test_every_pack_declares_a_manifest(pack: Path) -> None:
    assert (pack / "manifest.json").is_file()


@pytest.mark.parametrize(
    ("pack", "name", "entry"), CASES, ids=[f"{p.name}:{n}" for p, n, _ in CASES]
)
def test_manifest_hash_and_size_match_the_shipped_file(
    pack: Path, name: str, entry: dict
) -> None:
    """Conforming assets after writing a manifest is how these drift apart."""

    shipped = pack / "images" / entry["file"]
    assert shipped.is_file(), f"{pack.name} declares a missing file"

    digest = hashlib.sha256(shipped.read_bytes()).hexdigest()
    assert digest == entry["sha256"], f"{pack.name}:{name} hash describes another image"

    with Image.open(shipped) as image:
        assert list(image.size) == entry["size"]
        assert image.mode == entry["mode"]


def _is_sheet(stem: str) -> bool:
    from tangl.media.sprite_sheets import SheetName

    return SheetName.parse(stem) is not None


@pytest.mark.parametrize("pack", PACKS, ids=lambda p: p.name)
def test_packs_are_interchangeable_by_name(pack: Path) -> None:
    """A swap is one manifest line, so packs must agree on their required assets.

    Sprite sheets are the one exemption, and a deliberate one: a sheet is an
    optional alternative to a still every client can already draw, so a pack
    without sheets is a complete reskin that simply does not animate -- not a
    reskin that half works. Everything else must still match exactly.
    """

    manifest = json.loads((pack / "manifest.json").read_text())
    assert {name for name in manifest["assets"] if not _is_sheet(name)} == ASSET_NAMES
    assert {f.stem for f in (pack / "images").glob("*.png") if not _is_sheet(f.stem)} == ASSET_NAMES
    # The exemption is from pack equality, not from being declared: an undeclared
    # sheet would otherwise ship without its hash, size and mode ever being checked.
    assert {f.stem for f in (pack / "images").glob("*.png") if _is_sheet(f.stem)} == {
        Path(entry["file"]).stem for entry in manifest["assets"].values() if "sprite_sheet" in entry
    }


SHEET_CASES = [
    (pack, name, entry) for pack, name, entry in CASES if "sprite_sheet" in entry
]


def test_the_spaceport_pack_ships_a_sheet_for_every_sprite() -> None:
    """Guard against the sheet checks below passing because they found nothing."""

    assert {entry["sprite_sheet"]["of"] for pack, _n, entry in SHEET_CASES if pack.name == "media_spaceport"} == {
        "clerk_sprite", "master_sprite", "worker_sprite"
    }


@pytest.mark.parametrize(("pack", "name", "entry"), SHEET_CASES, ids=[f"{p.name}:{n}" for p, n, _ in SHEET_CASES])
def test_a_shipped_sheet_belongs_to_a_shipped_still_and_says_so_consistently(pack, name, entry) -> None:
    """The manifest, the filename and the sidecar each state the sheet's still and clips."""

    from tangl.media.sprite_sheets import SheetName, read_aseprite_export

    sheet = entry["sprite_sheet"]
    sidecar = pack / "images" / sheet["sidecar"]["file"]
    assert hashlib.sha256(sidecar.read_bytes()).hexdigest() == sheet["sidecar"]["sha256"]
    parsed = read_aseprite_export(sidecar.read_text())

    assert sheet["of"] in ASSET_NAMES
    assert SheetName.parse(Path(entry["file"]).stem).root == sheet["of"]
    assert sheet["clips"] == parsed.clip_names()
    assert [frame.pivot.model_dump() for frame in parsed.frames] == [sheet["pivot"]] * len(parsed.frames)


@pytest.mark.parametrize(("pack", "name", "entry"), SHEET_CASES, ids=[f"{p.name}:{n}" for p, n, _ in SHEET_CASES])
def test_a_shipped_sheet_offers_the_contest_clips(pack, name, entry) -> None:
    """Named with the kernel's phrase roles, so a pack supplies what the story asks for."""

    assert entry["sprite_sheet"]["clips"] == ["idle", "call", "response"]


@pytest.mark.parametrize(("pack", "name", "entry"), SHEET_CASES, ids=[f"{p.name}:{n}" for p, n, _ in SHEET_CASES])
def test_frame_zero_of_a_shipped_sheet_is_its_still(pack, name, entry) -> None:
    """The art invariant, checked on the committed bytes.

    A client switches from the still to a clip without the character moving only
    if the first frame, placed by the manifest's own placement law, is the still.
    Compared on visible pixels: the still keeps whatever colour its cutout left
    under transparency, and the sheet deliberately zeroes it.
    """

    from tangl.media.sprite_sheets import read_aseprite_export

    sheet = read_aseprite_export((pack / "images" / entry["sprite_sheet"]["sidecar"]["file"]).read_text())
    with Image.open(pack / "images" / f"{entry['sprite_sheet']['of']}.png") as still_image:
        still = still_image.convert("RGBA")
    with Image.open(pack / "images" / entry["file"]) as sheet_image:
        atlas = sheet_image.convert("RGBA")

    index = sheet.play_order("idle")[0]
    rect, at = sheet.frames[index].rect, sheet.placement(index, still.size)
    left, top = rect.x - at.x, rect.y - at.y
    region = atlas.crop((left, top, left + still.width, top + still.height))

    a, b = region.load(), still.load()
    differing = sum(
        1
        for x in range(still.width)
        for y in range(still.height)
        if (a[x, y][3] > 0) != (b[x, y][3] > 0) or (b[x, y][3] > 0 and a[x, y] != b[x, y])
    )
    assert differing == 0


@pytest.mark.parametrize("pack", MANIFEST_PACKS, ids=lambda p: p.name)
def test_the_indexer_accepts_every_shipped_sheet_and_attaches_it(pack: Path) -> None:
    """The real loader, not a re-reading of the JSON: what a world load would do."""

    from tangl.media.media_resource.resource_manager import ResourceManager

    manager = ResourceManager(pack)
    manager.index_directory("images")
    manifest = json.loads((pack / "manifest.json").read_text())
    expected: dict[str, list[str]] = {}
    for entry in manifest["assets"].values():
        if "sprite_sheet" in entry:
            expected.setdefault(entry["sprite_sheet"]["of"], []).append(entry["file"])

    for still in ASSET_NAMES:
        if still.endswith("_sprite"):
            attached = [ref.path.name for ref in manager.get_rit(f"{still}.png").sprite_sheets]
            assert attached == sorted(expected.get(still, []))


# Full-frame assets fill the logical surface; sprites are trimmed and share a
# height. The map plate is full-frame without being scenery — no client stages
# it as a background, since it carries media_role "map_im" — so it is named
# here rather than caught by the "_bg" suffix.
FULL_FRAME_ASSETS = {"quay_map"}


def _is_full_frame(stem: str) -> bool:
    return stem.endswith("_bg") or stem in FULL_FRAME_ASSETS


@pytest.mark.parametrize("pack", PACKS, ids=lambda p: p.name)
def test_shipped_assets_are_conformed_to_the_client_target(pack: Path) -> None:
    for shipped in (pack / "images").glob("*.png"):
        with Image.open(shipped) as image:
            if _is_full_frame(shipped.stem):
                assert image.size == (320, 200)
            else:
                assert image.size[1] == 112


def test_opening_media_wire_payload_separates_role_from_shape() -> None:
    """The DTO gives clients semantic intent and an independent layout hint."""

    from tangl.persistence import PersistenceManagerFactory
    from tangl.service.service_manager import ServiceManager

    manager = ServiceManager(PersistenceManagerFactory.native_in_mem())
    user_id = manager.create_user().details["user_id"]
    envelope = manager.create_story(user_id=user_id, world_id="repartee_loop")
    fragments = envelope.to_dto()["fragments"]
    payload = next(fragment for fragment in fragments if fragment["fragment_type"] == "media")

    assert payload["media_role"] == "narrative_im"
    assert payload["staging_hints"]["media_shape"] == "landscape"
