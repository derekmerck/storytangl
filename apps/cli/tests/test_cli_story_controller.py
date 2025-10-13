from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
import cmd2

from tangl.cli.controllers.story_controller import StoryController

# This uses a test-app to focus on the StoryController

class RecordingCLI(cmd2.Cmd):
    def __init__(self) -> None:
        super().__init__(allow_cli_args=False, auto_load_commands=False)
        self.user_id = uuid4()
        self.ledger_id = uuid4()
        self.outputs: list[str] = []
        self.calls: list[tuple[str, dict[str, object]]] = []
        self.choice_id = uuid4()
        self.story_controller = StoryController()
        self.register_command_set(self.story_controller)

    def poutput(self, message: object, *, end: str = "\n", **_: object) -> None:
        self.outputs.append(str(message))

    def call_endpoint(self, endpoint: str, /, **params: object) -> object:
        self.calls.append((endpoint, params))
        if endpoint.endswith("get_journal_entries"):
            return [SimpleNamespace(content="start")]
        if endpoint.endswith("get_available_choices"):
            return [{"uid": self.choice_id, "label": "Go"}]
        if endpoint.endswith("resolve_choice"):
            return {"fragments": [SimpleNamespace(content="moved")]} 
        if endpoint.endswith("get_story_info"):
            return {"title": "demo", "cursor_id": uuid4(), "step": 0, "journal_size": 1}
        return {}


@pytest.fixture()
def story_controller() -> StoryController:
    cli = RecordingCLI()
    return cli.story_controller

def test_story_command_fetches_journal_and_choices(story_controller: StoryController) -> None:
    story_controller.do_story()
    cli = story_controller._cmd
    assert cli.calls[0][0].endswith("get_journal_entries")
    assert cli.calls[1][0].endswith("get_available_choices")
    assert any("Choices:" in line for line in cli.outputs)


def test_do_command_resolves_choice(story_controller: StoryController) -> None:
    story_controller.do_story()
    story_controller.do_do("1")
    cli = story_controller._cmd
    resolve_calls = [call for call in cli.calls if call[0].endswith("resolve_choice")]
    assert resolve_calls
    _, params = resolve_calls[-1]
    assert params["choice_id"] == cli.choice_id
