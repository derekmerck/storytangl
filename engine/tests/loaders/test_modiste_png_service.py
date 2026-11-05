"""PNG generation remains an UPDATE-time derivative across Service restore."""
from io import BytesIO
from base64 import b64decode
import asyncio
from pathlib import Path
import os

from PIL import Image
import pytest

from tangl.core import Selector
from tangl.journal.fragments import MediaFragment
from tangl.media.media_creators.svg_forge import render_playwright
from tangl.media.media_data_type import MediaDataType
from tangl.media.media_resource.resource_manager import ResourceManager
from tangl.persistence import PersistenceManagerFactory
from tangl.service import ServiceManager, world_registry
from tangl.service.response import DirectEdgeRequest
from tangl.service.media import MediaContentProfile, MediaRenderProfile, media_fragment_to_payload
from tangl.story import Action


@pytest.mark.parametrize("real", [False, pytest.param(True, marks=pytest.mark.skipif(
    os.environ.get("STORYTANGL_TEST_SVG_BROWSER") != "1", reason="optional Chromium journey"))])
def test_png_choices_reuse_and_failure_recover_after_json(tmp_path: Path, monkeypatch, real: bool) -> None:
    monkeypatch.setattr(world_registry, "get_world_dirs", lambda: [Path(__file__).resolve().parents[3] / "worlds"])
    monkeypatch.setattr("tangl.media.story_media.get_story_media_dir",
                        lambda story_id=None: tmp_path / "media" / str(story_id))
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[3] / "worlds/modiste_demo"))
    from modiste_demo import domain
    if real:
        try:
            render_playwright.renderer_identity()
        except render_playwright.RendererUnavailable as exc:
            pytest.skip(str(exc))
    if not real:
        monkeypatch.setattr(domain, "renderer_identity", lambda: "chromium:mock;playwright:mock")
        monkeypatch.setattr(render_playwright, "renderer_identity", lambda: "chromium:mock;playwright:mock")
    generated = []
    original_render = render_playwright.render_svg

    def render(source, dims, **kwargs):
        generated.append(source)
        if real:
            return original_render(source, dims, **kwargs)
        out = BytesIO()
        Image.new("RGBA", dims, "red").save(out, format="PNG")
        return out.getvalue()

    monkeypatch.setattr(render_playwright, "render_svg", render)
    def factory():
        return PersistenceManagerFactory.json_file(base_path=tmp_path / "store")
    service = ServiceManager(factory())
    user = service.create_user(secret="png").details["user_id"]
    service.create_story(user_id=user, world_id="modiste_demo")

    def choose(manager, label):
        with manager.open_session(user_id=user) as session:
            action = next(e for e in session.ledger.cursor.edges_out(Selector(has_kind=Action))
                          if e.label == label)
            request = DirectEdgeRequest(edge_id=action.uid, payload=action.payload)
        return manager.resolve_choice(user_id=user, request=request)

    def figure(response, kind):
        return next(f.content for f in response.fragments if isinstance(f, MediaFragment)
                    and f.content_format == "rit" and f.content.data_type == kind)

    rose = choose(service, "camisole")
    rose_png = figure(rose, MediaDataType.IMAGE)
    assert Image.open(rose_png.path).size == (496, 665)
    blue = choose(service, "blue")
    blue_png = figure(blue, MediaDataType.IMAGE)
    image_fragment = next(f for f in blue.fragments if isinstance(f, MediaFragment)
                          and f.content_format == "rit" and f.content.data_type == MediaDataType.IMAGE)
    payload = media_fragment_to_payload(image_fragment, render_profile=MediaRenderProfile(
        content_profile=MediaContentProfile.INLINE_DATA))
    assert b64decode(payload["data"]) == blue_png.path.read_bytes()
    svg = figure(blue, MediaDataType.VECTOR)
    assert blue_png.uid != rose_png.uid and len(generated) == 3
    assert blue_png.execution_spec["renderer_version"].startswith("chromium:")
    assert blue_png.execution_spec["source_id"] == svg.uid
    with service.open_session(user_id=user) as session:
        graph = session.ledger.graph
        raster = graph.get(session.ledger.cursor.media[1]["dependency_id"])
        assert raster.provider.uid == blue_png.uid
        assert raster.requirement.media_spec.source_id == svg.uid
        before = graph.value_hash(), len(graph.members)
    with monkeypatch.context() as reads:
        def no_admission(*args, **kwargs):
            raise AssertionError("read or restore attempted resource admission")
        reads.setattr(ResourceManager, "register_file", no_admission)
        reopened = ServiceManager(factory())
        reopened.get_story_update(user_id=user)
        with reopened.open_session(user_id=user) as session:
            assert (session.ledger.graph.value_hash(), len(session.ledger.graph.members)) == before
            assert session.ledger.graph.get(session.ledger.cursor.media[1]["dependency_id"]).provider.uid == blue_png.uid
    assert len(generated) == 3
    assert figure(choose(reopened, "rose"), MediaDataType.IMAGE).uid == rose_png.uid
    assert len(generated) == 3
    choose(reopened, "blue")

    def fail(*args, **kwargs):
        raise render_playwright.RendererUnavailable("test failure")
    monkeypatch.setattr(render_playwright, "render_svg", fail)
    failed = choose(reopened, "underwear")
    assert figure(failed, MediaDataType.VECTOR)
    assert not any(isinstance(f, MediaFragment) and f.content_format == "rit"
                   and f.content.data_type == MediaDataType.IMAGE for f in failed.fragments)
    monkeypatch.setattr(render_playwright, "render_svg", render)
    reopened = ServiceManager(factory())
    async def choose_in_loop():
        return choose(reopened, "underwear")
    recovered = asyncio.run(choose_in_loop())
    assert figure(recovered, MediaDataType.IMAGE).path.is_file()
    original_identity = domain.renderer_identity
    monkeypatch.setattr(domain, "renderer_identity", fail)
    unavailable = choose(reopened, "camisole")
    assert figure(unavailable, MediaDataType.VECTOR)
    assert not any(isinstance(f, MediaFragment) and f.content_format == "rit"
                   and f.content.data_type == MediaDataType.IMAGE for f in unavailable.fragments)
    monkeypatch.setattr(domain, "renderer_identity", original_identity)
    reopened = ServiceManager(factory())
    assert figure(choose(reopened, "camisole"), MediaDataType.IMAGE).uid == blue_png.uid
    if not real:
        monkeypatch.setattr(domain, "renderer_identity", lambda: "chromium:new;playwright:mock")
        monkeypatch.setattr(render_playwright, "renderer_identity", lambda: "chromium:new;playwright:mock")
        changed = figure(choose(reopened, "camisole"), MediaDataType.IMAGE)
        assert changed.uid != blue_png.uid and changed.execution_spec["renderer_version"] == "chromium:new;playwright:mock"
