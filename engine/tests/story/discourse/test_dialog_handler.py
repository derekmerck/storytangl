from __future__ import annotations

from tangl.journal.discourse import AttributedFragment
from tangl.story.discourse import DialogHandler, DialogMuBlock


def test_dialog_handler_detects_format() -> None:
    text = "> [!POV] Hero\n> Hello world"

    assert DialogHandler.has_mu_blocks(text)


def test_parse_dialog_block() -> None:
    text = "> [!NPC.happy] Shopkeep\n> Welcome!"
    mu_blocks = DialogHandler.parse(text)

    assert len(mu_blocks) == 1
    block = mu_blocks[0]
    assert block.label == "Shopkeep"
    assert block.dialog_class == "NPC.happy"
    assert block.text == "Welcome!"


def test_mixed_narration_and_dialog() -> None:
    text = """
You enter the shop.

> [!NPC] Shopkeep
> Hello!

You wave back.
"""
    mu_blocks = DialogHandler.parse(text)

    assert len(mu_blocks) == 3
    assert [block.dialog_class for block in mu_blocks] == [
        "narration",
        "NPC",
        "narration",
    ]
    assert mu_blocks[1].label == "Shopkeep"
    assert mu_blocks[2].text == "You wave back."


def test_mu_block_to_fragment() -> None:
    mu_block = DialogMuBlock(text="Hello", label="Hero", dialog_class="pov")

    fragment = mu_block.to_fragment()

    assert isinstance(fragment, AttributedFragment)
    assert fragment.content == "Hello"
    assert fragment.who == "Hero"
    assert fragment.how == "pov"
