"""Interactive catalogue choices survive JSON-backed Service reopen."""
from pathlib import Path
import re

from tangl.core import Selector
from tangl.journal.fragments import ContentFragment, MediaFragment
from tangl.persistence import PersistenceManagerFactory
from tangl.service import ServiceManager, world_registry
from tangl.service.response import DirectEdgeRequest
from tangl.service.media import MediaContentProfile, MediaRenderProfile, media_fragment_to_payload
from tangl.story import Action
from tangl.media.media_creators.svg_forge.vector_forge import VectorForge
from tangl.media.media_resource.resource_manager import ResourceManager


def test_modiste_choices_restore_and_continue(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(world_registry, "get_world_dirs", lambda: [Path(__file__).resolve().parents[3] / "worlds"])
    monkeypatch.setattr("tangl.media.story_media.get_story_media_dir",
                        lambda story_id=None: tmp_path / "media" / str(story_id))
    generated = []
    original_create = VectorForge.create_media

    def count_create(self, spec, *, source):
        generated.append(spec.spec_fingerprint())
        return original_create(self, spec, source=source)

    monkeypatch.setattr(VectorForge, "create_media", count_create)
    service = ServiceManager(PersistenceManagerFactory.json_file(base_path=tmp_path / "store"))
    user = service.create_user(secret="modiste").details["user_id"]
    service.create_story(user_id=user, world_id="modiste_demo")
    from modiste_demo import domain
    calls = []
    original_load = domain.load_pack

    def count_load(manager):
        calls.append(manager)
        return original_load(manager)

    monkeypatch.setattr(domain, "load_pack", count_load)

    def choose(manager: ServiceManager, label: str):
        with manager.open_session(user_id=user) as session:
            action = next(edge for edge in session.ledger.cursor.edges_out(Selector(has_kind=Action))
                          if edge.label == label)
            request = DirectEdgeRequest(edge_id=action.uid, payload=action.payload)
        return manager.resolve_choice(user_id=user, request=request)

    assert len(generated) == 1
    first = choose(service, "camisole")
    first_resource = next(f.content for f in first.fragments if isinstance(f, MediaFragment) and f.content_format == "rit")
    first_svg = first_resource.path.read_text()
    assert 'id="camisole_2_"' in first_svg and '#F1B3A4' in first_svg
    response = choose(service, "blue")
    fragment = next(f for f in response.fragments if isinstance(f, MediaFragment) and f.content_format == "rit")
    resource = fragment.content
    svg = resource.path.read_text()
    payload = media_fragment_to_payload(fragment, render_profile=MediaRenderProfile(
        content_profile=MediaContentProfile.INLINE_DATA,
    ))
    assert payload["content_format"] == "xml" and payload["data"] == svg
    assert 'id="camisole_2_"' in svg and '#a8cae0' in svg
    assert resource.uid != first_resource.uid and len(generated) == 3
    text = " ".join(f.content for f in response.fragments if isinstance(f, ContentFragment) and isinstance(f.content, str))
    assert "Outfit: camisole" in text and "Palette: blue" in text
    assert "top.camisole" in text and "feet.slippers" in text
    identity = re.search(r"Plan: ([a-f0-9]{64})", text).group(1)
    with service.open_session(user_id=user) as session:
        persisted = session.ledger.graph.value_hash(), len(session.ledger.graph.members)
    def no_admission(*args, **kwargs):
        raise AssertionError("read or reuse attempted resource admission")

    monkeypatch.setattr(ResourceManager, "register_file", no_admission)
    reopened = ServiceManager(PersistenceManagerFactory.json_file(base_path=tmp_path / "store"))
    with reopened.open_session(user_id=user) as session:
        assert session.ledger.cursor.outfit == "camisole" and session.ledger.cursor.palette == "blue"
        dep = session.ledger.graph.get(session.ledger.cursor.media[0]["dependency_id"])
        assert dep.provider.uid == resource.uid and dep.provider.path.read_text() == svg
        before = session.ledger.graph.value_hash(), len(session.ledger.graph.members)
        assert before == persisted
    update = reopened.get_story_update(user_id=user)
    text = " ".join(f.content for f in update.fragments if isinstance(f, ContentFragment) and isinstance(f.content, str))
    assert f"Plan: {identity}" in text
    with reopened.open_session(user_id=user) as session:
        assert (session.ledger.graph.value_hash(), len(session.ledger.graph.members)) == before
    response = choose(reopened, "blue")
    text = " ".join(f.content for f in response.fragments if isinstance(f, ContentFragment) and isinstance(f.content, str))
    assert f"Plan: {identity}" in text
    assert "Outfit: camisole" in text and "Palette: blue" in text
    assert calls == []
    assert len(generated) == 3
    again = choose(reopened, "rose")
    restored = next(f.content for f in again.fragments if isinstance(f, MediaFragment) and f.content_format == "rit")
    assert restored.uid == first_resource.uid and restored.path.read_text() == first_svg
    assert len(generated) == 3
    monkeypatch.setattr(domain, "palette_targets", lambda *_: (("skin", "fill", "absent", ()),))
    failed = choose(reopened, "blue")
    assert not any(isinstance(f, MediaFragment) and f.content_format == "rit" for f in failed.fragments)
    text = " ".join(f.content for f in failed.fragments if isinstance(f, ContentFragment)
                    and isinstance(f.content, str))
    assert "Missing or ambiguous palette target" in text
