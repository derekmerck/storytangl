"""Selected SVG groups retain registration, ancestry, definitions, and palette targets."""
from uuid import uuid4
from hashlib import sha256

from lxml import etree
import pytest

from tangl.media.media_creators.svg_forge.vector_forge import VectorForge
from tangl.media.media_creators.svg_forge.vector_spec import VectorSpec


SOURCE = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">
<defs><linearGradient id="shade"><stop offset="0" stop-color="black"/></linearGradient></defs>
<g id="ancestor" transform="translate(2 3)" style="opacity:0.5">
  <g id="back"><path id="base" d="M0 0h3v3z" style="fill:red"/>
    <path id="fixed" d="M1 1h1v1z" style="fill:gold"/>
    <path id="shading" d="M0 0h1v1z" style="fill:url(#shade);mix-blend-mode:hard-light"/>
  </g>
  <g id="front" style="display:none;opacity:0.8"><path id="coat" d="M0 0h2v2z" style="fill:blue"/></g>
  <g id="unselected"><path id="unwanted" d="M0 0h1v1z"/></g>
</g></svg>'''


def request(color: str = "green") -> VectorSpec:
    return VectorSpec(source_id=uuid4(), source_hash=b"source", source_sha256=sha256(SOURCE.encode()).hexdigest(), plan_identity="plan",
                      registration=(0, 0, 10, 10), locators=("#back", "#front"),
                      bindings={"cloth": {"fill": color}},
                      targets=(("cloth", "fill", "base", ()),))


def test_figure_preserves_geometry_and_applies_only_explicit_target() -> None:
    spec = request()
    rendered, realized = VectorForge().create_media(spec, source=SOURCE)
    again, _ = VectorForge().create_media(spec, source=SOURCE)
    assert rendered == again and realized is spec
    root = etree.fromstring(rendered.encode())
    ns = {"s": "http://www.w3.org/2000/svg"}
    assert root.get("viewBox") == "0 0 10 10"
    assert [e.get("id") for e in root.xpath("//s:g[@id]", namespaces=ns)] == ["ancestor", "back", "front"]
    assert root.xpath("//*[@id='back']")[0].getparent() is root.xpath("//*[@id='front']")[0].getparent()
    assert root.xpath("//*[@id='back']")[0].getparent().get("transform") == "translate(2 3)"
    assert root.xpath("//*[@id='front']")[0].getparent().get("style") == "opacity:0.5"
    assert root.xpath("//*[@id='front']")[0].get("style") == "opacity:0.8;display:inline"
    assert root.xpath("//*[@id='base']")[0].get("style") == "fill:green"
    assert root.xpath("//*[@id='fixed']")[0].get("style") == "fill:gold"
    assert "hard-light" in root.xpath("//*[@id='shading']")[0].get("style")
    assert root.xpath("//*[@id='shade']") and not root.xpath("//*[@id='unwanted']")
    blue, _ = VectorForge().create_media(request("blue"), source=SOURCE)
    blue_root = etree.fromstring(blue.encode())
    assert blue_root.xpath("//*[@id='base']")[0].get("style") == "fill:blue"
    assert blue_root.xpath("//*[@id='fixed']")[0].get("style") == "fill:gold"
    assert root.xpath("//*[@id='base']")[0].get("d") == blue_root.xpath("//*[@id='base']")[0].get("d")
    assert 'fill:red' in SOURCE


def test_vector_spec_constructor_roundtrip_and_identity() -> None:
    spec = request()
    restored = VectorSpec.structure(spec.unstructure())
    assert restored.source_id == spec.source_id and restored.targets == spec.targets
    assert restored.spec_fingerprint() == spec.spec_fingerprint()
    assert spec.model_copy(update={"source_id": uuid4()}).spec_fingerprint() == spec.spec_fingerprint()
    assert spec.model_copy(update={"label": "different"}).spec_fingerprint() == spec.spec_fingerprint()
    assert request("blue").spec_fingerprint() != spec.spec_fingerprint()
    assert spec.model_copy(update={"source_hash": b"changed"}).spec_fingerprint() != spec.spec_fingerprint()
    assert spec.model_copy(update={"targets": ()}).spec_fingerprint() != spec.spec_fingerprint()
    assert spec.model_copy(update={"renderer_version": "1"}).spec_fingerprint() != spec.spec_fingerprint()


@pytest.mark.parametrize("changes", [
    {"locators": ("#absent",)},
    {"targets": (("cloth", "fill", "absent", ()),)},
    {"registration": (0, 0, 11, 10)},
])
def test_invalid_figure_fails_explicitly(changes: dict) -> None:
    with pytest.raises(ValueError):
        VectorForge().create_media(request().model_copy(update=changes), source=SOURCE)


def test_unresolved_reference_fails() -> None:
    source = SOURCE.replace("url(#shade)", "url(#missing)")
    spec = request().model_copy(update={"source_sha256": sha256(source.encode()).hexdigest()})
    with pytest.raises(ValueError, match="Unresolved"):
        VectorForge().create_media(spec, source=source)


def test_changed_source_is_rejected() -> None:
    with pytest.raises(ValueError, match="source content changed"):
        VectorForge().create_media(request(), source=SOURCE.replace("fill:red", "fill:green"))


def test_ancestor_id_styles_and_shared_compositing_are_preserved() -> None:
    source = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">
    <style>#ancestor {fill:red}</style><g id="ancestor" opacity="0.5">
      <g id="back"><rect width="10" height="10"/></g>
      <g id="unused"><rect id="unwanted"/></g>
      <g id="front"><rect width="10" height="10" fill="blue"/></g>
    </g></svg>'''
    spec = request().model_copy(update={"source_sha256": sha256(source.encode()).hexdigest(),
        "locators": ("#front", "#back"), "targets": ()})
    result, _ = VectorForge().create_media(spec, source=source)
    root = etree.fromstring(result.encode())
    ancestor = root.xpath("//*[@id='ancestor']")
    assert len(ancestor) == 1 and ancestor[0].get("opacity") == "0.5"
    assert [child.get("id") for child in ancestor[0]] == ["front", "back"]
    assert "#ancestor {fill:red}" in root.xpath("//*[local-name()='style']")[0].text
    assert not root.xpath("//*[@id='unwanted']")


def test_interleaving_shared_ancestor_fails_explicitly() -> None:
    source = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">
      <g id="a" opacity="0.5"><g id="a1"/><g id="a2"/></g>
      <g id="b"><g id="b1"/></g></svg>'''
    spec = request().model_copy(update={"source_sha256": sha256(source.encode()).hexdigest(),
        "locators": ("#a1", "#b1", "#a2"), "targets": ()})
    with pytest.raises(ValueError, match="split a shared SVG ancestor"):
        VectorForge().create_media(spec, source=source)
