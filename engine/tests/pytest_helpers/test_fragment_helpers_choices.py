from __future__ import annotations

from types import SimpleNamespace

from .fragment_helpers import extract_all_choices, extract_blocks_with_choices


def test_extract_all_choices_and_blocks_with_choices() -> None:
    choice_in_block = SimpleNamespace(fragment_type="choice", content="Enter cave")
    standalone_choice = SimpleNamespace(fragment_type="choice", content="Wait")
    block_fragment = SimpleNamespace(fragment_type="block", choices=[choice_in_block])

    fragments = [block_fragment, standalone_choice]

    choices = extract_all_choices(fragments)
    assert choice_in_block in choices
    assert standalone_choice in choices

    blocks_with_choices = extract_blocks_with_choices(fragments)
    assert blocks_with_choices == [(block_fragment, [choice_in_block])]
