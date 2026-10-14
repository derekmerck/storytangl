"""Shared authored values, pure parsing, and constructor-form ownership."""
from uuid import uuid4

import pytest

from tangl.prose import DialogHandler, DialogMuBlock, MuBlock
from tangl.prose.mu_block import ConceptReference
from tangl.prose.naming import ProseBlock
from tangl.story import StoryGraph


@pytest.mark.parametrize("kind", [MuBlock, DialogMuBlock])
@pytest.mark.parametrize("text", ["", [], "literal"])
def test_text_and_template_are_exclusive(kind: type[MuBlock], text: str | list) -> None:
    with pytest.raises(ValueError, match="text or template, not both"):
        kind(text=text, template="{{ value }}")


def test_parse_is_authored_structure_only(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("Parsing must not bind or project a speaker")

    monkeypatch.setattr(DialogMuBlock, "to_fragment", forbidden)
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
