from tangl.journal.discourse import ChoiceFragment


def test_choice_fragment_with_unavailable_reason() -> None:
    fragment = ChoiceFragment(
        content="Open the locked door",
        active=False,
        unavailable_reason="Requires keycard",
    )

    assert fragment.active is False
    assert fragment.unavailable_reason == "Requires keycard"

    data = fragment.model_dump()
    restored = ChoiceFragment.model_validate(data)
    assert restored.unavailable_reason == "Requires keycard"
