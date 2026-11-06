"""An unavailable PNG creator must respect ordinary soft dependencies."""
from uuid import uuid4
from hashlib import sha256
from types import SimpleNamespace

import pytest

from tangl.media.media_creators.svg_forge import render_playwright
from tangl.media.media_resource import media_provisioning
from tangl.media.media_resource import MediaDep, MediaResourceInventoryTag as MediaRIT
from tangl.story.fabula import World
from tangl.story.fabula.types import GraphInitializationError
from tangl.vm import Resolver
from tangl.vm.runtime.frame import PhaseCtx
from tangl.media.media_data_type import MediaDataType


@pytest.mark.parametrize("failure", ["unavailable", "creation", "missing_source"])
@pytest.mark.parametrize("hard", [False, True])
def test_authored_png_failure_respects_requirement(monkeypatch, failure: str, hard: bool) -> None:
    source = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"/>'
    if failure == "unavailable":
        monkeypatch.setattr(render_playwright, "find_spec", lambda _: None)
    else:
        monkeypatch.setattr(render_playwright, "renderer_identity", lambda: "chromium:test")
    if failure == "creation":
        def fail(*args, **kwargs):
            raise render_playwright.RendererUnavailable("browser failed")
        monkeypatch.setattr(render_playwright, "render_svg", fail)
        monkeypatch.setattr(media_provisioning, "resolve_composition_inputs",
                            lambda *args, **kwargs: [SimpleNamespace(svg=source)])
    world = World.from_script_data(script_data={
        "label": "soft_png_review",
        "scenes": {"intro": {"blocks": {"start": {
            "content": "still playable",
            "media": [{"hard": hard, "spec": {"kind": "svg_png", "source_id": uuid4(),
                                "source_hash": b"hash", "source_sha256": sha256(source.encode()).hexdigest(),
                                "width": 10, "height": 10}}],
        }}}},
    })
    if hard:
        with pytest.raises(GraphInitializationError):
            world.create_story("soft_png_review_story")
        return
    result = world.create_story("soft_png_review_story")
    story = result.graph
    block = next(item for item in story.values() if getattr(item, "label", None) == "start")
    assert block.content == "still playable"
    dependency = next(edge for edge in block.edges_out() if isinstance(edge, MediaDep))
    assert dependency.provider is None and dependency.satisfied is not hard
    assert bool(result.report.unresolved_hard) is hard
    assert not any(isinstance(item, MediaRIT) and item.path and item.path.suffix == ".png"
                   for item in story.values())
    if failure == "unavailable":
        unrelated = MediaRIT(data='<svg xmlns="http://www.w3.org/2000/svg"/>',
                             data_type=MediaDataType.VECTOR)
        story.add(unrelated)
        ctx = PhaseCtx(graph=story, cursor_id=block.uid)
        assert not Resolver.from_ctx(ctx).resolve_dependency(dependency, _ctx=ctx)
        assert dependency.provider is None
