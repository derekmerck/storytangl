"""Explicit region exports reference registered beauty and survive JSON restore."""
from io import BytesIO
import os
from pathlib import Path

from PIL import Image
import pytest

from tangl.core import Selector
from tangl.media.media_creators.svg_forge import render_playwright
from tangl.persistence import PersistenceManagerFactory
from tangl.service import ServiceManager, world_registry
from tangl.service.response import DirectEdgeRequest
from tangl.story import Action


@pytest.mark.parametrize("real", [False, pytest.param(True, marks=pytest.mark.skipif(
    os.environ.get("STORYTANGL_TEST_SVG_BROWSER") != "1", reason="optional Chromium export"))])
def test_explicit_export_and_json_restore(tmp_path: Path, monkeypatch, real: bool) -> None:
    monkeypatch.setattr(world_registry, "get_world_dirs", lambda: [Path(__file__).resolve().parents[3] / "worlds"])
    monkeypatch.setattr("tangl.media.story_media.get_story_media_dir",
                        lambda story_id=None: tmp_path / "media" / str(story_id))
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[3] / "worlds/modiste_demo"))
    from modiste_demo import domain
    generated = []
    if real:
        original_render = render_playwright.render_svg
        def count_render(source, dims, **kwargs):
            generated.append(source)
            return original_render(source, dims, **kwargs)
        monkeypatch.setattr(render_playwright, "render_svg", count_render)
    if not real:
        monkeypatch.setattr(domain, "renderer_identity", lambda: "chromium:mock;playwright:mock")
        monkeypatch.setattr(render_playwright, "renderer_identity", lambda: "chromium:mock;playwright:mock")
        def fake_render(source, dims, **kwargs):
            generated.append(source)
            out = BytesIO()
            Image.new("RGBA", dims, "white").save(out, format="PNG")
            return out.getvalue()
        monkeypatch.setattr(render_playwright, "render_svg", fake_render)
    def factory():
        return PersistenceManagerFactory.json_file(base_path=tmp_path / "store")
    service = ServiceManager(factory())
    user = service.create_user(secret="regions").details["user_id"]
    service.create_story(user_id=user, world_id="modiste_demo")

    def choose(manager, label):
        with manager.open_session(user_id=user) as session:
            action = next(e for e in session.ledger.cursor.edges_out(Selector(has_kind=Action)) if e.label == label)
            request = DirectEdgeRequest(edge_id=action.uid, payload=action.payload)
        return manager.resolve_choice(user_id=user, request=request)

    def masks_on_grid(graph, record):
        result = {}
        with Image.open(graph.get(record.beauty_id).path) as image:
            assert image.size == record.dimensions
        for name, uid in record.masks.items():
            with Image.open(graph.get(uid).path) as image:
                assert image.size == record.dimensions
                result[name] = image.convert("RGBA").tobytes()
        return result

    choose(service, "camisole")
    with service.open_session(user_id=user) as session:
        source = session.ledger.graph.get(session.ledger.cursor.media[0]["dependency_id"]).provider
        beauty = session.ledger.graph.get(session.ledger.cursor.media[1]["dependency_id"]).provider
        original_source, original_beauty = source.path.read_bytes(), beauty.path.read_bytes()
    choose(service, "export_regions")
    with service.open_session(user_id=user) as session:
        record = session.ledger.cursor.exports[-1]
        assert record.depth == "absent" and record.dimensions == (496, 665)
        assert record.coverage == {"lower_body": "visible", "torso": "visible"}
        first = masks_on_grid(session.ledger.graph, record)
        first_ids = dict(record.masks)
        assert session.ledger.graph.get(record.beauty_id).path.is_file()
        assert session.ledger.graph.get(record.source_id).path.read_bytes() == original_source
        assert session.ledger.graph.get(record.beauty_id).path.read_bytes() == original_beauty
    generated_before_reuse = len(generated)
    choose(service, "export_regions")
    with service.open_session(user_id=user) as session:
        assert session.ledger.cursor.exports[-1].masks == first_ids
    assert len(generated) == generated_before_reuse
    choose(service, "blue")
    choose(service, "export_regions")
    generated_before_read = len(generated)
    reopened = ServiceManager(factory())
    with reopened.open_session(user_id=user) as session:
        record = session.ledger.cursor.exports[-1]
        assert record.depth == "absent" and record.coverage == {"lower_body": "visible", "torso": "visible"}
        second = masks_on_grid(session.ledger.graph, record)
        before = session.ledger.graph.value_hash(), len(session.ledger.graph.members)
    assert first == second
    reopened.get_story_update(user_id=user)
    assert len(generated) == generated_before_read
    with reopened.open_session(user_id=user) as session:
        assert (session.ledger.graph.value_hash(), len(session.ledger.graph.members)) == before
    def unavailable():
        raise render_playwright.RendererUnavailable("unavailable")
    monkeypatch.setattr(domain, "renderer_identity", unavailable)
    choose(reopened, "export_regions")
    with reopened.open_session(user_id=user) as session:
        assert len(session.ledger.cursor.exports) == 3
        assert "unavailable" in session.ledger.cursor.render_error
    if not real:
        monkeypatch.setattr(domain, "renderer_identity", lambda: "chromium:new;playwright:mock")
        monkeypatch.setattr(render_playwright, "renderer_identity", lambda: "chromium:new;playwright:mock")
        original_render = render_playwright.render_svg
        def fail(*args, **kwargs):
            raise render_playwright.RendererUnavailable("failed")
        monkeypatch.setattr(render_playwright, "render_svg", fail)
        choose(reopened, "export_regions")
        monkeypatch.setattr(domain, "renderer_identity", lambda: "chromium:mock;playwright:mock")
        monkeypatch.setattr(render_playwright, "renderer_identity", lambda: "chromium:mock;playwright:mock")
        monkeypatch.setattr(render_playwright, "render_svg", original_render)
        count = len(generated)
        choose(reopened, "blue")
        assert len(generated) == count


@pytest.mark.parametrize("regions", [{}, {"ghost": ("body.not_present",)}])
def test_export_reports_missing_coverage_metadata(tmp_path: Path, monkeypatch, regions: dict) -> None:
    monkeypatch.setattr(world_registry, "get_world_dirs", lambda: [Path(__file__).resolve().parents[3] / "worlds"])
    monkeypatch.setattr("tangl.media.story_media.get_story_media_dir",
                        lambda story_id=None: tmp_path / "media" / str(story_id))
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[3] / "worlds/modiste_demo"))
    from modiste_demo import domain
    original = domain.load_pack
    monkeypatch.setattr(domain, "renderer_identity", lambda: "chromium:mock;playwright:mock")
    monkeypatch.setattr(render_playwright, "renderer_identity", lambda: "chromium:mock;playwright:mock")
    def fake_render(source, dims, **kwargs):
        out = BytesIO()
        Image.new("RGBA", dims, "white").save(out, format="PNG")
        return out.getvalue()
    monkeypatch.setattr(render_playwright, "render_svg", fake_render)
    def without_regions(manager):
        pack, catalog = original(manager)
        return pack.model_copy(update={"regions": regions}), catalog
    monkeypatch.setattr(domain, "load_pack", without_regions)
    service = ServiceManager(PersistenceManagerFactory.json_file(base_path=tmp_path / "store"))
    user = service.create_user(secret="missing-regions").details["user_id"]
    service.create_story(user_id=user, world_id="modiste_demo")
    with service.open_session(user_id=user) as session:
        action = next(e for e in session.ledger.cursor.edges_out(Selector(has_kind=Action))
                      if e.label == "export_regions")
        request = DirectEdgeRequest(edge_id=action.uid, payload=action.payload)
    service.resolve_choice(user_id=user, request=request)
    with service.open_session(user_id=user) as session:
        if not regions:
            assert not session.ledger.cursor.exports
            assert session.ledger.cursor.render_error == "Missing region coverage metadata"
        else:
            record = session.ledger.cursor.exports[-1]
            assert record.coverage == {"ghost": "unrepresented"} and record.masks == {}
