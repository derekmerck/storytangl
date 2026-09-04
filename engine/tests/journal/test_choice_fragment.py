from uuid import uuid4

import pytest

from tangl.journal.fragments import fragment_to_dto
from tangl.journal.intent import (
    ComposeAccepts,
    ComposePart,
    LengthValidator,
    PickAccepts,
    PieceConstraints,
    PiecesAccepts,
    PlaceAccepts,
    QuantityAccepts,
    RegexValidator,
    TextAccepts,
)
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


class TestTypedAcceptsSurvivesConstructorForm:
    """A discriminated ``accepts`` must round-trip through unstructure/structure.

    ``unstructure()`` elides defaults, and a union tag declared as
    ``kind: Literal["pick"] = "pick"`` is indistinguishable from one. Before the
    ``unstructurable`` marker was applied, a flat dump dropped the tag, structure
    could not re-validate the union, ``evolve()`` raised, and the frame's step
    stamp was silently skipped -- leaving the fragment at the ledger's "still
    open" sentinel forever (#436).
    """

    @pytest.mark.parametrize(
        "accepts",
        [
            PickAccepts(),
            PiecesAccepts(min=1, max=1, constraints=PieceConstraints(target_zone_ref="z")),
            TextAccepts(validators=[RegexValidator(pattern="^a"), LengthValidator(max=5)]),
            QuantityAccepts(min=1, max=9, unit="coin"),
            PlaceAccepts(source_zone_ref="a", target_zone_ref="b"),
            ComposeAccepts(
                parts=[
                    ComposePart(role="amount", accepts=QuantityAccepts(max=2)),
                    ComposePart(role="target", accepts=PiecesAccepts()),
                ]
            ),
        ],
        ids=lambda value: type(value).__name__,
    )
    def test_round_trip_preserves_the_union_member(self, accepts) -> None:
        fragment = ChoiceFragment(edge_id=uuid4(), text="act", accepts=accepts)

        restored = ChoiceFragment.structure(fragment.unstructure())

        assert type(restored.accepts) is type(accepts)
        assert restored.accepts == accepts

    def test_evolve_can_stamp_a_step(self) -> None:
        # The frame stamps journal records with evolve(); a failure here reads as
        # "open choice" and republishes a consumed edge to every client.
        fragment = ChoiceFragment(edge_id=uuid4(), text="act", accepts=PickAccepts())

        assert fragment.evolve(step=3).step == 3

    def test_dto_keeps_the_string_discriminator(self) -> None:
        # Persistence discriminates by class; the wire DTO keeps the literal.
        fragment = ChoiceFragment(edge_id=uuid4(), text="act", accepts=PiecesAccepts())

        assert fragment_to_dto(fragment)["accepts"]["kind"] == "pieces"

    def test_unstructure_still_elides_ordinary_defaults(self) -> None:
        # The tag is identity, not state: recursing must not re-admit defaults.
        fragment = ChoiceFragment(edge_id=uuid4(), text="act", accepts=PickAccepts())

        assert fragment.unstructure()["accepts"] == {"kind": PickAccepts}
