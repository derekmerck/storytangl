"""Proof that semantic media requests may adapt into a backend spec class."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from lxml import etree

from tangl.core import Priority
from tangl.journal.media import MediaFragment
from tangl.media.media_creators.media_spec import (
    MediaResolutionClass,
    MediaSpec,
    on_adapt_media_spec,
)
from tangl.media.media_data_type import MediaDataType
from tangl.media.media_resource import MediaDep, MediaResourceInventoryTag as MediaRIT
from tangl.service.media import media_fragment_to_payload
from tangl.story.fabula import World
from tangl.story.system_handlers import render_block_media


class _ToySemanticSpec(MediaSpec):
    """Test-private request whose fields are not SVG instructions."""

    box_color: str
    circle_color: str
    order: tuple[str, str] = ("box", "circle")
    offset: int = 0
    seed: int | None = None


class _ToySvgSpec(MediaSpec):
    """Test-private backend request containing concrete SVG instructions."""

    resolution_class: MediaResolutionClass = MediaResolutionClass.FAST_SYNC
    data_type: MediaDataType = MediaDataType.VECTOR

    box_color: str
    circle_color: str
    element_order: tuple[str, str]
    circle_x: int
    circle_y: int
    seed: int
    rendered_element_count: int | None = None

    @classmethod
    def get_creation_service(cls) -> "_ToySvgCreator":
        return _ToySvgCreator()


@on_adapt_media_spec.register(priority=Priority.NORMAL)
def _adapt_toy_svg(spec: _ToySemanticSpec, ctx: dict[str, object] | None = None) -> _ToySvgSpec:
    """Compile a semantic box-and-circle request into SVG instructions."""
    spec.commit_deterministic_seed()
    return _ToySvgSpec(
        label=spec.label,
        box_color=spec.box_color,
        circle_color=spec.circle_color,
        element_order=spec.order,
        circle_x=32 + spec.offset,
        circle_y=32 + spec.offset,
        seed=spec.seed,
    )


_adapt_toy_svg._behavior.wants_caller_kind = _ToySemanticSpec


class _ToySvgCreator:
    """Test-private SVG backend that returns its concrete execution request."""

    def create_media(self, spec: _ToySvgSpec) -> tuple[str, _ToySvgSpec]:
        elements = {
            "box": f'<rect x="8" y="8" width="48" height="48" fill="{spec.box_color}"/>',
            "circle": (
                f'<circle cx="{spec.circle_x}" cy="{spec.circle_y}" r="18" '
                f'fill="{spec.circle_color}"/>'
            ),
        }
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64">'
            f"{''.join(elements[element] for element in spec.element_order)}"
            "</svg>"
        )
        return svg, spec.model_copy(update={"rendered_element_count": len(spec.element_order)})


def _story_media_root(tmp_path: Path):
    root = tmp_path / "story_media"

    def _resolve(story_id=None):
        if story_id is None:
            return root
        return root / str(story_id)

    return _resolve


def _toy_story(*, specs: list[_ToySemanticSpec]) -> dict[str, object]:
    media_specs: list[dict[str, object]] = []
    for spec in specs:
        payload = spec.normalized_spec_payload()
        payload["kind"] = f"{type(spec).__module__}.{type(spec).__name__}"
        media_specs.append({"spec": payload, "media_role": "narrative_im"})

    return {
        "label": "toy_svg_world",
        "scenes": {
            "intro": {
                "blocks": {
                    "start": {
                        "content": "Generated media",
                        "media": media_specs,
                    }
                }
            }
        },
    }


def _create_toy_story(
    *,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    specs: list[_ToySemanticSpec],
):
    monkeypatch.setattr(
        "tangl.media.story_media.get_story_media_dir",
        _story_media_root(tmp_path),
    )
    world = World.from_script_data(script_data=_toy_story(specs=specs))
    story = world.create_story("toy-svg-story").graph
    block = next(node for node in story.values() if getattr(node, "label", None) == "start")
    return story, block


def test_semantic_spec_adapts_to_backend_spec_with_stable_identity() -> None:
    first = _ToySemanticSpec(
        label="portrait",
        box_color="navy",
        circle_color="gold",
        offset=4,
    )
    second = first.model_copy(deep=True)
    changed_layout = first.model_copy(update={"offset": 5})

    adapted = first.adapt_spec(ctx={})

    assert isinstance(adapted, _ToySvgSpec)
    assert adapted.element_order == ("box", "circle")
    assert adapted.circle_x == adapted.circle_y == 36
    assert adapted.spec_fingerprint() == second.adapt_spec(ctx={}).spec_fingerprint()
    assert adapted.spec_fingerprint() != changed_layout.adapt_spec(ctx={}).spec_fingerprint()


def test_cross_class_adaptation_provisions_and_reuses_story_svg(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    request = _ToySemanticSpec(
        label="toy_portrait",
        box_color="navy",
        circle_color="gold",
        offset=4,
    )
    story, block = _create_toy_story(
        monkeypatch=monkeypatch,
        tmp_path=tmp_path,
        specs=[request, request.model_copy(deep=True)],
    )

    deps = [edge for edge in block.edges_out() if isinstance(edge, MediaDep)]
    assert len(deps) == 2
    assert deps[0].provider is not None
    assert deps[0].provider.uid == deps[1].provider.uid

    provider = deps[0].provider
    assert isinstance(provider, MediaRIT)
    assert provider.path is not None and provider.path.exists()
    assert provider.derivation_spec is not None
    assert provider.derivation_spec["offset"] == 4
    assert "circle_x" not in provider.derivation_spec
    assert provider.adapted_spec is not None
    assert provider.adapted_spec["circle_x"] == 36
    assert "offset" not in provider.adapted_spec
    assert provider.execution_spec is not None
    assert provider.execution_spec["rendered_element_count"] == 2
    adapted_request = request.adapt_spec(ctx={})
    assert isinstance(adapted_request, _ToySvgSpec)
    assert provider.adapted_spec_hash == _ToySvgSpec(
        label="toy_portrait",
        box_color="navy",
        circle_color="gold",
        element_order=("box", "circle"),
        circle_x=36,
        circle_y=36,
        seed=adapted_request.seed,
    ).spec_fingerprint()
    assert etree.fromstring(provider.path.read_bytes()).tag.endswith("svg")

    fragments = render_block_media(caller=block, ctx=SimpleNamespace(get_ns=lambda _caller: {}))
    fragment = next(item for item in fragments if isinstance(item, MediaFragment))
    payload = media_fragment_to_payload(
        fragment,
        world_id="toy_svg_world",
        story_id=str(story.story_id),
        story_media_root=story.story_resources.resource_path,
    )

    assert payload is not None
    assert payload["content_format"] == "rit"
    assert payload["scope"] == "story"
    assert payload["url"].endswith(".svg")
