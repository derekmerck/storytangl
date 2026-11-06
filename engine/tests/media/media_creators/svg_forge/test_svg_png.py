"""PNG derivative values and opt-in browser fidelity."""
from hashlib import sha256
from io import BytesIO
import asyncio
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from uuid import uuid4

from PIL import Image
import pytest

from tangl.core import Graph
from tangl.media.media_creators.composition_forge.composition_inputs import CompositionInputUnavailable, resolve_composition_inputs
from tangl.media.media_creators.composition_forge.composition_spec import CompositionInputRef, CompositionSpec
from tangl.media.media_creators.svg_forge.svg_png_spec import SvgPngSpec, create_svg_png
from tangl.media.media_resource import MediaResourceInventoryTag as MediaRIT
from tangl.media.media_data_type import MediaDataType
from tangl.media.media_creators.svg_forge.render_playwright import RendererUnavailable, render_svg, renderer_identity
from tangl.media.media_creators.svg_forge import render_playwright
from tangl.media.media_creators.svg_forge.vector_forge import VectorForge


SVG = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">
<rect x="2" y="2" width="6" height="6" fill="#4080c0"/>
<rect x="2" y="2" width="6" height="6" fill="#c08040" style="mix-blend-mode:hard-light"/>
</svg>'''


def spec() -> SvgPngSpec:
    return SvgPngSpec(source_id=uuid4(), source_hash=b"hash", source_sha256=sha256(SVG.encode()).hexdigest(),
                      width=20, height=10, renderer_version="chromium:test")


def test_request_roundtrip_validation_and_identity() -> None:
    original = spec()
    restored = SvgPngSpec.structure(original.unstructure())
    assert restored.source_id == original.source_id
    assert restored.spec_fingerprint() == original.spec_fingerprint()
    assert original.model_copy(update={"source_id": uuid4()}).spec_fingerprint() == original.spec_fingerprint()
    for field, value in (("width", 30), ("source_hash", b"other"),
                         ("renderer_version", "other"), ("background", "white")):
        assert original.model_copy(update={field: value}).spec_fingerprint() != original.spec_fingerprint()
    with pytest.raises(ValueError):
        SvgPngSpec(source_id=uuid4(), source_hash=b"x", source_sha256="x", width=0, height=1)


def test_missing_or_changed_source_cannot_render() -> None:
    graph = Graph()
    source = MediaRIT(data=SVG, data_type=MediaDataType.VECTOR)
    graph.add(source)
    reference = CompositionInputRef(role="source", rit_id=source.uid, content_hash=b"wrong")
    with pytest.raises(CompositionInputUnavailable):
        resolve_composition_inputs(CompositionSpec(inputs=[reference]), graph=graph)
    with pytest.raises(ValueError, match="source content changed"):
        create_svg_png(spec(), {"vector_source": SVG + " "})
    with pytest.raises(ValueError, match="resolved SVG source"):
        create_svg_png(spec())
    invalid = SVG.replace('viewBox="0 0 10 10"', 'viewBox="0 0 0 10"')
    bad_spec = spec().model_copy(update={"source_sha256": sha256(invalid.encode()).hexdigest()})
    with pytest.raises(ValueError, match="valid viewBox"):
        create_svg_png(bad_spec, {"vector_source": invalid})


def test_missing_optional_renderer_is_reported(monkeypatch) -> None:
    monkeypatch.setattr(render_playwright, "find_spec", lambda _: None)
    with pytest.raises(RendererUnavailable, match="svg-png extra"):
        renderer_identity()


def test_sync_file_helpers_return_and_write_png(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(render_playwright, "render_svg", lambda *args, **kwargs: b"png")
    source = tmp_path / "source.svg"
    source.write_text(SVG)
    out = tmp_path / "result.png"
    assert render_playwright.render_svg_file(source, out, (20, 10)) == b"png"
    assert out.read_bytes() == b"png"
    assert VectorForge.to_png(svg_fp=source, output_fp=out, dims=(20, 10), as_bytes=True) == b"png"
    assert out.read_bytes() == b"png"


@pytest.mark.skipif(os.environ.get("STORYTANGL_TEST_SVG_BROWSER") != "1",
                    reason="optional Chromium fidelity test")
def test_real_chromium_transparency_aspect_and_hard_light() -> None:
    try:
        identity = renderer_identity()
    except RendererUnavailable as exc:
        pytest.skip(str(exc))
    image = Image.open(BytesIO(render_svg(SVG, (20, 10), identity=identity))).convert("RGBA")
    assert image.size == (20, 10) and image.getpixel((0, 0))[3] == 0
    assert image.getpixel((5, 5))[3] == 0
    pixel = image.getpixel((10, 5))
    assert all(abs(actual - expected) <= 3 for actual, expected in zip(pixel, (160, 128, 96, 255)))
    white = Image.open(BytesIO(render_svg(SVG, (20, 10), background="white", identity=identity))).convert("RGBA")
    assert white.getpixel((0, 0)) == (255, 255, 255, 255)


@pytest.mark.skipif(os.environ.get("STORYTANGL_TEST_SVG_BROWSER") != "1",
                    reason="optional Chromium fidelity test")
def test_real_chromium_inside_event_loop_preserves_gradient_clip_and_opacity() -> None:
    try:
        renderer_identity()
    except RendererUnavailable as exc:
        pytest.skip(str(exc))
    source = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">
      <defs><linearGradient id="g"><stop stop-color="red"/><stop offset="1" stop-color="blue"/></linearGradient>
      <clipPath id="c"><rect x="2" y="2" width="6" height="6"/></clipPath></defs>
      <g opacity="0.5" clip-path="url(#c)"><rect width="10" height="10" fill="url(#g)"/></g>
    </svg>'''
    async def render_in_loop():
        return render_svg(source, (20, 20), identity=renderer_identity())
    image = Image.open(BytesIO(asyncio.run(render_in_loop()))).convert("RGBA")
    assert image.getpixel((0, 0))[3] == 0 and image.getpixel((10, 10))[3] == 128
    left, right = image.getpixel((5, 10)), image.getpixel((14, 10))
    assert left[0] > left[2] and right[2] > right[0]


@pytest.mark.skipif(os.environ.get("STORYTANGL_TEST_SVG_BROWSER") != "1",
                    reason="optional Chromium fidelity test")
def test_real_chromium_nested_svg_and_external_content_are_isolated() -> None:
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            requests.append(self.path)
            self.send_response(204)
            self.end_headers()

        def log_message(self, format, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    url = f"http://127.0.0.1:{server.server_port}"
    source = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20">
      <script>fetch('{url}/script')</script>
      <image href="{url}/image" x="0" y="0" width="20" height="20"/>
      <svg x="5" y="5" width="5" height="5" viewBox="0 0 5 5">
        <rect width="5" height="5" fill="red"/></svg>
    </svg>'''
    try:
        image = Image.open(BytesIO(render_svg(source, (20, 20)))).convert("RGBA")
        assert image.getpixel((7, 7)) == (255, 0, 0, 255)
        assert image.getpixel((15, 15))[3] == 0
        assert requests == []
    finally:
        server.shutdown()
        server.server_close()
        worker.join()
