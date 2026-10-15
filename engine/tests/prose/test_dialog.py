"""Dialog callout grammar and projection tests."""

from __future__ import annotations

import pytest

from tangl.prose import DialogHandler


@pytest.mark.parametrize(
    ("header", "expected_label"),
    [
        ("> [!aside]", None),
        ("> [!aside] The Guide", "The Guide"),
    ],
)
def test_plain_custom_callout_type_with_optional_title(
    header: str,
    expected_label: str | None,
) -> None:
    text = f"{header}\n> Listen closely."

    assert DialogHandler.has_mu_blocks(text)
    [mu_block] = DialogHandler.parse(text)

    assert mu_block.dialog_class == "aside"
    assert mu_block.dialog_mode == "aside"
    assert mu_block.attitude is None
    assert mu_block.label == expected_label
    assert mu_block.text == "Listen closely."


@pytest.mark.parametrize("fold", ["+", "-"])
def test_fold_marker_is_not_part_of_type_or_title(fold: str) -> None:
    text = f"> [!custom.notice]{fold} Speaker Name\n> Folded content."

    assert DialogHandler.has_mu_blocks(text)
    [mu_block] = DialogHandler.parse(text)

    assert mu_block.dialog_class == "custom.notice"
    assert mu_block.dialog_mode == "custom"
    assert mu_block.attitude == "notice"
    assert mu_block.label == "Speaker Name"


def test_unknown_custom_type_is_accepted_and_colon_is_not_semantic() -> None:
    [mu_block] = DialogHandler.parse(
        "> [!unregistered:variant] Speaker\n> Still valid."
    )

    assert mu_block.dialog_class == "unregistered:variant"
    assert mu_block.dialog_mode == "unregistered:variant"
    assert mu_block.attitude is None


def test_mixed_dialog_and_ordinary_block_quote_are_classified_independently() -> None:
    text = (
        "> [!NPC.happy] Guide\n"
        "> Welcome.\n\n"
        "> This is an ordinary quoted paragraph."
    )

    assert DialogHandler.has_mu_blocks(text)
    dialog, narration = DialogHandler.parse(text)

    assert dialog.dialog_class == "NPC.happy"
    assert dialog.dialog_mode == "NPC"
    assert dialog.attitude == "happy"
    assert narration.dialog_class == "narration"
    assert narration.text == "> This is an ordinary quoted paragraph."


def test_malformed_claim_is_detected_and_runtime_parse_fails_defensively() -> None:
    text = "> [!NPC.happy Guide\n> Missing the closing bracket."

    assert DialogHandler.has_mu_blocks(text)
    assert DialogHandler.find_malformed_header(text) == "> [!NPC.happy Guide"
    with pytest.raises(ValueError, match="Invalid dialog syntax"):
        DialogHandler.parse(text)


def test_ordinary_block_quote_is_not_dialog_markup() -> None:
    text = "> This is only a quotation."

    assert not DialogHandler.has_mu_blocks(text)
    assert DialogHandler.find_malformed_header(text) is None


@pytest.mark.parametrize("wrapper", ["fence", "tilde", "inline", "unclosed"])
@pytest.mark.parametrize("header", ["> [!npc] guide", "> [!npc guide"])
def test_all_dialog_entry_points_preserve_code_regions(wrapper: str, header: str) -> None:
    body = f"Rin #intro\n\n{header}\n> literal"
    if wrapper == "fence":
        text = f"```python\n{body}\n```"
    elif wrapper == "tilde":
        text = f"~~~\n{body}\n~~~"
    elif wrapper == "inline":
        text = f"``{body}``"
    else:
        text = f"```\n{body}"
    assert not DialogHandler.has_mu_blocks(text)
    assert DialogHandler.find_malformed_header(text) is None
    [unit] = DialogHandler.parse(text)
    assert unit.dialog_class == "narration"
    assert unit.text == text


def test_protected_malformed_header_does_not_hide_a_real_header_outside_code() -> None:
    text = "```\n\n> [!npc missing\n```\n\n> [!npc outside\n> invalid"
    assert DialogHandler.has_mu_blocks(text)
    assert DialogHandler.find_malformed_header(text) == "> [!npc outside"
    with pytest.raises(ValueError, match="npc outside"):
        DialogHandler.parse(text)
