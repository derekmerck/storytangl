"""Media tests for the logic demo gate badge spec."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from tangl.core import Selector
from tangl.journal.media import MediaFragment
from tangl.loaders import WorldBundle
from tangl.loaders.compiler import WorldCompiler
from tangl.media.media_resource import MediaDep, MediaResourceInventoryTag as MediaRIT
from tangl.service.media import media_fragment_to_payload
from tangl.story import Action, InitMode
from tangl.story.system_handlers import render_block_media
from tangl.vm import Ledger


def _logic_root() -> Path:
    return Path(__file__).resolve().parents[3] / "worlds" / "logic_demo"


def _story_media_root(tmp_path: Path):
    root = tmp_path / "story_media"

    def _resolve(story_id=None):
        if story_id is None:
            return root
        return root / str(story_id)

    return _resolve


def _choice_by_text(ledger: Ledger, text: str) -> Action:
    return next(
        action
        for action in ledger.cursor.edges_out(Selector(has_kind=Action, trigger_phase=None))
        if action.text == text
    )


def _make_story(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setattr(
        "tangl.media.story_media.get_story_media_dir",
        _story_media_root(tmp_path),
    )

    bundle = WorldBundle.load(_logic_root())
    world = WorldCompiler().compile(bundle)
    result = world.create_story("logic_demo_media", init_mode=InitMode.EAGER)
    story = result.graph
    ledger = Ledger.from_graph(story, entry_id=story.initial_cursor_id)
    return world, story, ledger


def test_gate_badge_spec_fingerprint_is_deterministic(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    world, _story, _ledger = _make_story(monkeypatch, tmp_path)
    gate_badge_cls = world.class_registry["GateBadgeSpec"]

    first = gate_badge_cls(label="logic_badge", gate_type="OUTPUT", badge_text="EVEN")
    second = gate_badge_cls(label="logic_badge", gate_type="OUTPUT", badge_text="EVEN")

    assert first.spec_fingerprint() == second.spec_fingerprint()


def test_logic_demo_output_badge_resolves_to_story_svg(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _world, story, ledger = _make_story(monkeypatch, tmp_path)

    ledger.resolve_choice(_choice_by_text(ledger, "Inspect the parity checker").uid)
    ledger.resolve_choice(_choice_by_text(ledger, "First bit = 1").uid)
    ledger.resolve_choice(_choice_by_text(ledger, "Second bit = 1").uid)

    deps = [edge for edge in ledger.cursor.edges_out() if isinstance(edge, MediaDep)]
    assert len(deps) == 1

    provider = deps[0].provider
    assert isinstance(provider, MediaRIT)
    assert provider.path is not None and provider.path.exists()
    assert provider.path.suffix == ".svg"
    assert provider.path.parent == story.story_resources.resource_path

    fragments = render_block_media(
        caller=ledger.cursor,
        ctx=SimpleNamespace(get_ns=lambda _caller: {}),
    )
    fragment = next(item for item in fragments if isinstance(item, MediaFragment))
    payload = media_fragment_to_payload(
        fragment,
        story_id=str(story.story_id),
        story_media_root=story.story_resources.resource_path,
    )

    assert payload is not None
    assert payload["scope"] == "story"
    assert payload["content_format"] == "rit"
    assert payload["url"].startswith(f"/media/story/{story.story_id}/parity_even_badge-")
    assert payload["url"].endswith(".svg")
