"""Shared authored values, pure parsing, and constructor-form ownership."""
from collections.abc import Mapping
from uuid import UUID, uuid4

import pytest
from pydantic import Field

from tangl.journal.fragments import AttributedFragment
from tangl.persistence.serializers import JsonSerializationHandler
from tangl.prose import DialogHandler, DialogMuBlock, MuBlock
from tangl.prose.mu_block import ConceptReference, NameResolver, SpeakerResolver
from tangl.prose.naming import ProseBlock
from tangl.story import Actor, StoryGraph
from tangl.vm.ctx import VmPhaseCtx


class CustomDialog(DialogMuBlock):
    emphasis: str = ""

    def prepare_fragment(
        self, *, source_id: UUID | None = None, ns: Mapping[str, object] | None = None,
        ctx: VmPhaseCtx | None = None, name_resolver: NameResolver | None = None,
        speaker_resolver: SpeakerResolver | None = None,
    ) -> AttributedFragment:
        fragment = super().prepare_fragment(
            source_id=source_id, ns=ns, ctx=ctx, name_resolver=name_resolver,
            speaker_resolver=speaker_resolver,
        )
        return fragment.model_copy(update={"tags": fragment.tags | {f"emphasis:{self.emphasis}"}})


class CustomProseBlock(ProseBlock):
    prose: list[MuBlock | DialogMuBlock | CustomDialog] = Field(
        default_factory=list, json_schema_extra={"include": True, "unstructurable": True},
    )


@pytest.mark.parametrize("kind", [MuBlock, DialogMuBlock])
@pytest.mark.parametrize("text", ["", [], "literal"])
def test_text_and_template_are_exclusive(kind: type[MuBlock], text: str | list) -> None:
    with pytest.raises(ValueError, match="text or template, not both"):
        kind(text=text, template="{{ value }}")


def test_parse_is_authored_structure_only(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("Parsing must not bind or project a speaker")

    monkeypatch.setattr(DialogMuBlock, "prepare_fragment", forbidden)
    source_id = uuid4()
    units = DialogHandler.parse(
        "Narrative.\n\n> [!NPC.happy]+ host\n> Nanae #intro is literal speech.",
        source_id=source_id,
    )
    assert [unit.text for unit in units] == ["Narrative.", "Nanae #intro is literal speech."]
    assert units[1].label == "host"
    assert units[1].dialog_class == "NPC.happy"
    assert units[1].dialog_mode == "NPC"
    assert units[1].attitude == "happy"
    assert all(unit.source_id == source_id for unit in units)
    assert "speaker_name" not in units[1].unstructure()


def test_embedded_authored_values_restore_classes_and_in_place_parts() -> None:
    graph = StoryGraph()
    block = ProseBlock(label="start", registry=graph)
    units = DialogHandler.parse(
        "Narrative.\n\n> [!NPC.happy] host\n> Speech.", source_id=block.uid,
    )
    literal = MuBlock(text=[])
    literal.text.extend(["Meet ", ConceptReference(ref="host"), "."])
    literal.style_dict["font-weight"] = "600"
    block.prose.extend([literal, *units])
    data = graph.unstructure()
    restored = StoryGraph.structure(data)
    stored = restored.get(block.uid).prose
    assert [type(unit) for unit in stored] == [MuBlock, DialogMuBlock, DialogMuBlock]
    assert isinstance(stored[0].text[1], ConceptReference)
    assert stored[0].text[1].ref == "host"
    assert stored[0].style_dict == {"font-weight": "600"}
    assert stored[2].dialog_class == "NPC.happy"
    assert stored[2].label == "host"
    assert stored[2].source_id == block.uid
    assert [unit.unstructure() for unit in stored] == [unit.unstructure() for unit in block.prose]


def test_declared_custom_variant_survives_owner_graph_flat_json_and_projection() -> None:
    graph = StoryGraph()
    actor = Actor(label="rin", name="Rin", registry=graph)
    owner = CustomProseBlock(label="start", registry=graph)
    authored = CustomDialog(label="host", dialog_class="NPC.happy", text="Hello.")
    authored.emphasis = "urgent"
    authored.style_dict["font-weight"] = "700"
    owner.prose.append(authored)
    restored = StoryGraph.structure(JsonSerializationHandler.deserialize(
        JsonSerializationHandler.serialize(graph.unstructure()),
    ))
    stored_owner = restored.get(owner.uid)
    assert isinstance(stored_owner, CustomProseBlock)
    stored = stored_owner.prose[0]
    assert type(stored) is CustomDialog
    assert stored.emphasis == "urgent"
    assert stored.style_dict == {"font-weight": "700"}
    assert stored.unstructure() == authored.unstructure()
    before = restored.value_hash()
    fragment = DialogHandler.render(
        stored_owner.prose, ns={"host": restored.get(actor.uid)}, source_id=owner.uid,
    )[0]
    assert fragment.content == "Hello."
    assert fragment.how == "NPC.happy"
    assert fragment.speaker_id == str(actor.uid)
    assert fragment.source_id == owner.uid
    assert "emphasis:urgent" in fragment.tags
    assert restored.value_hash() == before
