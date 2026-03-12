"""Contract tests for concept-carried narrator knowledge and prose seams.

Organized by concept:
- presentable references and focalization
- speech profile fallback
- presence adapter seams
- current engine baseline contracts
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from types import SimpleNamespace
from typing import Any, Protocol, runtime_checkable
from uuid import uuid4

import jinja2

from tangl.lang.gens import Gens
from tangl.lang.nominal import DeterminativeType as DT
from tangl.lang.pronoun import PT
from tangl.story import EntityKnowledge, StoryGraph, get_narrator_key
from tangl.story.episode import Block
from tangl.story.system_handlers import render_block_content
from tangl.utils.rejinja import RecursiveTemplate
from tangl.vm import Ledger


class Familiarity(IntEnum):
    """Toy familiarity scale for the contract spike."""

    ANONYMOUS = 0
    FAMILIAR = 1
    NAMED = 2
    INTIMATE = 3


@runtime_checkable
class Presentable(Protocol):
    """Minimum prose-facing interface for the spike."""

    def get_label(self) -> str:
        ...

    def get_nominal(
        self,
        *,
        familiarity: Familiarity = Familiarity.ANONYMOUS,
        det: DT = DT.DEFINITE,
    ) -> str:
        ...

    def get_pronoun(self, pt: PT) -> str:
        ...


def _default_pronouns(gender: Gens) -> str:
    if gender is Gens.XX:
        return "she/her/her/hers"
    if gender is Gens.XY:
        return "he/him/his/his"
    return "they/them/their/theirs"


def _articulate(value: str, *, det: DT) -> str:
    if not value:
        return ""
    article = DT.get_det(det, next_word=value)
    return f"{article} {value}".strip()


@dataclass(slots=True)
class ToyLook:
    """Toy presence payload proving the prose/media seam."""

    description: str
    media_prompt: str | None = None


@dataclass(slots=True)
class SpeakerProfile:
    """Toy speaker profile derived lazily from entity fields."""

    native_language: str = "en"
    register: str = "casual"
    vocabulary: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_entity(cls, entity: Any) -> "SpeakerProfile":
        return cls(
            native_language=getattr(entity, "native_language", "en"),
            register=getattr(entity, "register", "casual"),
            vocabulary=dict(getattr(entity, "vocabulary", {}) or {}),
        )


@dataclass(slots=True)
class DiscourseContext:
    """Ephemeral per-render discourse state for the spike."""

    narrator_key: str = "_"
    focused_entity: Presentable | None = None
    last_speaker: Presentable | None = None
    speaker_profiles: dict[str, SpeakerProfile] = field(default_factory=dict)

    def set_focus(self, entity: Presentable | None) -> None:
        self.focused_entity = entity

    def focus_pronoun(self, pt: PT) -> str:
        if self.focused_entity is None:
            return ""
        return self.focused_entity.get_pronoun(pt)

    @classmethod
    def from_phase_ctx(cls, ctx: Any = None) -> "DiscourseContext":
        return cls(narrator_key=get_narrator_key(ctx))


VOCAB_BANKS: dict[str, dict[str, str]] = {
    "en": {
        "greeting.casual": "hi",
        "greeting.formal": "good evening",
        "farewell.casual": "bye",
        "affirmation": "yeah",
    },
    "ru": {
        "greeting.casual": "Privet",
        "greeting.formal": "Zdravstvuyte",
        "farewell.casual": "Poka",
        "affirmation": "Da",
    },
}


STATE_UNKNOWN = "UNKNOWN"
STATE_FAMILIAR = "FAMILIAR"
STATE_IDENTIFIED = "IDENTIFIED"


@dataclass(slots=True)
class ToyConcept:
    """Toy concept implementing the minimal Presentable contract."""

    label: str
    name: str | None = None
    nominal: str | None = None
    pronouns: str | None = None
    gender: Gens = Gens.X_
    content: str = ""
    uid: str = field(default_factory=lambda: str(uuid4()))
    narrator_knowledge: dict[str, EntityKnowledge] = field(default_factory=dict)

    def get_label(self) -> str:
        return self.label

    def get_knowledge(self, key: str = "_") -> EntityKnowledge:
        narrator_key = str(key or "_")
        knowledge = self.narrator_knowledge.get(narrator_key)
        if not isinstance(knowledge, EntityKnowledge):
            knowledge = EntityKnowledge()
            self.narrator_knowledge[narrator_key] = knowledge
        return knowledge

    def get_nominal(
        self,
        *,
        familiarity: Familiarity = Familiarity.ANONYMOUS,
        det: DT = DT.DEFINITE,
    ) -> str:
        if familiarity in {Familiarity.NAMED, Familiarity.INTIMATE}:
            return self.name or self.nominal or self.get_label()

        if familiarity is Familiarity.FAMILIAR:
            base = self.nominal or self.name or self.get_label()
            return _articulate(base, det=DT.DEFINITE)

        base = self.nominal or self.name or self.get_label()
        description = self.describe()
        if description and description != base:
            return _articulate(description, det=DT.INDEFINITE)
        return _articulate(base, det=DT.INDEFINITE)

    def get_pronoun(self, pt: PT) -> str:
        forms = (self.pronouns or _default_pronouns(self.gender)).split("/")
        match pt:
            case PT.S:
                return forms[0]
            case PT.O:
                return forms[1]
            case PT.PA:
                return forms[2]
            case PT.P:
                return forms[3]
        raise ValueError(f"Unsupported pronoun type: {pt}")

    def describe(
        self,
        *,
        ns: dict[str, Any] | None = None,
        ctx: DiscourseContext | None = None,
    ) -> str:
        if not self.content:
            return self.nominal or self.name or self.get_label()

        env = _build_env(ctx or DiscourseContext())
        template = env.from_string(self.content, template_class=RecursiveTemplate)
        scope = dict(ns or {})
        scope.setdefault("self", self)
        return template.render(**scope).strip()


@dataclass(slots=True)
class ToyActor(ToyConcept):
    """Toy actor adding sparse speech-profile fields."""

    native_language: str = "en"
    register: str = "casual"
    vocabulary: dict[str, str] = field(default_factory=dict)


class HasPresenceMixin:
    """Toy presence seam proving prose/media delegation."""

    look: ToyLook | None

    def describe(
        self,
        *,
        ns: dict[str, Any] | None = None,
        ctx: DiscourseContext | None = None,
    ) -> str:
        if not getattr(self, "look", None):
            return super().describe(ns=ns, ctx=ctx)  # type: ignore[misc]
        return ToyProseAdapter.describe_presence(self, ctx=ctx, ns=ns)

    def adapt_media_spec(self, *, ctx: DiscourseContext | None = None) -> dict[str, Any] | None:
        return ToyMediaAdapter.from_presence(self, ctx=ctx)


@dataclass(slots=True)
class ToyPresenceActor(HasPresenceMixin, ToyActor):
    """Toy actor with presence data attached."""

    look: ToyLook | None = None


class ToyProseAdapter:
    """Toy prose adapter proving that presence stays outside the data model."""

    @staticmethod
    def describe_presence(
        entity: ToyPresenceActor,
        *,
        ctx: DiscourseContext | None = None,
        ns: dict[str, Any] | None = None,
    ) -> str:
        if entity.look is None:
            return ToyActor.describe(entity, ns=ns, ctx=ctx)

        scope = dict(ns or {})
        scope.setdefault("look_description", entity.look.description)
        if entity.content:
            env = _build_env(ctx or DiscourseContext())
            template = env.from_string(entity.content, template_class=RecursiveTemplate)
            return template.render(**scope).strip()
        return entity.look.description


class ToyMediaAdapter:
    """Toy media adapter proving that presence can project beyond prose."""

    @staticmethod
    def from_presence(
        entity: ToyPresenceActor,
        *,
        ctx: DiscourseContext | None = None,
    ) -> dict[str, Any] | None:
        _ = ctx
        if entity.look is None:
            return None
        return {
            "media_role": "avatar_im",
            "subject": entity.get_label(),
            "prompt": entity.look.media_prompt or entity.look.description,
        }


def resolve_speech(intent: str, entity: ToyActor, ctx: DiscourseContext) -> str:
    profile = ctx.speaker_profiles.setdefault(
        str(entity.uid),
        SpeakerProfile.from_entity(entity),
    )
    return (
        profile.vocabulary.get(intent)
        or VOCAB_BANKS.get(profile.native_language, {}).get(intent)
        or VOCAB_BANKS["en"].get(intent)
        or intent
    )


def _knowledge_reference(entity: Presentable, ctx: DiscourseContext) -> EntityKnowledge:
    getter = getattr(entity, "get_knowledge", None)
    if not callable(getter):
        raise TypeError(f"{type(entity).__name__} does not provide get_knowledge(key)")
    return getter(ctx.narrator_key)


def _reference_text(entity: Presentable, knowledge: EntityKnowledge) -> str:
    if knowledge.state == STATE_IDENTIFIED:
        return entity.get_nominal(familiarity=Familiarity.NAMED)
    if knowledge.state == STATE_FAMILIAR:
        return knowledge.nominal_handle or entity.get_nominal(familiarity=Familiarity.FAMILIAR)
    return knowledge.first_description or entity.get_nominal(familiarity=Familiarity.ANONYMOUS)


def _prime_unknown_knowledge(entity: Presentable, knowledge: EntityKnowledge) -> None:
    if knowledge.first_description is None:
        knowledge.first_description = entity.get_nominal(familiarity=Familiarity.ANONYMOUS)
    if knowledge.nominal_handle is None:
        base = getattr(entity, "nominal", None) or getattr(entity, "name", None) or entity.get_label()
        knowledge.nominal_handle = _articulate(base, det=DT.DEFINITE)


def _filter_n(entity: Presentable, ctx: DiscourseContext) -> str:
    knowledge = _knowledge_reference(entity, ctx)
    ctx.set_focus(entity)
    if knowledge.state == STATE_UNKNOWN:
        _prime_unknown_knowledge(entity, knowledge)
        knowledge.state = STATE_FAMILIAR
        return knowledge.first_description or entity.get_nominal(
            familiarity=Familiarity.ANONYMOUS,
        )
    return _reference_text(entity, knowledge)


def _filter_ref(entity: Presentable, ctx: DiscourseContext) -> str:
    knowledge = _knowledge_reference(entity, ctx)
    ctx.set_focus(entity)
    return _reference_text(entity, knowledge)


def _filter_meet(entity: Presentable, ctx: DiscourseContext) -> str:
    knowledge = _knowledge_reference(entity, ctx)
    ctx.set_focus(entity)
    if knowledge.state == STATE_IDENTIFIED:
        return entity.get_nominal(familiarity=Familiarity.NAMED)

    _prime_unknown_knowledge(entity, knowledge)
    anonymous = knowledge.first_description or entity.get_nominal(familiarity=Familiarity.ANONYMOUS)
    named = entity.get_nominal(familiarity=Familiarity.NAMED)
    knowledge.state = STATE_IDENTIFIED
    knowledge.identification_source = "direct_introduction"
    if anonymous == named:
        return named
    return f"{anonymous} - {named}, as it turns out -"


def _filter_desc(entity: Any, ctx: DiscourseContext) -> str:
    ctx.set_focus(entity)
    return entity.describe(ctx=ctx)


def _build_env(ctx: DiscourseContext) -> jinja2.Environment:
    env = jinja2.Environment()
    env.filters["n"] = lambda entity: _filter_n(entity, ctx)
    env.filters["ref"] = lambda entity: _filter_ref(entity, ctx)
    env.filters["meet"] = lambda entity: _filter_meet(entity, ctx)
    env.filters["desc"] = lambda entity: _filter_desc(entity, ctx)
    env.filters["subj"] = lambda entity: entity.get_pronoun(PT.S)
    env.filters["obj"] = lambda entity: entity.get_pronoun(PT.O)
    env.filters["poss_adj"] = lambda entity: entity.get_pronoun(PT.PA)
    env.filters["poss"] = lambda entity: entity.get_pronoun(PT.P)
    env.filters["greeting"] = lambda entity: resolve_speech("greeting.casual", entity, ctx)
    env.filters["farewell"] = lambda entity: resolve_speech("farewell.casual", entity, ctx)
    env.filters["says"] = lambda entity, intent: resolve_speech(intent, entity, ctx)

    env.globals["focus_subj"] = lambda: ctx.focus_pronoun(PT.S)
    env.globals["focus_obj"] = lambda: ctx.focus_pronoun(PT.O)
    env.globals["focus_poss_adj"] = lambda: ctx.focus_pronoun(PT.PA)
    env.globals["focus_poss"] = lambda: ctx.focus_pronoun(PT.P)
    return env


def _render_contract_template(
    template_source: str,
    *,
    ctx: DiscourseContext,
    **scope: Any,
) -> str:
    env = _build_env(ctx)
    template = env.from_string(template_source, template_class=RecursiveTemplate)
    return template.render(**scope).strip()


def _ctx_with_ns(ns: dict[str, object] | None = None) -> SimpleNamespace:
    return SimpleNamespace(get_ns=lambda _caller: dict(ns or {}))


class TestPresentableFocalization:
    """Tests for nominal resolution and discourse focus."""

    def test_anonymous_reference_becomes_named_after_meet(self) -> None:
        ctx = DiscourseContext()
        actor = ToyPresenceActor(
            label="katya",
            name="Katya",
            nominal="bartender",
            gender=Gens.XX,
            look=ToyLook(description="blue-haired bartender"),
        )

        first = _render_contract_template("{{ actor|n }}", ctx=ctx, actor=actor)
        meeting = _render_contract_template("{{ actor|meet }}", ctx=ctx, actor=actor)
        second = _render_contract_template("{{ actor|n }}", ctx=ctx, actor=actor)

        assert first == "a blue-haired bartender"
        assert meeting == "a blue-haired bartender - Katya, as it turns out -"
        assert second == "Katya"
        assert actor.get_knowledge().state == STATE_IDENTIFIED
        assert actor.get_knowledge().identification_source == "direct_introduction"

    def test_focus_pronouns_follow_the_most_recently_referenced_entity(self) -> None:
        ctx = DiscourseContext()
        katya = ToyActor(label="katya", name="Katya", nominal="bartender", gender=Gens.XX)
        viktor = ToyActor(label="viktor", name="Viktor", nominal="guard", gender=Gens.XY)

        first = _render_contract_template(
            "{{ actor|n }} waved. {{ focus_subj()|capitalize }} smiled.",
            ctx=ctx,
            actor=katya,
        )
        second = _render_contract_template(
            "{{ actor|n }} answered. {{ focus_subj()|capitalize }} nodded.",
            ctx=ctx,
            actor=viktor,
        )

        assert first == "a bartender waved. She smiled."
        assert second == "a guard answered. He nodded."

    def test_narrator_key_selection_isolates_state_on_the_same_entity(self) -> None:
        player_ctx = DiscourseContext.from_phase_ctx(
            SimpleNamespace(get_meta=lambda: {"narrator_key": "player"}),
        )
        guide_ctx = DiscourseContext.from_phase_ctx(
            SimpleNamespace(get_meta=lambda: {"narrator_key": "guide"}),
        )

        actor = ToyActor(label="katya", name="Katya", nominal="traveler", gender=Gens.XX)

        assert player_ctx.narrator_key == "player"
        assert guide_ctx.narrator_key == "guide"
        assert _render_contract_template("{{ actor|meet }}", ctx=player_ctx, actor=actor) == (
            "a traveler - Katya, as it turns out -"
        )
        assert _render_contract_template("{{ actor|n }}", ctx=guide_ctx, actor=actor) == "a traveler"
        assert actor.get_knowledge("player").state == STATE_IDENTIFIED
        assert actor.get_knowledge("guide").state == STATE_FAMILIAR

    def test_role_and_actor_knowledge_remain_distinct_in_the_same_render_scope(self) -> None:
        ctx = DiscourseContext()
        role = ToyConcept(label="villain_role", nominal="masked villain")
        actor = ToyActor(label="katya", name="Katya", nominal="bartender", gender=Gens.XX)

        rendered = _render_contract_template(
            "{{ role|n }} confronted {{ actor|meet }}.",
            ctx=ctx,
            role=role,
            actor=actor,
        )

        assert rendered == "a masked villain confronted a bartender - Katya, as it turns out -."
        assert role.get_knowledge().state == STATE_FAMILIAR
        assert actor.get_knowledge().state == STATE_IDENTIFIED


class TestSpeakerProfiles:
    """Tests for speech profile fallback behavior."""

    def test_speech_resolution_falls_back_from_override_to_language_to_english_to_literal(self) -> None:
        ctx = DiscourseContext()

        override = ToyActor(
            label="katya",
            vocabulary={"greeting.casual": "Zdorovo"},
            native_language="ru",
        )
        language_default = ToyActor(label="anya", native_language="ru")
        english_fallback = ToyActor(label="sam", native_language="xx")
        literal_fallback = ToyActor(label="casey", native_language="xx")

        assert resolve_speech("greeting.casual", override, ctx) == "Zdorovo"
        assert resolve_speech("greeting.casual", language_default, ctx) == "Privet"
        assert resolve_speech("farewell.casual", english_fallback, ctx) == "bye"
        assert resolve_speech("unknown.intent", literal_fallback, ctx) == "unknown.intent"

    def test_contract_spike_can_render_outside_the_active_journal_pipeline(self) -> None:
        ctx = DiscourseContext()
        actor = ToyActor(
            label="katya",
            name="Katya",
            nominal="traveler",
            native_language="ru",
            gender=Gens.XX,
        )

        rendered = _render_contract_template(
            "{{ actor|n }} said {{ actor|greeting }}.",
            ctx=ctx,
            actor=actor,
        )

        assert rendered == "a traveler said Privet."


class TestPresenceAdapters:
    """Tests for presence-driven prose and media enrichment."""

    def test_presence_enriches_description_without_changing_presentable_contract(self) -> None:
        ctx = DiscourseContext()
        actor = ToyPresenceActor(
            label="viktor",
            name="Viktor",
            nominal="bartender",
            gender=Gens.XY,
            look=ToyLook(
                description="blue-haired bartender in a silver jacket",
                media_prompt="portrait of a blue-haired bartender in a silver jacket",
            ),
        )

        description = _render_contract_template("{{ actor|desc }}", ctx=ctx, actor=actor)
        media_spec = actor.adapt_media_spec(ctx=ctx)

        assert isinstance(actor, Presentable)
        assert description == "blue-haired bartender in a silver jacket"
        assert media_spec == {
            "media_role": "avatar_im",
            "subject": "viktor",
            "prompt": "portrait of a blue-haired bartender in a silver jacket",
        }

    def test_presence_actor_without_look_degrades_to_base_description(self) -> None:
        ctx = DiscourseContext()
        actor = ToyPresenceActor(label="keeper", nominal="shopkeeper", gender=Gens.X_)

        assert _render_contract_template("{{ actor|desc }}", ctx=ctx, actor=actor) == "shopkeeper"
        assert actor.adapt_media_spec(ctx=ctx) is None


class TestCurrentEngineBaseline:
    """Tests documenting the current v38 baseline for the spike."""

    def test_phase_ctx_is_ephemeral_while_ledger_is_persistent(self) -> None:
        """Document the current split: Ledger persists; PhaseCtx is rebuilt per pass."""
        graph = StoryGraph(locals={"gold": 7})
        block = Block(label="start", content="Start")
        graph.add(block)

        ledger = Ledger.from_graph(graph, block.uid)
        ctx_1 = ledger._make_phase_ctx()
        ctx_2 = ledger._make_phase_ctx()

        ns_1 = ctx_1.get_ns(block)
        ns_2 = ctx_2.get_ns(block)

        assert ledger.cursor_id == block.uid
        assert ctx_1 is not ctx_2
        assert ns_1 is ctx_1.get_ns(block)
        assert ns_1 is not ns_2
        assert ns_1["gold"] == 7
        assert ns_2["gold"] == 7

    def test_narrator_key_can_come_from_context_meta_without_ledger_schema_changes(self) -> None:
        graph = StoryGraph()
        block = Block(label="start", content="Start")
        graph.add(block)

        ledger = Ledger.from_graph(graph, block.uid)
        ctx = SimpleNamespace(get_meta=lambda: {"narrator_key": "guide"})

        assert get_narrator_key(ctx) == "guide"
        assert "narrative_session" not in ledger.model_dump(mode="python")
        assert "narrator_state" not in ledger.model_dump(mode="python")

    def test_story_block_rendering_still_uses_namespace_and_format_map_not_jinja(self) -> None:
        """Document the live renderer baseline for the prose spike."""
        block = Block(label="start", content="Hello {{name}} / {name}")

        fragment = render_block_content(caller=block, ctx=_ctx_with_ns({"name": "Joe"}))

        assert fragment is not None
        assert fragment.content == "Hello {name} / Joe"
