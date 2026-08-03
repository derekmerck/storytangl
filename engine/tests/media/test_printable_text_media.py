"""Generic printable text through the deterministic SVG media lifecycle."""

from __future__ import annotations

from pathlib import Path

from lxml import etree
import pytest

from tangl.core import Graph
from tangl.media import MediaDataType, PrintableTextSpec
from tangl.media.media_creators.svg_text_forge import SvgTextSpec
from tangl.media.media_resource import MediaDep, MediaResourceInventoryTag as MediaRIT
from tangl.story.fabula import World


def _story_media_root(tmp_path: Path):
    root = tmp_path / "story_media"

    def _resolve(story_id=None):
        return root if story_id is None else root / str(story_id)

    return _resolve


def _story(*requests: PrintableTextSpec) -> dict[str, object]:
    return {
        "label": "printable_text_world",
        "scenes": {
            "intro": {
                "blocks": {
                    "start": {
                        "content": "Generated text",
                        "media": [
                            {
                                "spec": {
                                    "kind": "printable_text",
                                    **request.normalized_spec_payload(),
                                },
                                "media_role": "narrative_im",
                            }
                            for request in requests
                        ],
                    }
                }
            }
        },
    }


def test_printable_text_adapts_to_concrete_svg_layout() -> None:
    request = PrintableTextSpec(lines=("NAME: Ada", "CLASS: visitor"))

    adapted = request.adapt_spec(ctx={})

    assert isinstance(adapted, SvgTextSpec)
    assert adapted.lines == request.lines
    assert adapted.canvas_width == 320
    assert adapted.canvas_height == 80
    assert adapted.font_family == "sans-serif"
    assert adapted.line_height == 24
    assert adapted.adapter_version == "1"


def test_svg_text_uses_literal_xml_safe_ordered_lines() -> None:
    request = PrintableTextSpec(lines=(" first ", "<&> \"quoted\""))

    svg, realized = request.create_media(ctx={})
    root = etree.fromstring(svg.encode("utf-8"))
    lines = root.xpath("./svg:text", namespaces={"svg": "http://www.w3.org/2000/svg"})

    assert [line.text for line in lines] == [" first ", "<&> \"quoted\""]
    assert all(
        line.get("{http://www.w3.org/XML/1998/namespace}space") == "preserve"
        for line in lines
    )
    assert realized.renderer_name == "svg-text-forge"
    assert "&lt;&amp;&gt;" in svg


def test_printable_text_identity_includes_order_and_resolved_layout() -> None:
    request = PrintableTextSpec(lines=("one", "two"))
    equivalent = PrintableTextSpec(lines=("one", "two"))
    changed_text = PrintableTextSpec(lines=("one", "three"))
    changed_order = PrintableTextSpec(lines=("two", "one"))
    adapted = request.adapt_spec(ctx={})
    assert isinstance(adapted, SvgTextSpec)

    assert adapted.spec_fingerprint() == equivalent.adapt_spec(ctx={}).spec_fingerprint()
    assert adapted.spec_fingerprint() != changed_text.adapt_spec(ctx={}).spec_fingerprint()
    assert adapted.spec_fingerprint() != changed_order.adapt_spec(ctx={}).spec_fingerprint()
    assert adapted.spec_fingerprint() != adapted.model_copy(
        update={"font_size": adapted.font_size + 1}
    ).spec_fingerprint()


def test_printable_text_provisions_and_reuses_story_svg(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        "tangl.media.story_media.get_story_media_dir",
        _story_media_root(tmp_path),
    )
    request = PrintableTextSpec(label="badge_text", lines=("ADA VENN", "VISITOR"))
    world = World.from_script_data(script_data=_story(request, request.model_copy(deep=True)))
    story = world.create_story("printable-text-story").graph
    block = next(node for node in story.values() if getattr(node, "label", None) == "start")
    deps = [edge for edge in block.edges_out() if isinstance(edge, MediaDep)]

    assert len(deps) == 2
    assert deps[0].provider is not None
    assert deps[0].provider.uid == deps[1].provider.uid
    provider = deps[0].provider
    assert isinstance(provider, MediaRIT)
    assert provider.status.value == "resolved"
    assert provider.data_type is MediaDataType.VECTOR
    assert provider.path is not None
    assert etree.fromstring(provider.path.read_bytes()).tag.endswith("svg")
    assert provider.derivation_spec == request.normalized_spec_payload()
    assert provider.adapted_spec is not None
    assert provider.adapted_spec["canvas_width"] == 320
    assert provider.execution_spec is not None
    assert provider.execution_spec["renderer_name"] == "svg-text-forge"


def test_graph_constructor_round_trip_restores_typed_printable_text_spec() -> None:
    graph = Graph(label="printable-text")
    request = PrintableTextSpec(lines=("Ada",))
    dep = MediaDep(registry=graph, media_spec=request)
    graph.add(dep)

    restored = Graph.structure(graph.unstructure())
    restored_dep = next(value for value in restored.values() if isinstance(value, MediaDep))

    assert isinstance(restored_dep.requirement.media_spec, PrintableTextSpec)
    assert restored_dep.requirement.media_spec.lines == ("Ada",)
