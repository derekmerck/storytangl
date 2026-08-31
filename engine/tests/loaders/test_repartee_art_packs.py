"""Every art pack's manifest must describe the files it actually ships."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from PIL import Image

WORLD = Path(__file__).resolve().parents[3] / "worlds" / "repartee_loop"
PACKS = sorted(p for p in WORLD.glob("media*") if (p / "manifest.json").is_file())
ASSET_NAMES = {
    "quai_bg", "salon_bg", "warehouse_bg",
    "clerk_sprite", "master_sprite", "worker_sprite",
}


def _entries(pack: Path):
    manifest = json.loads((pack / "manifest.json").read_text())
    return [(pack, name, entry) for name, entry in manifest["assets"].items()]


CASES = [case for pack in PACKS for case in _entries(pack)]


def test_every_pack_declares_a_manifest() -> None:
    assert {p.name for p in PACKS} == {"media", "media_spaceport"}


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

    assert {f.stem for f in (pack / "images").glob("*.png")} == ASSET_NAMES


@pytest.mark.parametrize("pack", PACKS, ids=lambda p: p.name)
def test_shipped_assets_are_conformed_to_the_client_target(pack: Path) -> None:
    for shipped in (pack / "images").glob("*.png"):
        with Image.open(shipped) as image:
            if shipped.stem.endswith("_bg"):
                assert image.size == (320, 200)
            else:
                assert image.size[1] == 112
