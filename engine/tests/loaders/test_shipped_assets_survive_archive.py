"""A required asset must survive `git archive`, not merely exist in the tree.

Three world packs override the repository-wide LFS rule so their plates are
ordinary git blobs, on the grounds that the pack suites decode those bytes and
therefore cannot depend on LFS having materialized. That reasoning is sound and
the overrides were still wrong: each one carried `export-ignore` along with the
LFS attributes it meant to unset, so the one set of PNGs that *could* survive an
archive was the set excluded from it. An exact `git archive` of the merged head
contained the manifests and empty image directories and none of the fourteen
plates.

Nothing caught it because every existing assertion reads the working tree, where
the files are present and correct. This reads what actually ships.

The trap worth naming: git attributes are inherited unless a nearer file
*mentions* them, so deleting the word `export-ignore` from an override leaves
the root rule in force and looks like a fix. It has to be unset explicitly, and
that is what this test pins.
"""

from __future__ import annotations

import json
import subprocess
import tarfile
from io import BytesIO
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
WORLDS = REPO / "worlds"


def _declared_assets() -> list[tuple[str, str]]:
    """Every file a world media manifest claims to ship, as repo-relative paths."""

    declared: list[tuple[str, str]] = []
    for manifest_path in sorted(WORLDS.glob("*/media*/manifest.json")):
        manifest = json.loads(manifest_path.read_text())
        pack = manifest_path.parent
        for name, entry in manifest["assets"].items():
            path = (pack / "images" / entry["file"]).relative_to(REPO)
            declared.append((f"{pack.parent.name}:{name}", str(path)))
    return declared


DECLARED = _declared_assets()


@pytest.fixture(scope="module")
def archived_paths() -> set[str]:
    """Paths present in `git archive HEAD -- worlds`.

    The real artifact rather than the attribute that produces it: `git
    check-attr` would confirm the configuration while an archive could still
    come out empty for some other reason.
    """

    try:
        blob = subprocess.run(
            ["git", "archive", "HEAD", "--", "worlds"],
            cwd=REPO,
            capture_output=True,
            check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        pytest.skip(f"not an archivable git checkout: {exc}")

    with tarfile.open(fileobj=BytesIO(blob)) as tar:
        return {member.name for member in tar.getmembers() if member.isfile()}


def test_some_assets_are_declared() -> None:
    """Guard against the suite passing because it found nothing to check."""

    assert len(DECLARED) >= 14


@pytest.mark.parametrize(
    "path", [path for _id, path in DECLARED], ids=[id_ for id_, _path in DECLARED]
)
def test_a_declared_asset_is_present_in_an_archive(path: str, archived_paths) -> None:
    assert path in archived_paths, (
        f"{path} is declared in a media manifest but excluded from `git archive`. "
        "Check that its world .gitattributes unsets `-export-ignore` explicitly: "
        "omitting the attribute inherits the root rule instead of clearing it."
    )
