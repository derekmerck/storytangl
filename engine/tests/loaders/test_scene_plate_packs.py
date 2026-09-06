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
import yaml
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

    with Image.open(shipped) as image:
        # `open` reads the header and defers the pixels, so a truncated plate
        # reports its declared size and mode quite happily. The manifest hash
        # cannot catch that either -- it is generated from the shipped file, so
        # a corrupt commit is recorded faithfully. Decoding is the only
        # assertion here that proves the bytes are an image.
        image.load()

        assert list(image.size) == entry["size"]
        assert image.mode == entry["mode"]
    assert hashlib.sha256(shipped.read_bytes()).hexdigest() == entry["sha256"]


@pytest.mark.parametrize(("pack", "name", "entry"), CASES, ids=IDS)
def test_plates_are_conformed_to_the_client_surface(pack, name, entry) -> None:
    """A plate that is not the logical surface is a plate someone will rescale."""

    assert tuple(entry["size"]) == LOGICAL_SIZE
    assert entry["conformed_from"]["size"] != list(LOGICAL_SIZE)
    assert entry["conformed_from"]["transform"]


def _staged_media_names(node) -> set[str]:
    """Every ``name`` under a block's ``media:`` list, anywhere in the script.

    Walks the parsed document rather than the raw text. A substring search over
    the file counts a filename in a comment, in narration, or in a commented-out
    block as a reference -- which is precisely the case this test exists to
    catch, since a plate nothing stages is a plate that should not ship.
    """

    found: set[str] = set()
    if isinstance(node, dict):
        media = node.get("media")
        if isinstance(media, list):
            found |= {
                item["name"]
                for item in media
                if isinstance(item, dict) and isinstance(item.get("name"), str)
            }
        for value in node.values():
            found |= _staged_media_names(value)
    elif isinstance(node, list):
        for value in node:
            found |= _staged_media_names(value)
    return found


@pytest.mark.parametrize("pack", PACKS, ids=lambda p: p.parent.name)
def test_every_named_asset_is_referenced_by_the_world(pack) -> None:
    """An unused plate is an asset with no consumer, which does not ship."""

    manifest = json.loads((pack / "manifest.json").read_text())
    script = yaml.safe_load((pack.parent / "script.yaml").read_text())
    staged = _staged_media_names(script)
    unused = [
        entry["file"]
        for entry in manifest["assets"].values()
        if entry["file"] not in staged
    ]

    assert staged, f"{pack.parent.name} stages no media at all"
    assert not unused, f"{pack.parent.name} ships plates nothing stages: {unused}"


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
