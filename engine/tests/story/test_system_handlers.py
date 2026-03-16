"""Story journal handler contract tests."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from tangl.core import BehaviorRegistry, DispatchLayer, Graph, TemplateRegistry
from tangl.core.runtime_op import Predicate
from tangl.discourse.dialog import DialogMuBlock
from tangl.journal.discourse import AttributedFragment
from tangl.journal.media import MediaFragment as JournalMediaFragment
from tangl.lang.body_parts import BodyPart, BodyRegion
from tangl.mechanics.presence.look import BodyPhenotype, EyeColor, HairColor, HairStyle, Look, SkinTone
from tangl.mechanics.presence.look.look import HasLook
from tangl.mechanics.presence.ornaments import Ornament, OrnamentType
from tangl.mechanics.presence.wearable import Wearable, WearableLayer, WearableType
from tangl.media.media_resource import MediaDep, MediaResourceInventoryTag as MediaRIT
from tangl.story import Actor, Role, Scene, StoryGraph
from tangl.story.episode import Action, Block
from tangl.story.fragments import ChoiceFragment, ContentFragment, MediaFragment
from tangl.story.system_handlers import (
    render_block,
    render_block_choices,
    render_block_content,
    render_block_media,
)
from tangl.vm.dispatch import do_journal
from tangl.vm import Dependency, Requirement
from tangl.vm.runtime.frame import PhaseCtx


@pytest.fixture(autouse=True)
def reset_wearable_types():
    WearableType.clear_instances()
    yield
    WearableType.clear_instances()


def _ctx_with_ns(ns: dict[str, object] | None = None) -> SimpleNamespace:
    return SimpleNamespace(get_ns=lambda _caller: dict(ns or {}))


class DemoGuide(Actor, HasLook):
    """Story actor with visual presence used by JOURNAL handler tests."""

    def goes_by(self, alias: str) -> bool:
        alias = alias.strip().casefold()
        return alias in {
            self.name.casefold(),
            self.get_label().casefold(),
            "guide",
        }

    def get_dialog_style(self, dialog_class: str | None = None) -> dict[str, str]:
        if dialog_class and dialog_class.lower().endswith(".annoyed"):
            return {"font-weight": "700", "letter-spacing": "0.02em"}
        return {"font-weight": "600"}


def _build_outfit(actor: HasLook) -> None:
    shirt_type = WearableType(
        label="journal_shirt",
        noun="shirt",
        covers={BodyRegion.TOP},
        layer=WearableLayer.OUTER,
    )
    coat_type = WearableType(
        label="journal_coat",
        noun="coat",
        covers={BodyRegion.TOP},
        layer=WearableLayer.OVER,
    )

    actor.outfit.assign("top_60", Wearable(label=shirt_type.label))
    actor.outfit.assign("top_80", Wearable(label=coat_type.label))


def _build_ornaments(actor: HasLook) -> None:
    actor.ornamentation.add_ornament(
        Ornament(
            body_part=BodyPart.LEFT_ARM,
            ornament_type=OrnamentType.TATTOO,
            text="a dragon",
        )
    )


def _presence_story(
    *,
    content: str = "",
    media: list[dict[str, object]] | None = None,
    with_outfit: bool = True,
    with_ornaments: bool = True,
) -> tuple[StoryGraph, Block, DemoGuide]:
    graph = StoryGraph(label="presence_story")
    scene = Scene(label="scene")
    block = Block(label="start", content=content, media=media or [])
    guide = DemoGuide(
        label="guide_actor",
        name="Guide",
        look=Look(
            hair_color=HairColor.AUBURN,
            hair_style=HairStyle.BRAID,
            eye_color=EyeColor.GRAY,
            skin_tone=SkinTone.OLIVE,
            body_phenotype=BodyPhenotype.FIT,
        ),
    )
    role = Role(
        label="guide",
        predecessor_id=scene.uid,
        requirement=Requirement(has_kind=Actor, hard_requirement=False),
    )

    graph.add(scene)
    graph.add(block)
    graph.add(guide)
    graph.add(role)
    scene.add_child(block)
    role.set_provider(guide)

    if with_outfit:
        _build_outfit(guide)
    if with_ornaments:
        _build_ornaments(guide)

    return graph, block, guide


def test_render_block_emits_content_media_and_choice_fragments() -> None:
    graph = Graph()
    start = Block(label="start", content="Hello {name}", media=[{"kind": "image", "src": "a.svg"}])
    end = Block(label="end", content="bye")
    graph.add(start)
    graph.add(end)
    graph.add(Action(predecessor_id=start.uid, successor_id=end.uid, text="Continue"))

    fragments = render_block(caller=start, ctx=_ctx_with_ns({"name": "Joe"}))
    assert fragments is not None
    assert isinstance(fragments[0], ContentFragment)
    assert fragments[0].content == "Hello Joe"
    assert any(isinstance(fragment, MediaFragment) for fragment in fragments)

    choices = [fragment for fragment in fragments if isinstance(fragment, ChoiceFragment)]
    assert len(choices) == 1
    assert choices[0].available is True
    assert choices[0].unavailable_reason is None


def test_render_block_choice_unavailable_reason_missing_successor() -> None:
    graph = Graph()
    start = Block(label="start")
    graph.add(start)
    graph.add(Action(predecessor_id=start.uid, text="Broken"))

    fragments = render_block(caller=start, ctx=_ctx_with_ns())
    assert fragments is not None
    choice = next(fragment for fragment in fragments if isinstance(fragment, ChoiceFragment))
    assert choice.available is False
    assert choice.unavailable_reason == "missing_successor"
    assert choice.blockers == [{"type": "edge", "reason": "missing_successor"}]


def test_render_block_choice_missing_successor_uses_preview_blockers_when_dependency_exists() -> None:
    graph = StoryGraph()
    start = Block(label="start")
    graph.add(start)
    action = Action(predecessor_id=start.uid, text="Broken")
    graph.add(action)
    requirement = Requirement(has_identifier="missing", hard_requirement=True)
    graph.add(Dependency(predecessor_id=action.uid, label="destination", requirement=requirement))
    # No templates available for resolution.
    graph.factory = TemplateRegistry(label="empty")

    ctx = PhaseCtx(graph=graph, cursor_id=start.uid)
    fragments = render_block(caller=start, ctx=ctx)
    assert fragments is not None
    choice = next(fragment for fragment in fragments if isinstance(fragment, ChoiceFragment))
    assert choice.available is False
    assert choice.unavailable_reason == "missing_successor"
    assert choice.blockers is not None
    assert choice.blockers[0]["type"] == "provision"


def test_render_block_choice_unavailable_reason_missing_dependency() -> None:
    graph = Graph()
    start = Block(label="start")
    locked = Block(label="locked", availability=[Predicate(expr="False")])
    graph.add(start)
    graph.add(locked)
    graph.add(Action(predecessor_id=start.uid, successor_id=locked.uid, text="Try door"))
    requirement = Requirement(has_label="key")
    requirement.resolution_reason = "no_offers"
    requirement.resolution_meta = {"alternatives": []}
    graph.add(Dependency(predecessor_id=locked.uid, requirement=requirement))

    fragments = render_block(caller=start, ctx=_ctx_with_ns())
    assert fragments is not None
    choice = next(fragment for fragment in fragments if isinstance(fragment, ChoiceFragment))
    assert choice.available is False
    assert choice.unavailable_reason == "missing_dependency"
    assert choice.blockers is not None
    assert choice.blockers[0]["type"] == "dependency"
    assert choice.blockers[0]["resolution_reason"] == "no_offers"
    assert choice.blockers[0]["resolution_meta"] == {"alternatives": []}


def test_render_block_choice_hard_dependency_blocks_even_when_guard_is_true() -> None:
    graph = Graph()
    start = Block(label="start")
    reachable = Block(label="reachable")
    graph.add(start)
    graph.add(reachable)
    graph.add(Action(predecessor_id=start.uid, successor_id=reachable.uid, text="Open"))
    requirement = Requirement(has_label="key", hard_requirement=True)
    requirement.resolution_reason = "no_offers"
    graph.add(Dependency(predecessor_id=reachable.uid, requirement=requirement))

    fragments = render_block(caller=start, ctx=_ctx_with_ns())
    assert fragments is not None
    choice = next(fragment for fragment in fragments if isinstance(fragment, ChoiceFragment))
    assert choice.available is False
    assert choice.unavailable_reason == "missing_dependency"


def test_render_block_choice_unavailable_reason_guard_failed() -> None:
    graph = Graph()
    start = Block(label="start")
    locked = Block(label="locked", availability=[Predicate(expr="False")])
    graph.add(start)
    graph.add(locked)
    graph.add(Action(predecessor_id=start.uid, successor_id=locked.uid, text="Try door"))

    fragments = render_block(caller=start, ctx=_ctx_with_ns())
    assert fragments is not None
    choice = next(fragment for fragment in fragments if isinstance(fragment, ChoiceFragment))
    assert choice.available is False
    assert choice.unavailable_reason == "guard_failed_or_unavailable"


def test_render_block_emits_choice_payload_accepts_and_ui_hints() -> None:
    graph = Graph()
    start = Block(label="start")
    end = Block(label="end")
    graph.add(start)
    graph.add(end)
    graph.add(
        Action(
            predecessor_id=start.uid,
            successor_id=end.uid,
            text="Pick a color",
            accepts={"type": "string", "enum": ["red", "blue", "green"]},
            ui_hints={"widget": "select", "framework": "vuetify"},
        )
    )

    fragments = render_block(caller=start, ctx=_ctx_with_ns())
    assert fragments is not None
    choice = next(fragment for fragment in fragments if isinstance(fragment, ChoiceFragment))
    assert choice.accepts == {"type": "string", "enum": ["red", "blue", "green"]}
    assert choice.ui_hints == {"widget": "select", "framework": "vuetify"}


def test_render_block_compatibility_facade_merges_split_handlers() -> None:
    graph = Graph()
    start = Block(label="start", content="Hello {name}", media=[{"kind": "image", "src": "a.svg"}])
    end = Block(label="end")
    graph.add(start)
    graph.add(end)
    graph.add(Action(predecessor_id=start.uid, successor_id=end.uid, text="Continue"))

    ctx = _ctx_with_ns({"name": "Joe"})
    content = render_block_content(caller=start, ctx=ctx)
    media = render_block_media(caller=start, ctx=ctx)
    choices = render_block_choices(caller=start, ctx=ctx)

    fragments = render_block(caller=start, ctx=ctx)
    assert fragments is not None
    expected_len = (
        (1 if content is not None else 0)
        + (len(media) if media else 0)
        + (len(choices) if choices else 0)
    )
    assert len(fragments) == expected_len
    assert isinstance(fragments[0], ContentFragment)
    assert fragments[0].content == "Hello Joe"
    assert any(isinstance(fragment, MediaFragment) for fragment in fragments)
    assert any(isinstance(fragment, ChoiceFragment) for fragment in fragments)


def test_dispatch_journal_allows_custom_handler_injection() -> None:
    graph = StoryGraph()
    start = Block(label="start", content="Hello {name}", media=[{"kind": "image", "src": "a.svg"}])
    end = Block(label="end")
    graph.add(start)
    graph.add(end)
    graph.add(Action(predecessor_id=start.uid, successor_id=end.uid, text="Continue"))

    custom_registry = BehaviorRegistry(
        label="custom.story.journal",
        default_dispatch_layer=DispatchLayer.AUTHOR,
    )

    def _custom_overlay(*, caller, ctx, **_kw):
        if isinstance(caller, Block):
            return ContentFragment(content="overlay", source_id=caller.uid)
        return None
    custom_registry.register(_custom_overlay, task="render_journal", priority=0)

    graph.world = SimpleNamespace(get_authorities=lambda: [custom_registry])
    ctx = PhaseCtx(graph=graph, cursor_id=start.uid)
    ctx._ns_cache[start.uid] = {"name": "Joe"}  # bypass gather_ns wiring for focused journal test

    fragments = do_journal(start, ctx=ctx)
    assert isinstance(fragments, list)

    contents = [fragment.content for fragment in fragments if isinstance(fragment, ContentFragment)]
    assert "overlay" in contents
    assert "Hello Joe" in contents


def test_dispatch_journal_allows_compose_handler_injection() -> None:
    graph = StoryGraph()
    start = Block(label="start", content="Hello {name}", media=[{"kind": "image", "src": "a.svg"}])
    end = Block(label="end")
    graph.add(start)
    graph.add(end)
    graph.add(Action(predecessor_id=start.uid, successor_id=end.uid, text="Continue"))

    custom_registry = BehaviorRegistry(
        label="custom.story.compose",
        default_dispatch_layer=DispatchLayer.AUTHOR,
    )
    seen: dict[str, list[str]] = {}

    def _compose(*, caller, ctx, fragments, **_kw):
        if isinstance(caller, Block):
            seen["types"] = [type(fragment).__name__ for fragment in fragments]
            return [ContentFragment(content="summary", source_id=caller.uid), *fragments]
        return None

    custom_registry.register(_compose, task="compose_journal", priority=0)

    graph.world = SimpleNamespace(get_authorities=lambda: [custom_registry])
    ctx = PhaseCtx(graph=graph, cursor_id=start.uid)
    ctx._ns_cache[start.uid] = {"name": "Joe"}  # focused test bypass

    fragments = do_journal(start, ctx=ctx)
    assert isinstance(fragments, list)

    assert seen["types"] == ["ContentFragment", "MediaFragment", "ChoiceFragment"]
    assert isinstance(fragments[0], ContentFragment)
    assert fragments[0].content == "summary"
    assert any(
        isinstance(fragment, ContentFragment) and fragment.content == "Hello Joe"
        for fragment in fragments
    )


def test_dispatch_journal_composes_explicit_dialog_markup_into_attributed_fragments() -> None:
    graph, block, _guide = _presence_story(
        content=(
            "> [!spoken] {guide_name}\n"
            "> Welcome to the room.\n\n"
            "A hush fell over the room."
        ),
    )
    ctx = PhaseCtx(graph=graph, cursor_id=block.uid)

    fragments = do_journal(block, ctx=ctx)
    assert isinstance(fragments, list)

    assert all(isinstance(fragment, AttributedFragment) for fragment in fragments)
    assert fragments[0].who == "Guide"
    assert fragments[0].how == "spoken"
    assert fragments[0].content == "Welcome to the room."
    assert fragments[1].who == "narrator"
    assert fragments[1].how == "narration"
    assert fragments[1].content == "A hush fell over the room."


def test_dispatch_journal_dialog_composition_preserves_media_and_choice_order() -> None:
    graph, block, _guide = _presence_story(
        content="> [!spoken] {guide_name}\n> Welcome.",
        media=[{"kind": "image", "src": "a.svg"}],
    )
    end = Block(label="end")
    graph.add(end)
    graph.add(Action(predecessor_id=block.uid, successor_id=end.uid, text="Continue"))
    ctx = PhaseCtx(graph=graph, cursor_id=block.uid)

    fragments = do_journal(block, ctx=ctx)
    assert isinstance(fragments, list)

    types = [type(fragment).__name__ for fragment in fragments]
    assert types == ["AttributedFragment", "MediaFragment", "ChoiceFragment"]


def test_dispatch_journal_dialog_composition_enriches_speaker_formatting() -> None:
    graph, block, _guide = _presence_story(
        content="> [!NPC.annoyed] guide\n> Welcome.",
    )
    ctx = PhaseCtx(graph=graph, cursor_id=block.uid)

    fragments = do_journal(block, ctx=ctx)
    fragment = fragments[0] if isinstance(fragments, list) else fragments
    assert isinstance(fragment, AttributedFragment)
    assert fragment.who == "Guide"
    assert fragment.how == "NPC.annoyed"
    assert fragment.dialog_mode == "NPC"
    assert fragment.speaker_attitude == "annoyed"
    assert fragment.speaker_key == "guide"
    assert fragment.speaker_label == "guide_actor"
    assert fragment.presentation_hints.style_name == "npc"
    assert "speaker_key:guide" in fragment.presentation_hints.style_tags
    assert "attitude:annoyed" in fragment.presentation_hints.style_tags
    assert fragment.presentation_hints.style_dict == {
        "font-weight": "700",
        "letter-spacing": "0.02em",
    }
    assert fragment.media == "dialog_im"
    assert fragment.media_payload["media_role"] == "dialog_im"
    assert fragment.media_payload["attitude"] == "annoyed"


def test_dialog_mu_block_rebinding_resets_stale_speaker_state_and_sanitizes_tags() -> None:
    _graph, _block, guide = _presence_story()
    mu_block = DialogMuBlock(
        text="Welcome.",
        label="Guide Actor",
        dialog_class="NPC.annoyed",
    )

    mu_block.bind(ns={"Guide Actor": guide}, ctx=None)

    assert "dialog_class:npc_annoyed" in mu_block.presentation_hints.style_tags
    assert "speaker_key:guide_actor" in mu_block.presentation_hints.style_tags
    assert mu_block.speaker_id == str(guide.uid)
    assert mu_block.media_payload is not None

    mu_block.label = "Unknown Person"
    mu_block.bind(ns={}, ctx=None)
    fragment = mu_block.to_fragment()

    assert mu_block.speaker_id is None
    assert mu_block.speaker_key is None
    assert mu_block.speaker_label is None
    assert mu_block.media_payload is None
    assert "speaker:unknown_person" in mu_block.presentation_hints.style_tags
    assert "speaker:unknown_person" in fragment.tags


def test_render_block_facade_uses_compose_journal_with_phase_ctx() -> None:
    graph, block, _guide = _presence_story(
        content="> [!spoken] {guide_name}\n> Welcome.",
    )
    ctx = PhaseCtx(graph=graph, cursor_id=block.uid)

    fragments = render_block(caller=block, ctx=ctx)
    assert fragments is not None
    assert isinstance(fragments[0], AttributedFragment)
    assert fragments[0].who == "Guide"
    assert fragments[0].how == "spoken"


def test_render_block_content_includes_graph_locals_from_gather_ns() -> None:
    graph = StoryGraph(locals={"gold": 10})
    graph.world = SimpleNamespace(locals={"gold": 3})
    start = Block(label="start", content="Gold: {gold}")
    graph.add(start)
    graph.initial_cursor_id = start.uid
    ctx = PhaseCtx(graph=graph, cursor_id=start.uid)

    fragments = do_journal(start, ctx=ctx)
    if isinstance(fragments, ContentFragment):
        content = fragments
    else:
        assert isinstance(fragments, list)
        content = next(fragment for fragment in fragments if isinstance(fragment, ContentFragment))
    assert content.content == "Gold: 10"


def test_render_block_content_uses_role_prefixed_presence_symbols() -> None:
    graph, block, _guide = _presence_story(
        content=(
            "Look: {guide_look_description} | "
            "Outfit: {guide_outfit_description} | "
            "Marks: {guide_ornament_description}"
        ),
    )
    ctx = PhaseCtx(graph=graph, cursor_id=block.uid)

    fragments = do_journal(block, ctx=ctx)
    if isinstance(fragments, ContentFragment):
        content = fragments
    else:
        assert isinstance(fragments, list)
        content = next(fragment for fragment in fragments if isinstance(fragment, ContentFragment))
    assert "olive skin" in content.content
    assert "shirt and coat" in content.content
    assert "a dragon tattoo on their left arm" in content.content


def test_render_block_media_emits_canonical_formats(tmp_path) -> None:
    graph = StoryGraph()
    block = Block(
        label="start",
        media=[
            {"url": "https://example.com/poster.svg", "source_kind": "url"},
            {"data": "<svg xmlns='http://www.w3.org/2000/svg'></svg>", "source_kind": "data"},
            {"name": "cover.svg", "source_kind": "inventory"},
        ],
    )
    graph.add(block)

    asset = tmp_path / "cover.svg"
    asset.write_text("<svg xmlns='http://www.w3.org/2000/svg'></svg>", encoding="utf-8")
    rit = MediaRIT(path=asset, label="cover.svg", tags={"scope:world"})
    graph.add(rit)
    dep = MediaDep(registry=graph, predecessor_id=block.uid, media_id="cover.svg", scope="world")
    dep.set_provider(rit)
    block.media[2]["dependency_id"] = dep.uid

    fragments = render_block_media(caller=block, ctx=_ctx_with_ns())

    assert fragments is not None
    assert isinstance(fragments[0], JournalMediaFragment)
    assert fragments[0].fragment_type == "media"
    assert fragments[0].content_format == "url"
    assert isinstance(fragments[1], JournalMediaFragment)
    assert fragments[1].fragment_type == "media"
    assert fragments[1].content_format == "data"
    assert isinstance(fragments[2], JournalMediaFragment)
    assert fragments[2].fragment_type == "media"
    assert fragments[2].content_format == "rit"
    assert fragments[2].content == rit


def test_render_block_media_supports_facet_source_kind() -> None:
    graph, block, _guide = _presence_story(
        media=[
            {"source_kind": "facet", "subject": "guide", "facet": "look", "media_role": "avatar_im"},
            {"source_kind": "facet", "subject": "guide", "facet": "outfit", "media_role": "paperdoll_im"},
            {
                "source_kind": "facet",
                "subject": "guide",
                "facet": "ornamentation",
                "media_role": "detail_im",
            },
        ],
    )
    ctx = PhaseCtx(graph=graph, cursor_id=block.uid)

    fragments = render_block_media(caller=block, ctx=ctx)

    assert fragments is not None
    assert len(fragments) == 3
    assert all(isinstance(fragment, JournalMediaFragment) for fragment in fragments)
    assert fragments[0].media_role == "avatar_im"
    assert fragments[0].content["traits"]["hair_color"] == "auburn"
    assert fragments[0].content["outfit_tokens"] == ["shirt", "coat"]
    assert fragments[1].media_role == "paperdoll_im"
    assert fragments[1].content["items"] == ["shirt", "coat"]
    assert fragments[2].media_role == "detail_im"
    assert fragments[2].content["items"] == ["a dragon tattoo on their left arm"]


def test_render_block_media_facet_missing_subject_uses_fallback_text() -> None:
    graph = StoryGraph()
    block = Block(
        label="start",
        media=[
            {
                "source_kind": "facet",
                "subject": "missing",
                "facet": "look",
                "fallback_text": "No portrait available.",
            }
        ],
    )
    graph.add(block)

    fragments = render_block_media(caller=block, ctx=_ctx_with_ns())

    assert fragments is not None
    assert len(fragments) == 1
    assert isinstance(fragments[0], ContentFragment)
    assert fragments[0].content == "No portrait available."


def test_render_block_media_facet_unsupported_facet_emits_placeholder() -> None:
    graph, block, _guide = _presence_story(
        media=[{"source_kind": "facet", "subject": "guide", "facet": "voice"}],
    )
    ctx = PhaseCtx(graph=graph, cursor_id=block.uid)

    fragments = render_block_media(caller=block, ctx=ctx)

    assert fragments is not None
    assert len(fragments) == 1
    assert isinstance(fragments[0], JournalMediaFragment)
    assert fragments[0].content["source_kind"] == "facet"
    assert fragments[0].content["unresolved_reason"] == "unsupported_facet"
    assert fragments[0].content["facet"] == "voice"


def test_render_block_media_facet_empty_payload_emits_placeholder() -> None:
    graph, block, _guide = _presence_story(
        media=[{"source_kind": "facet", "subject": "guide", "facet": "outfit"}],
        with_outfit=False,
        with_ornaments=False,
    )
    ctx = PhaseCtx(graph=graph, cursor_id=block.uid)

    fragments = render_block_media(caller=block, ctx=ctx)

    assert fragments is not None
    assert len(fragments) == 1
    assert isinstance(fragments[0], JournalMediaFragment)
    assert fragments[0].content["source_kind"] == "facet"
    assert fragments[0].content["unresolved_reason"] == "empty_facet_payload"


def test_render_block_media_facet_metadata_only_payload_uses_fallback_text() -> None:
    graph = StoryGraph()
    block = Block(
        label="start",
        media=[
            {
                "source_kind": "facet",
                "subject": "guide",
                "facet": "look",
                "fallback_text": "No portrait available.",
            }
        ],
    )
    graph.add(block)

    subject = SimpleNamespace(adapt_look_media_spec=lambda **_kw: {"media_role": "avatar_im"})
    fragments = render_block_media(caller=block, ctx=_ctx_with_ns({"guide": subject}))

    assert fragments is not None
    assert len(fragments) == 1
    assert isinstance(fragments[0], ContentFragment)
    assert fragments[0].content == "No portrait available."


def test_render_block_media_emits_placeholder_for_unresolved_inventory_without_fallback() -> None:
    graph = StoryGraph()
    block = Block(
        label="start",
        media=[{"name": "missing.svg", "source_kind": "inventory", "media_role": "narrative_im"}],
    )
    graph.add(block)

    dep = MediaDep(registry=graph, predecessor_id=block.uid, media_id="missing.svg", scope="world")
    dep.requirement.resolution_reason = "no_offers"
    dep.requirement.resolution_meta = {"alternatives": []}
    block.media[0]["dependency_id"] = dep.uid

    fragments = render_block_media(caller=block, ctx=_ctx_with_ns())

    assert fragments is not None
    assert len(fragments) == 1
    assert isinstance(fragments[0], JournalMediaFragment)
    assert fragments[0].fragment_type == "media"
    assert fragments[0].content_format == "json"
    assert fragments[0].scope == "world"
    assert fragments[0].content["name"] == "missing.svg"
    assert fragments[0].content["source_kind"] == "inventory"
    assert fragments[0].content["unresolved_reason"] == "no_offers"
    assert fragments[0].content["resolution_meta"] == {"alternatives": []}
