"""Scene-plate packs must describe the files they actually ship.

Mirrors ``test_repartee_art_packs`` for the two worlds whose art is a single
pack of block backgrounds rather than interchangeable skins. Kept separate
because those worlds make a different claim: repartee proves a *reskin*, these
prove that a world with no art and a world with art differ only in a media
directory.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from PIL import Image

WORLDS = Path(__file__).resolve().parents[3] / "worlds"
PACKS = [WORLDS / "hall_monitor" / "media", WORLDS / "coronate_the_regent" / "media"]
LFS_POINTER_MAGIC = b"version https://git-lfs.github.com/spec/v1"
LOGICAL_SIZE = (320, 200)


def _cases():
    for pack in PACKS:
        manifest = json.loads((pack / "manifest.json").read_text())
        for name, entry in manifest["assets"].items():
            yield pack, name, entry


CASES = list(_cases())
IDS = [f"{pack.parent.name}:{name}" for pack, name, _ in CASES]


@pytest.mark.parametrize(("pack", "name", "entry"), CASES, ids=IDS)
def test_shipped_plates_are_real_images_not_lfs_pointers(pack, name, entry) -> None:
    """Fail legibly when LFS has not materialized.

    Every assertion below reads image bytes, so without LFS they fail as
    ``UnidentifiedImageError`` or a hash mismatch, neither of which names the
    real problem. See each pack's ``AGENTS.md`` for why these are binary.
    """

    shipped = pack / "images" / entry["file"]
    assert shipped.is_file(), f"{pack.parent.name} declares a missing file"
    head = shipped.read_bytes()[: len(LFS_POINTER_MAGIC)]
    assert head != LFS_POINTER_MAGIC, (
        f"{pack.parent.name}:{name} is an unmaterialized Git LFS pointer. "
        "Run `git lfs pull`, or check out with LFS enabled."
    )


@pytest.mark.parametrize(("pack", "name", "entry"), CASES, ids=IDS)
def test_the_manifest_matches_the_shipped_bytes(pack, name, entry) -> None:
    """Conforming an image after writing its manifest is how the two drift."""

    shipped = pack / "images" / entry["file"]
    image = Image.open(shipped)

    assert list(image.size) == entry["size"]
    assert image.mode == entry["mode"]
    assert hashlib.sha256(shipped.read_bytes()).hexdigest() == entry["sha256"]


@pytest.mark.parametrize(("pack", "name", "entry"), CASES, ids=IDS)
def test_plates_are_conformed_to_the_client_surface(pack, name, entry) -> None:
    """A plate that is not the logical surface is a plate someone will rescale."""

    assert tuple(entry["size"]) == LOGICAL_SIZE
    assert entry["conformed_from"]["size"] != list(LOGICAL_SIZE)
    assert entry["conformed_from"]["transform"]


@pytest.mark.parametrize("pack", PACKS, ids=lambda p: p.parent.name)
def test_every_named_asset_is_referenced_by_the_world(pack) -> None:
    """An unused plate is an asset with no consumer, which does not ship."""

    manifest = json.loads((pack / "manifest.json").read_text())
    script = (pack.parent / "script.yaml").read_text()
    unused = [
        entry["file"]
        for entry in manifest["assets"].values()
        if entry["file"] not in script
    ]
    assert not unused, f"{pack.parent.name} ships plates nothing references: {unused}"


@pytest.mark.parametrize("pack", PACKS, ids=lambda p: p.parent.name)
def test_generation_is_reconstructible_without_the_endpoint(pack) -> None:
    """Provenance is an archived record: reproducible in kind, not resumable.

    The worker hostname is LAN infrastructure and is redacted deliberately.
    """

    jobs = json.loads((pack / "provenance" / "jobs.json").read_text())
    assert jobs["endpoint"] == "configured-worker"
    assert jobs["models"]["unet"] and jobs["params"]["steps"]
    manifest = json.loads((pack / "manifest.json").read_text())
    assert set(jobs["jobs"]) == set(manifest["assets"])
    for name, job in jobs["jobs"].items():
        assert job["prompt"].strip(), f"{name} records no prompt"
        assert job["reference_sha256"], f"{name} records no reference hash"
