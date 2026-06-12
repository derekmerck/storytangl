from uuid import uuid4

from tangl.journal.prose import ChoiceFragment


def test_choice_fragment_with_unavailable_reason() -> None:
    fragment = ChoiceFragment(
        edge_id=uuid4(),
        text="Open the locked door",
        available=False,
        unavailable_reason="Requires keycard",
    )

    assert fragment.available is False
    assert fragment.unavailable_reason == "Requires keycard"

    data = fragment.model_dump()
    restored = ChoiceFragment.model_validate(data)
    assert restored.unavailable_reason == "Requires keycard"
