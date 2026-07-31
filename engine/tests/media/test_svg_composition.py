"""One-level SVG composition through ordinary media provisioning."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from lxml import etree
import pytest

from tangl.core import Graph, Priority
from tangl.media import MediaDataType
from tangl.media.media_creators.composition_forge.composition_inputs import (
    COMPOSITION_INPUTS_CONTEXT_KEY,
    CompositionInputUnavailable,
    ResolvedCompositionInput,
    resolve_composition_inputs,
)
from tangl.media.media_creators.composition_forge.composition_forge import CompositionForge
from tangl.media.media_creators.composition_forge.composition_spec import (
    CompositionInputRef,
    CompositionSpec,
)
from tangl.media.media_creators.media_spec import on_create_media
from tangl.media.media_resource import MediaDep, MediaResourceInventoryTag as MediaRIT
from tangl.media.media_resource.media_provisioning import MediaSpecProvisioner
from tangl.media.media_resource.media_resource_inv_tag import MediaRITStatus
from tangl.story.fabula import World
from tangl.utils.hashing import compute_data_hash


_RECT_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg">'
    '<rect width="40" height="40" fill="navy"/>'
    "</svg>"
)
_CIRCLE_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg">'
    '<circle cx="30" cy="30" r="20" fill="gold"/>'
    "</svg>"
)
_VIEWPORT_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 10 10">'
    '<defs><linearGradient id="paint"><stop offset="0" stop-color="navy"/></linearGradient></defs>'
    '<rect width="10" height="10" fill="url(#paint)"/>'
    "</svg>"
)
_SECOND_VIEWPORT_SVG = _VIEWPORT_SVG.replace("navy", "gold")
_REFERENCE_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" id="portrait">'
    '<defs><linearGradient id="paint"/></defs><path id="face"/>'
    '<use href="#face"/><use href="other.svg#face"/>'
    '<rect fill="url(#paint)" stroke="#face"/>'
    '<text>literal #face</text>'
    "</svg>"
)


def _story_media_root(tmp_path: Path):
    root = tmp_path / "story_media"

    def _resolve(story_id=None):
        return root if story_id is None else root / str(story_id)

    return _resolve


def _story(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setattr(
        "tangl.media.story_media.get_story_media_dir",
        _story_media_root(tmp_path),
    )
    world = World.from_script_data(
        script_data={
            "label": "composition_world",
            "scenes": {"intro": {"blocks": {"start": {"content": "Compose"}}}},
        }
    )
    story = world.create_story("composition-story").graph
    block = next(
        node for node in story.values() if getattr(node, "label", None) == "start"
    )
    return story, block


def _child(svg: str, *, label: str) -> MediaRIT:
    return MediaRIT(label=label, data=svg, data_type=MediaDataType.VECTOR)


def _spec(*children: MediaRIT) -> CompositionSpec:
    return CompositionSpec(
        label="identity_card",
        inputs=[
            CompositionInputRef(
                role=role,
                rit_id=child.uid,
                content_hash=child.get_content_hash(),
                offset=offset,
            )
            for role, child, offset in (
                ("background", children[0], (0, 0)),
                ("portrait", children[1], (16, 12)),
            )
        ],
        canvas_size=(128, 128),
        background="white",
    )


def _context(story, block):
    return SimpleNamespace(
        graph=story,
        cursor=block,
        cursor_id=block.uid,
        get_ns=lambda _parent: {},
    )


def _offers(story, block, spec: CompositionSpec):
    dep = MediaDep(registry=story, predecessor_id=block.uid, media_spec=spec)
    story.add(dep)
    return list(
        MediaSpecProvisioner(graph=story).get_dependency_offers(
            dep.requirement,
            _ctx=_context(story, block),
        )
    )


def test_graph_constructor_round_trip_preserves_composition_child_ids() -> None:
    first = _child(_RECT_SVG, label="rect")
    second = _child(_CIRCLE_SVG, label="circle")
    spec = _spec(first, second)
    graph = Graph(label="composition")
    graph.add(first)
    graph.add(second)
    dep = MediaDep(registry=graph, media_spec=spec)
    graph.add(dep)

    restored_graph = Graph.structure(graph.unstructure())
    restored_dep = next(
        value for value in restored_graph.values() if isinstance(value, MediaDep)
    )
    restored = restored_dep.requirement.media_spec

    assert isinstance(restored, CompositionSpec)
    assert [ref.rit_id for ref in restored.inputs] == [first.uid, second.uid]
    assert [ref.content_hash for ref in restored.inputs] == [
        first.get_content_hash(),
        second.get_content_hash(),
    ]
    assert not any(isinstance(value, MediaRIT) for value in restored.inputs)


def test_composition_identity_uses_child_content_not_rit_id() -> None:
    first = _child(_RECT_SVG, label="rect")
    second = _child(_CIRCLE_SVG, label="circle")
    equivalent_first = _child(_RECT_SVG, label="other-rect")
    equivalent_second = _child(_CIRCLE_SVG, label="other-circle")

    spec = _spec(first, second)
    equivalent = _spec(equivalent_first, equivalent_second)
    changed_bytes = equivalent.model_copy(
        update={
            "inputs": [
                equivalent.inputs[0].model_copy(update={"content_hash": b"different"}),
                equivalent.inputs[1],
            ]
        }
    )
    changed_layout = equivalent.model_copy(
        update={
            "inputs": [
                equivalent.inputs[0],
                equivalent.inputs[1].model_copy(update={"offset": (17, 12)}),
            ]
        }
    )

    assert spec.spec_fingerprint() == equivalent.spec_fingerprint()
    assert spec.spec_fingerprint() != changed_bytes.spec_fingerprint()
    assert spec.spec_fingerprint() != changed_layout.spec_fingerprint()
    assert spec.spec_fingerprint() != spec.model_copy(
        update={"treatment": "mask"}
    ).spec_fingerprint()
    assert spec.spec_fingerprint() != spec.model_copy(
        update={"compositor_version": "2"}
    ).spec_fingerprint()
    assert spec.spec_fingerprint() != spec.model_copy(
        update={"inputs": list(reversed(spec.inputs))}
    ).spec_fingerprint()


def test_resolver_uses_graph_owned_child_and_rejects_hash_mismatch() -> None:
    graph = Graph(label="composition")
    first = _child(_RECT_SVG, label="rect")
    second = _child(_CIRCLE_SVG, label="circle")
    graph.add(first)
    graph.add(second)
    spec = _spec(first, second)

    resolved = resolve_composition_inputs(spec, graph=graph)

    assert resolved[0].svg == _RECT_SVG
    first.data = _RECT_SVG.replace("navy", "green")
    with pytest.raises(CompositionInputUnavailable, match="content hash changed"):
        resolve_composition_inputs(spec, graph=graph)


def test_resolver_reports_an_unreadable_child_as_unavailable(tmp_path: Path) -> None:
    graph = Graph(label="composition")
    missing = MediaRIT(
        label="missing",
        path=tmp_path / "missing.svg",
        preset_content_hash=b"expected",
        data_type=MediaDataType.VECTOR,
    )
    second = _child(_CIRCLE_SVG, label="circle")
    graph.add(missing)
    graph.add(second)

    with pytest.raises(CompositionInputUnavailable, match="could not be read"):
        resolve_composition_inputs(_spec(missing, second), graph=graph)


def test_compositor_preserves_child_viewports_and_namespaces_ids(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    story, block = _story(monkeypatch, tmp_path)
    first = _child(_VIEWPORT_SVG, label="first")
    second = _child(_SECOND_VIEWPORT_SVG, label="second")
    story.add(first)
    story.add(second)

    parent = _offers(story, block, _spec(first, second))[0].callback(
        _ctx=_context(story, block)
    )
    assert parent.path is not None
    root = etree.fromstring(parent.path.read_bytes())
    nested_svgs = root.xpath("./svg:g/svg:svg", namespaces={"svg": "http://www.w3.org/2000/svg"})
    gradients = root.xpath(".//svg:linearGradient", namespaces={"svg": "http://www.w3.org/2000/svg"})

    assert [svg.get("viewBox") for svg in nested_svgs] == ["0 0 10 10", "0 0 10 10"]
    assert [gradient.get("id") for gradient in gradients] == ["input-0-paint", "input-1-paint"]
    assert b"url(#input-0-paint)" in parent.path.read_bytes()
    assert b"url(#input-1-paint)" in parent.path.read_bytes()


def test_compositor_namespaces_only_svg_reference_syntax() -> None:
    ref = CompositionInputRef(role="portrait", rit_id=uuid4(), content_hash=b"child")
    svg, _ = CompositionForge().create_media(
        CompositionSpec(inputs=[]),
        inputs=[ResolvedCompositionInput(ref=ref, svg=_REFERENCE_SVG)],
    )
    root = etree.fromstring(svg.encode("utf-8"))
    child = root.xpath("./svg:g/svg:svg", namespaces={"svg": "http://www.w3.org/2000/svg"})[0]
    values = {
        "root": child.get("id"),
        "href": child.xpath(".//svg:use", namespaces={"svg": "http://www.w3.org/2000/svg"})[0].get("href"),
        "external": child.xpath(".//svg:use", namespaces={"svg": "http://www.w3.org/2000/svg"})[1].get("href"),
        "fill": child.xpath(".//svg:rect", namespaces={"svg": "http://www.w3.org/2000/svg"})[0].get("fill"),
        "stroke": child.xpath(".//svg:rect", namespaces={"svg": "http://www.w3.org/2000/svg"})[0].get("stroke"),
        "text": child.xpath(".//svg:text", namespaces={"svg": "http://www.w3.org/2000/svg"})[0].text,
    }

    assert child.getparent().get("id") is None
    assert values == {
        "root": "input-0-portrait",
        "href": "#input-0-face",
        "external": "other.svg#face",
        "fill": "url(#input-0-paint)",
        "stroke": "#face",
        "text": "literal #face",
    }


def test_pending_child_suppresses_parent_create_until_resolved(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    story, block = _story(monkeypatch, tmp_path)
    rect = _child(_RECT_SVG, label="rect")
    circle_hash = compute_data_hash(_CIRCLE_SVG)
    circle = MediaRIT(
        label="circle",
        preset_content_hash=circle_hash,
        status=MediaRITStatus.PENDING,
        data_type=MediaDataType.VECTOR,
    )
    story.add(rect)
    story.add(circle)
    spec = _spec(rect, circle)

    assert _offers(story, block, spec) == []

    circle.status = MediaRITStatus.RESOLVED
    circle.data = _CIRCLE_SVG
    offers = _offers(story, block, spec)

    assert len(offers) == 1
    parent = offers[0].callback(_ctx=_context(story, block))
    assert parent.status is MediaRITStatus.RESOLVED
    assert parent.path is not None and etree.fromstring(parent.path.read_bytes()).tag.endswith("svg")


def test_composition_provisions_once_and_retains_full_provenance(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    story, block = _story(monkeypatch, tmp_path)
    first = _child(_RECT_SVG, label="rect")
    second = _child(_CIRCLE_SVG, label="circle")
    story.add(first)
    story.add(second)
    spec = _spec(first, second)

    offers = _offers(story, block, spec)
    parent = offers[0].callback(_ctx=_context(story, block))
    story.add(parent)
    reused = _offers(story, block, spec.model_copy(deep=True))

    assert parent.path is not None and etree.fromstring(parent.path.read_bytes()).tag.endswith("svg")
    assert parent.derivation_spec == spec.normalized_spec_payload()
    assert parent.adapted_spec == spec.normalized_spec_payload()
    assert parent.execution_spec is not None
    assert parent.execution_spec["renderer_name"] == "svg-compositor"
    assert parent.execution_spec["resolved_input_hashes"] == [
        first.get_content_hash(),
        second.get_content_hash(),
    ]
    assert len(reused) == 1
    assert reused[0].candidate is parent


def test_composition_creation_uses_the_canonical_creator_dispatch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    story, block = _story(monkeypatch, tmp_path)
    first = _child(_RECT_SVG, label="rect")
    second = _child(_CIRCLE_SVG, label="circle")
    story.add(first)
    story.add(second)
    dispatched: list[dict[str, object]] = []

    @on_create_media.register(priority=Priority.EARLY)
    def record_composition_dispatch(
        spec: CompositionSpec,
        ctx: dict[str, object] | None = None,
    ) -> None:
        dispatched.append({"spec": spec, "ctx": ctx})

    record_composition_dispatch._behavior.wants_caller_kind = CompositionSpec
    try:
        parent = _offers(story, block, _spec(first, second))[0].callback(
            _ctx=_context(story, block)
        )
    finally:
        on_create_media.remove(record_composition_dispatch._behavior.uid)

    assert parent.status is MediaRITStatus.RESOLVED
    assert dispatched[0]["spec"].__class__ is CompositionSpec
    assert len(dispatched[0]["ctx"][COMPOSITION_INPUTS_CONTEXT_KEY]) == 2
