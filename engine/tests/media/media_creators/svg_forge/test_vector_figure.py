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
    assert [e.get("id") for e in root.xpath("//s:g[@id]", namespaces=ns)] == ["back", "front"]
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
