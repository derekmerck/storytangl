from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

from tangl.journal.fragments import (
    AttributedFragment,
    ChoiceFragment,
    ContentFragment,
    DialogFragment,
    MediaFragment,
)
from tangl.media.media_data_type import MediaDataType
from tangl.media.media_resource import MediaResourceInventoryTag as MediaRIT
from tangl.renpy import RenPySessionBridge
from tangl.service import RuntimeEnvelope, RuntimeInfo


class FakeServiceManager:
    def __init__(self) -> None:
        self.user_id = uuid4()
        self.ledger_id = uuid4()
        self.create_story_calls: list[dict[str, object]] = []
        self.resolve_choice_calls: list[dict[str, object]] = []

    def create_user(self, *, secret: str | None = None, **_kwargs: object) -> RuntimeInfo:
        return RuntimeInfo.ok(message="User created", user_id=str(self.user_id))

    def create_story(self, *, user_id: UUID, world_id: str, **_kwargs: object) -> RuntimeEnvelope:
        self.create_story_calls.append({"user_id": user_id, "world_id": world_id})
        return RuntimeEnvelope(
            fragments=[ContentFragment(content="A beginning.", step=0)],
            metadata={"ledger_id": str(self.ledger_id), "world_id": world_id},
        )

    def resolve_choice(
        self,
        *,
        choice_id: UUID,
        user_id: UUID | None = None,
        ledger_id: UUID | None = None,
        choice_payload: object = None,
    ) -> RuntimeEnvelope:
        self.resolve_choice_calls.append(
            {
                "choice_id": choice_id,
                "user_id": user_id,
                "ledger_id": ledger_id,
                "choice_payload": choice_payload,
            }
        )
        return RuntimeEnvelope(
            fragments=[ContentFragment(content="A resolution.", step=1)],
            metadata={"ledger_id": str(ledger_id)},
        )


def _write_svg(path: Path, *, fill: str) -> None:
    path.write_text(
        (
            '<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64">'
            f'<rect width="64" height="64" fill="{fill}"/>'
            "</svg>"
        ),
        encoding="utf-8",
    )


def test_bridge_syncs_user_and_ledger_ids_and_passes_choice_payload() -> None:
    service_manager = FakeServiceManager()
    bridge = RenPySessionBridge(service_manager=service_manager)

    envelope = bridge.start("renpy_demo")

    assert envelope.metadata["ledger_id"] == str(service_manager.ledger_id)
    assert bridge.user_id == service_manager.user_id
    assert bridge.ledger_id == service_manager.ledger_id
    assert service_manager.create_story_calls == [
        {"user_id": service_manager.user_id, "world_id": "renpy_demo"}
    ]

    choice_id = uuid4()
    payload = {"branch": "lantern_road"}
    bridge.choose(choice_id, choice_payload=payload)

    assert service_manager.resolve_choice_calls == [
        {
            "choice_id": choice_id,
            "user_id": service_manager.user_id,
            "ledger_id": service_manager.ledger_id,
            "choice_payload": payload,
        }
    ]


def test_build_turns_groups_by_step_and_preserves_unavailable_choices() -> None:
    bridge = RenPySessionBridge(service_manager=FakeServiceManager())
    first_choice_id = uuid4()
    second_choice_id = uuid4()

    turns = bridge.build_turns(
        [
            ContentFragment(content="Rain on the roof.", step=0),
            ChoiceFragment(edge_id=first_choice_id, text="Step inside", available=True, step=0),
            ChoiceFragment(
                edge_id=second_choice_id,
                text="Open the cellar",
                available=False,
                unavailable_reason="missing_key",
                step=0,
            ),
            ContentFragment(content="A later beat.", step=1),
        ]
    )

    assert [turn.step for turn in turns] == [0, 1]
    assert [line.text for line in turns[0].lines] == ["Rain on the roof."]
    assert [choice.text for choice in turns[0].choices] == ["Step inside", "Open the cellar"]
    assert turns[0].choices[0].available is True
    assert turns[0].choices[1].available is False
    assert turns[0].choices[1].unavailable_reason == "missing_key"
    assert [line.text for line in turns[1].lines] == ["A later beat."]


def test_build_turns_adapts_media_and_reuses_stable_portrait_tags(tmp_path: Path) -> None:
    background_path = tmp_path / "background.svg"
    portrait_path = tmp_path / "portrait.svg"
    _write_svg(background_path, fill="#223344")
    _write_svg(portrait_path, fill="#ccaa66")

    bridge = RenPySessionBridge(service_manager=FakeServiceManager())
    turns = bridge.build_turns(
        [
            MediaFragment(
                content=MediaRIT(path=background_path, data_type=MediaDataType.VECTOR),
                content_format="rit",
                content_type=MediaDataType.VECTOR,
                media_role="narrative_im",
                step=0,
            ),
            DialogFragment(
                content=[
                    AttributedFragment(
                        content="You're right on time.",
                        who="Guide",
                        how="NPC.concerned",
                        media="dialog_im",
                        speaker_key="guide",
                        media_payload={"ref": str(portrait_path), "media_role": "dialog_im"},
                        step=0,
                    ),
                    AttributedFragment(
                        content="Dawn will not wait for us.",
                        who="Guide",
                        how="NPC",
                        media="dialog_im",
                        speaker_key="guide",
                        media_payload={"ref": str(portrait_path), "media_role": "dialog_im"},
                        step=0,
                    ),
                ],
                step=0,
            ),
        ]
    )

    assert len(turns) == 1
    turn = turns[0]
    assert [op.action for op in turn.media_ops] == ["scene", "show", "show"]
    assert turn.media_ops[0].source == str(background_path)
    assert [op.tag for op in turn.media_ops[1:]] == ["guide", "guide"]
    assert [line.speaker for line in turn.lines] == ["Guide", "Guide"]
    assert [line.text for line in turn.lines] == [
        "You're right on time.",
        "Dawn will not wait for us.",
    ]


def test_build_turns_normalizes_stringified_rit_media(tmp_path: Path) -> None:
    background_path = tmp_path / "background.svg"
    _write_svg(background_path, fill="#446688")

    rit = MediaRIT(path=background_path, data_type=MediaDataType.VECTOR, label="background.svg")
    bridge = RenPySessionBridge(service_manager=FakeServiceManager())

    turns = bridge.build_turns(
        [
            MediaFragment(
                content=str(rit),
                content_format="rit",
                content_type=MediaDataType.VECTOR,
                media_role="narrative_im",
                step=0,
            )
        ]
    )

    assert len(turns) == 1
    assert len(turns[0].media_ops) == 1
    assert turns[0].media_ops[0].source == str(background_path)
