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


class TestWireContractForClients:
    """What a non-pygame client actually receives for staged media.

    The web reference client derives landscape treatment from
    ``staging_hints.media_shape``, not from the role name, so separating shape
    from role only helps if the hint survives serialization.
    """

    @staticmethod
    def _first_media_fragment() -> dict:
        from tangl.persistence import PersistenceManagerFactory
        from tangl.service.service_manager import ServiceManager

        manager = ServiceManager(PersistenceManagerFactory.native_in_mem())
        user_id = manager.create_user().details["user_id"]
        envelope = manager.create_story(user_id=user_id, world_id="repartee_loop")
        for fragment in envelope.fragments:
            payload = (
                fragment if isinstance(fragment, dict) else fragment.model_dump(mode="json")
            )
            if payload.get("fragment_type") == "media":
                return payload
        raise AssertionError("no media fragment in the opening envelope")

    def test_role_carries_intent_without_encoding_shape(self) -> None:
        payload = self._first_media_fragment()

        assert payload["media_role"] == "narrative_im"
        assert "landscape" not in payload["media_role"]

    def test_staging_hints_survive_serialization(self) -> None:
        """Hints reach the client on the wire, not only on the in-process fragment."""

        payload = self._first_media_fragment()

        assert payload["staging_hints"]["media_shape"] == "landscape"

    def test_the_web_client_landscape_rule_would_match(self) -> None:
        """Mirrors apps/web `hasLandscapeShape`, which reads the hint not the role."""

        payload = self._first_media_fragment()
        shape = (payload.get("staging_hints") or {}).get("media_shape")

        assert shape in {"landscape", "banner", "cover", "bg"}
