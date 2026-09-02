"""Every art pack's manifest must describe the files it actually ships."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from PIL import Image

WORLD = Path(__file__).resolve().parents[3] / "worlds" / "repartee_loop"
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


@pytest.mark.parametrize("pack", PACKS, ids=lambda p: p.name)
def test_packs_are_interchangeable_by_name(pack: Path) -> None:
    """A swap is one manifest line, so packs must agree on asset names."""

    manifest = json.loads((pack / "manifest.json").read_text())
    assert set(manifest["assets"]) == ASSET_NAMES
    assert {f.stem for f in (pack / "images").glob("*.png")} == ASSET_NAMES


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
