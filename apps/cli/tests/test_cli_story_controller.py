from __future__ import annotations

from uuid import UUID, uuid4

import cmd2
import pytest

from tangl.cli.controllers.story_controller import StoryController
from tangl.cli.rendering import PlainTerminalRenderer
from tangl.journal.fragments import ChoiceFragment, ContentFragment, PieceFragment
from tangl.journal.intent import Blocker, CostPreview, UIHints
from tangl.service.response import (
    BadgeListValue,
    DirectEdgeRequest,
    FindEdgeRequest,
    KvListValue,
    KvRow,
    ProjectedSection,
    ProjectedState,
    RuntimeEnvelope,
    UxEvent,
)


# This uses a test-app to focus on the StoryController


class RecordingCLI(cmd2.Cmd):
    def __init__(self) -> None:
        super().__init__(allow_cli_args=False, auto_load_commands=False)
        self.user_id = uuid4()
        self.ledger_id = uuid4()
        self.outputs: list[str] = []
        self.calls: list[tuple[str, dict[str, object]]] = []
        self.edge_id = uuid4()
        self.terminal_renderer = PlainTerminalRenderer()
        self.story_controller = StoryController()
        self.register_command_set(self.story_controller)

    def poutput(self, message: object, *, end: str = "\n", **_: object) -> None:  # noqa: ARG002
        self.outputs.append(str(message))

    def emit_terminal(self, renderables: list[object]) -> None:
        self.terminal_renderer.emit(self, renderables)

    def set_ledger(self, ledger_id: UUID | None) -> None:  # type: ignore[override]
        self.ledger_id = ledger_id

    def call_service(self, method_name: str, /, **params: object) -> object:
        self.calls.append((method_name, params))
        if method_name in {"create_story", "get_story_update"}:
            return RuntimeEnvelope(
                metadata={"ledger_id": str(self.ledger_id)},
                fragments=[
                    ContentFragment(content="start"),
                    ChoiceFragment(
                        edge_id=self.edge_id,
                        text="Go",
                    ),
                ],
            )
        if method_name == "resolve_choice":
            return RuntimeEnvelope(
                metadata={"ledger_id": str(self.ledger_id)},
                fragments=[ContentFragment(content="moved")],
            )
        if method_name == "get_story_info":
            return ProjectedState(
                sections=[
                    ProjectedSection(
                        section_id="session",
                        title="Session",
                        kind="stats",
                        value=KvListValue(
                            items=[
                                KvRow(key="Cursor", value="Dark Forest"),
                                KvRow(key="Step", value=0),
                            ]
                        ),
                    ),
                    ProjectedSection(
                        section_id="flags",
                        title="Flags",
                        kind="custom_metrics",
                        value=BadgeListValue(items=["torch_lit", "met_guide"]),
                    ),
                ]
            )
        if method_name == "drop_story":
            return {
                "status": "dropped",
                "dropped_ledger_id": str(self.ledger_id),
                "archived": bool(params.get("archive", False)),
                "persistence_deleted": not bool(params.get("archive", False)),
            }
        return {}


@pytest.fixture()
def story_controller() -> StoryController:
    cli = RecordingCLI()
    return cli.story_controller


def test_story_command_fetches_journal_and_choices(story_controller: StoryController) -> None:
    story_controller.do_story()
    cli = story_controller._cmd
    assert cli.calls[0][0] == "get_story_update"
    assert any("Choices:" in line for line in cli.outputs)


def test_do_command_resolves_choice(story_controller: StoryController) -> None:
    story_controller.do_story()
    story_controller.do_do("1")
    cli = story_controller._cmd
    resolve_calls = [call for call in cli.calls if call[0] == "resolve_choice"]
    assert resolve_calls
    _, params = resolve_calls[-1]
    assert params["request"] == DirectEdgeRequest(edge_id=cli.edge_id, payload={})


def test_command_text_submits_find_edge_request(story_controller: StoryController) -> None:
    story_controller.do_command("go north")
    cli = story_controller._cmd

    _, params = [call for call in cli.calls if call[0] == "resolve_choice"][-1]
    request = params["request"]

    assert isinstance(request, FindEdgeRequest)
    assert request.find_edge.command == "go north"


def test_cli_applies_runtime_envelope_dto_projection(
    story_controller: StoryController,
) -> None:
    cli = story_controller._cmd
    edge_id = uuid4()
    fragment_uid = uuid4()
    envelope = RuntimeEnvelope(
        metadata={"ledger_id": str(cli.ledger_id)},
        fragments=[
            ContentFragment(content="start", step=3),
            ChoiceFragment(
                uid=fragment_uid,
                edge_id=edge_id,
                text="Go north",
                step=3,
            ),
        ],
    )

    story_controller._apply_runtime_envelope(envelope)

    assert story_controller._current_story_update[0]["content"] == "start"
    assert "seq" not in story_controller._current_story_update[0]
    assert "step" not in story_controller._current_story_update[0]
    assert story_controller._current_story_update[1]["uid"] == str(fragment_uid)
    assert story_controller._current_choices[0].edge_id == edge_id
    assert story_controller._current_choices[0].label == "Go north"


def test_cli_preserves_choices_for_same_turn_guidance_envelope(
    story_controller: StoryController,
) -> None:
    cursor_id = uuid4()
    edge_id = uuid4()
    story_controller._apply_runtime_envelope(
        RuntimeEnvelope(
            cursor_id=cursor_id,
            step=3,
            fragments=[
                ContentFragment(content="start"),
                ChoiceFragment(edge_id=edge_id, text="Go north"),
            ],
        )
    )

    story_controller._apply_runtime_envelope(
        RuntimeEnvelope(
            cursor_id=cursor_id,
            step=3,
            fragments=[],
            ux_events=[
                UxEvent(
                    event_type="edge_not_found",
                    message="I couldn't match that command.",
                    severity="warning",
                )
            ],
        )
    )

    assert story_controller._current_story_update[0]["content"] == "start"
    assert story_controller._current_choices[0].edge_id == edge_id
    assert story_controller._current_ux_events[0]["event_type"] == "edge_not_found"


def test_cli_shows_locked_choices_with_reason(story_controller: StoryController) -> None:
    cli = story_controller._cmd
    story_controller._apply_runtime_envelope(
        RuntimeEnvelope(
            fragments=[
                ChoiceFragment(
                    edge_id=uuid4(),
                    text="Open vault",
                    available=False,
                    unavailable_reason="Requires keycard",
                    blockers=[
                        Blocker(
                            code="needs_keycard",
                            message="The security keycard is required.",
                        )
                    ],
                ),
                ChoiceFragment(
                    edge_id=uuid4(),
                    text="Go north",
                    ui_hints=UIHints(
                        cost_previews=[
                            CostPreview(ledger_key="time", delta=-1, unit="minute"),
                        ]
                    ),
                ),
            ]
        )
    )

    cli.outputs.clear()
    story_controller._render_current_story_update()

    output = "\n".join(cli.outputs)
    assert "1. Go north [cost: time -1 minute]" in output
    assert (
        "x) Open vault [locked: Requires keycard] "
        "[blockers: The security keycard is required.]"
        in output
    )


def test_cli_combines_action_and_input_cost_previews(
    story_controller: StoryController,
) -> None:
    cli = story_controller._cmd
    story_controller._apply_runtime_envelope(
        RuntimeEnvelope(
            fragments=[
                ChoiceFragment(
                    edge_id=cli.edge_id,
                    text="Buy rations",
                    accepts={
                        "kind": "quantity",
                        "min": 1,
                        "max": 3,
                        "cost_previews": [
                            {"ledger_key": "supplies", "delta": 1, "unit": "ration"},
                        ],
                    },
                    ui_hints={
                        "cost_previews": [
                            {"ledger_key": "purse", "delta": -2, "unit": "coin"},
                        ],
                    },
                )
            ]
        )
    )

    cli.outputs.clear()
    story_controller._render_current_story_update()

    assert (
        "1. Buy rations <quantity 1-3> "
        "[cost: purse -2 coin; supplies +1 ration]"
    ) in "\n".join(cli.outputs)


def test_do_command_submits_quantity_payload(story_controller: StoryController) -> None:
    cli = story_controller._cmd
    story_controller._apply_runtime_envelope(
        RuntimeEnvelope(
            fragments=[
                ChoiceFragment(
                    edge_id=cli.edge_id,
                    text="Take tokens",
                    accepts={"kind": "quantity", "min": 1, "max": 3},
                )
            ]
        )
    )

    story_controller.do_do("1 2")

    _, params = [call for call in cli.calls if call[0] == "resolve_choice"][-1]
    assert params["request"].payload == {"quantity": 2}


def test_do_command_submits_piece_payload(story_controller: StoryController) -> None:
    cli = story_controller._cmd
    story_controller._apply_runtime_envelope(
        RuntimeEnvelope(
            fragments=[
                PieceFragment(
                    piece_id="permit-7",
                    piece_kind="document",
                    content="Gate permit",
                ),
                ChoiceFragment(
                    edge_id=cli.edge_id,
                    text="Inspect a document",
                    accepts={"kind": "pieces", "min": 1, "max": 1},
                ),
            ]
        )
    )

    story_controller.do_do("1 permit-7")

    _, params = [call for call in cli.calls if call[0] == "resolve_choice"][-1]
    assert params["request"].payload == {"piece_ids": ["permit-7"]}


def test_do_command_rejects_invalid_quantity(story_controller: StoryController) -> None:
    cli = story_controller._cmd
    story_controller._apply_runtime_envelope(
        RuntimeEnvelope(
            fragments=[
                ChoiceFragment(
                    edge_id=cli.edge_id,
                    text="Take tokens",
                    accepts={"kind": "quantity", "min": 1, "max": 3},
                )
            ]
        )
    )
    calls_before = len(cli.calls)

    story_controller.do_do("1 4")

    assert len(cli.calls) == calls_before
    assert cli.outputs[-1] == "Quantity must be at most 3."


def test_do_command_accepts_explicit_compose_payload(
    story_controller: StoryController,
) -> None:
    cli = story_controller._cmd
    story_controller._apply_runtime_envelope(
        RuntimeEnvelope(
            fragments=[
                ChoiceFragment(
                    edge_id=cli.edge_id,
                    text="Give coins",
                    accepts={
                        "kind": "compose",
                        "parts": [
                            {
                                "role": "amount",
                                "accepts": {"kind": "quantity", "min": 1},
                            }
                        ],
                    },
                )
            ]
        )
    )

    story_controller.do_do("""1 --payload '{"parts":{"amount":{"quantity":2}}}'""")

    _, params = [call for call in cli.calls if call[0] == "resolve_choice"][-1]
    assert params["request"].payload == {"parts": {"amount": {"quantity": 2}}}


def test_drop_story_invokes_service_and_clears_context(story_controller: StoryController) -> None:
    cli = story_controller._cmd
    story_controller.do_story()
    cli.outputs.clear()

    story_controller.do_drop_story("--archive")

    drop_calls = [call for call in cli.calls if call[0] == "drop_story"]
    assert drop_calls
    _, params = drop_calls[-1]
    assert params["archive"] is True
    assert cli.ledger_id is None
    assert not story_controller._current_story_update
    assert not story_controller._current_choices
    assert not story_controller._current_ux_events
    assert not story_controller._current_metadata
    assert story_controller._current_cursor_id is None
    assert story_controller._current_step is None
    assert cli.outputs[0] == "Story dropped."
    assert cli.outputs[1].startswith("Dropped ledger:")
    assert cli.outputs[2] == "Archived: True"
    assert cli.outputs[3] == "Persistence deleted: False"


def test_status_renders_projected_sections_generically(story_controller: StoryController) -> None:
    cli = story_controller._cmd
    cli.outputs.clear()

    story_controller.do_status()

    output = "\n".join(cli.outputs)
    assert "Session:" in output
    assert "Cursor: Dark Forest" in output
    assert "Flags:" in output
    assert "torch_lit, met_guide" in output


def test_status_uses_projected_state_dto(
    story_controller: StoryController,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cli = story_controller._cmd
    state = ProjectedState(
        sections=[
            ProjectedSection(
                section_id="session",
                title="Session",
                kind="stats",
                value=KvListValue(items=[KvRow(key="Step", value=4)]),
            )
        ]
    )
    monkeypatch.setattr(cli, "call_service", lambda *_args, **_kwargs: state)
    cli.outputs.clear()

    story_controller.do_status()

    output = "\n".join(cli.outputs)
    assert "Session:" in output
    assert "Step: 4" in output
