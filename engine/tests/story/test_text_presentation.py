"""Focused tests for typed story text presentation."""

from __future__ import annotations

from types import SimpleNamespace

import jinja2
import pytest

from tangl.core import BehaviorRegistry, DispatchLayer
from tangl.lang.body_parts import BodyPart, BodyRegion
from tangl.mechanics.presence.look import (
    HairColor,
    HairStyle,
    HasLook,
    HasSimpleLook,
    Look,
    SkinTone,
)
from tangl.mechanics.presence.ornaments import Ornament, OrnamentType
from tangl.mechanics.presence.wearable import Wearable, WearableLayer, WearableType
from tangl.prose import TextRenderSession
from tangl.story import Actor
from tangl.story.dispatch import do_render_text
from tangl.story.presentation import render_text_as


class _TextCtx:
    cursor = SimpleNamespace(label="text-render")

    def __init__(
        self,
        namespace: dict[str, object] | None = None,
        authorities: list[BehaviorRegistry] | None = None,
    ) -> None:
        self.namespace = namespace or {}
        self.authorities = authorities or []

    def get_ns(self, _source: object | None = None) -> dict[str, object]:
        return self.namespace

    def get_authorities(self) -> list[BehaviorRegistry]:
        return self.authorities

    def get_inline_behaviors(self) -> list[object]:
        return []


class _SimpleActor(Actor, HasSimpleLook):
    """Pinned actor with the direct look facet."""


class _LookActor(Actor, HasLook):
    """Pinned actor with the bundled visual facets."""


@pytest.fixture(autouse=True)
def _reset_wearable_types():
    WearableType.clear_instances()
    yield
    WearableType.clear_instances()


def _actor_look(*, hair_color: HairColor = HairColor.RED) -> Look:
    return Look(
        hair_color=hair_color,
        hair_style=HairStyle.LONG,
        skin_tone=SkinTone.OLIVE,
    )


def _dress(actor: _LookActor) -> None:
    shirt_type = WearableType(
        label="presentation_shirt",
        noun="shirt",
        covers={BodyRegion.TOP},
        layer=WearableLayer.OUTER,
    )
    coat_type = WearableType(
        label="presentation_coat",
        noun="coat",
        covers={BodyRegion.TOP},
        layer=WearableLayer.OVER,
    )
    actor.outfit.assign("top_60", Wearable(token_from=shirt_type.label))
    actor.outfit.assign("top_80", Wearable(token_from=coat_type.label))


def _mark(actor: _LookActor) -> None:
    actor.ornamentation.add_ornament(
        Ornament(
            body_part=BodyPart.LEFT_ARM,
            ornament_type=OrnamentType.TATTOO,
            text="a dragon",
        ),
    )


def test_simple_look_renders_through_presence_aspect() -> None:
    actor = _SimpleActor(label="guide", look=_actor_look())

    rendered = render_text_as(actor, "presence_description", ctx=_TextCtx())

    assert "olive skin" in rendered
    assert "red long hair" in rendered


def test_has_look_recursively_composes_body_outfit_and_ornaments() -> None:
    actor = _LookActor(label="guide", look=_actor_look())
    _dress(actor)
    _mark(actor)

    rendered = render_text_as(actor, "presence_description", ctx=_TextCtx())

    assert "olive skin" in rendered
    assert "wearing shirt and coat" in rendered
    assert "a dragon tattoo on their left arm" in rendered


def test_empty_presence_components_do_not_leave_grammar_debris() -> None:
    actor = _LookActor(label="guide", look=_actor_look())

    rendered = render_text_as(actor, "presence_description", ctx=_TextCtx())

    assert "wearing" not in rendered
    assert "marked by" not in rendered
    assert not rendered.endswith(",")


def test_presence_rendering_reflects_live_look_and_outfit_state() -> None:
    actor = _LookActor(label="guide", look=_actor_look())

    initial = render_text_as(actor, "presence_description", ctx=_TextCtx())
    actor.look.hair_color = HairColor.BLUE
    _dress(actor)
    updated = render_text_as(actor, "presence_description", ctx=_TextCtx())

    assert "red long hair" in initial
    assert "blue long hair" in updated
    assert "wearing shirt and coat" in updated


def test_shared_session_renders_multiple_presence_subjects() -> None:
    first = _SimpleActor(label="first", look=_actor_look(hair_color=HairColor.RED))
    second = _SimpleActor(label="second", look=_actor_look(hair_color=HairColor.BLUE))
    ctx = _TextCtx(namespace={"actors": [first, second]})
    session = TextRenderSession(ctx=ctx)

    rendered = render_text_as(
        first,
        "presence_description",
        ctx=ctx,
        session=session,
        content="{% for actor in actors %}[{{ render_as(actor, 'presence_description') }}]{% endfor %}",
    )

    assert "red long hair" in rendered
    assert "blue long hair" in rendered


def test_render_as_filter_matches_documented_authoring_syntax() -> None:
    actor = _SimpleActor(label="guide", look=_actor_look())

    rendered = render_text_as(
        actor,
        "presence_description",
        ctx=_TextCtx(),
        content="{{ subject | render_as('presence_description') }}",
    )

    assert "olive skin" in rendered
    assert "red long hair" in rendered


def test_render_as_filter_forwards_explicit_child_bindings() -> None:
    target = object()
    authority = BehaviorRegistry(
        label="presentation.child-bindings",
        default_dispatch_layer=DispatchLayer.AUTHOR,
    )
    authority.register(
        lambda **_kwargs: "{{ packet.label }}",
        task="render_text",
        wants_caller_kind=object,
        wants_exact_kind=False,
    )
    bindings = {"packet": SimpleNamespace(label="bound packet")}

    rendered = render_text_as(
        target,
        "outer",
        ctx=_TextCtx(authorities=[authority]),
        content="{{ subject | render_as('nested', bindings={'packet': packet}) }}",
        bindings=bindings,
    )

    assert rendered == "bound packet"
    assert bindings == {"packet": SimpleNamespace(label="bound packet")}


def test_authored_content_replaces_recursive_presence_composition() -> None:
    target = object()

    rendered = render_text_as(
        target,
        "presence_description",
        ctx=_TextCtx(),
        content="A silhouette in a borrowed coat.",
    )

    assert rendered == "A silhouette in a borrowed coat."


def test_authority_dispatch_can_override_presence_text() -> None:
    actor = _LookActor(label="guide", look=_actor_look())
    authority = BehaviorRegistry(
        label="presentation.override",
        default_dispatch_layer=DispatchLayer.AUTHOR,
    )

    def _override(*, caller: object, aspect: str, ctx: _TextCtx) -> str | None:
        _ = caller, ctx
        return "The school librarian." if aspect == "presence_description" else None

    authority.register(
        _override,
        task="render_text",
        wants_caller_kind=_LookActor,
        wants_exact_kind=False,
    )

    assert render_text_as(
        actor,
        "presence_description",
        ctx=_TextCtx(authorities=[authority]),
    ) == "The school librarian."


def test_dispatch_rejects_an_invalid_non_winning_handler_result() -> None:
    target = object()
    authority = BehaviorRegistry(
        label="presentation.invalid-result",
        default_dispatch_layer=DispatchLayer.AUTHOR,
    )

    authority.register(
        lambda **_kwargs: 42,
        task="render_text",
        wants_caller_kind=object,
        wants_exact_kind=False,
    )
    authority.register(
        lambda **_kwargs: "valid override",
        task="render_text",
        wants_caller_kind=object,
        wants_exact_kind=False,
    )

    with pytest.raises(TypeError, match="must return str or None"):
        do_render_text(
            target,
            aspect="presence_description",
            ctx=_TextCtx(authorities=[authority]),
        )


def test_missing_adapter_and_symbol_fail_explicitly() -> None:
    actor = _SimpleActor(label="guide", look=_actor_look())

    with pytest.raises(LookupError, match="missing_description"):
        render_text_as(actor, "missing_description", ctx=_TextCtx())
    with pytest.raises(jinja2.UndefinedError):
        render_text_as(
            actor,
            "presence_description",
            ctx=_TextCtx(),
            content="{{ missing }}",
        )


def test_presence_rendering_does_not_mutate_the_actor() -> None:
    actor = _LookActor(label="guide", look=_actor_look())
    _dress(actor)
    _mark(actor)
    before = actor.unstructure()

    render_text_as(actor, "presence_description", ctx=_TextCtx())

    assert actor.unstructure() == before
