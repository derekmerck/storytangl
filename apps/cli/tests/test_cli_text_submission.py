"""cmd2 commands reach the real JSON-backed authoritative text submission path."""

from __future__ import annotations

import io
import json
import shlex
from collections.abc import Iterator
from uuid import UUID

import pytest

from tangl.cli.app import StoryTanglCLI
from tangl.persistence.serializers import JsonSerializationHandler as Json
from tangl.presentation.intent import EnumValidator, LengthValidator, RegexValidator, TextAccepts
from tangl.story import World

from pytest_helpers.text_choice import text_choice_session


@pytest.fixture(autouse=True)
def clear_worlds() -> Iterator[None]:
    World.clear_instances()
    yield
    World.clear_instances()


def _cli(accepts: TextAccepts, *, available: bool = True) -> StoryTanglCLI:
    _world, manager, user, envelope = text_choice_session(
        accepts, payload={"operation": "rename", "kept": 3}, available=available,
    )
    app = StoryTanglCLI(
        service_manager=manager, user_id=user.uid,
        ledger_id=UUID(str(envelope.metadata["ledger_id"])),
    )
    app.stdout = io.StringIO()
    app.onecmd("story")
    app.stdout.seek(0)
    app.stdout.truncate()
    return app


@pytest.mark.parametrize(("command", "accepts", "answer", "extra"), [
    ("do 1 Dana Reyes", TextAccepts(), "Dana Reyes", {}),
    ("do 1   Dana    Reyes  ", TextAccepts(), "Dana Reyes", {}),
    ("do 1 --payload " + shlex.quote(json.dumps({"text": "  Dana  Reyes \t", "kept": 4})),
     TextAccepts(), "  Dana  Reyes \t", {"kept": 4}),
    ("do 1 --payload " + shlex.quote(json.dumps({"text": ""})),
     TextAccepts(required=False), "", {}),
])
def test_cli_text_submission_preserves_effective_payload_and_exact_json_string(
    command: str, accepts: TextAccepts, answer: str, extra: dict[str, object],
) -> None:
    app = _cli(accepts)
    app.onecmd(command)
    assert "Answer saved." in app.stdout.getvalue()
    with app.service_manager.open_session(user_id=app.user_id) as session:
        ledger = session.ledger
        assert ledger.cursor.label == "end"
        assert ledger.graph.locals["answer"] == answer
        assert ledger.graph.locals["activation"] == {
            "operation": "rename", "kept": 3, "text": answer, **extra,
        }
        assert ledger.graph.locals["effect_count"] == 1
        assert isinstance(app.persistence.storage[ledger.uid], str)


@pytest.mark.parametrize(("accepts", "value", "message"), [
    (TextAccepts(), " \t", "required"),
    (TextAccepts(validators=[LengthValidator(min=2, max=8)]), "x", "at least 2"),
    (TextAccepts(validators=[LengthValidator(min=2, max=8)]),
     "too long to be accepted", "at most 8"),
    (TextAccepts(validators=[RegexValidator(pattern="[0-9]", message="Need a digit")]),
     "Dana", "Need a digit"),
    (TextAccepts(validators=[EnumValidator(values=["Dana"])]), "Other", "one of"),
    (TextAccepts(), 123, "string"),
    (TextAccepts(required=False), None, "string"),
])
def test_cli_reports_backend_rejection_without_advancement_and_allows_retry(
    accepts: TextAccepts, value: object, message: str,
) -> None:
    app = _cli(accepts)
    with app.service_manager.open_session(user_id=app.user_id) as session:
        before = Json.serialize(session.ledger.unstructure())
    app.onecmd("do 1 --payload " + shlex.quote(json.dumps({"text": value})))
    assert message in app.stdout.getvalue()
    with app.service_manager.open_session(user_id=app.user_id) as session:
        assert Json.serialize(session.ledger.unstructure()) == before
    # Cached choice/number remain usable; a refused attempt is not a new turn.
    valid = "Dana1" if any(isinstance(v, RegexValidator) for v in accepts.validators) else "Dana"
    app.onecmd("do 1 " + valid)
    with app.service_manager.open_session(user_id=app.user_id) as session:
        assert session.ledger.cursor.label == "end"


def test_cli_unavailable_text_choice_does_not_advance() -> None:
    app = _cli(TextAccepts(), available=False)
    with app.service_manager.open_session(user_id=app.user_id) as session:
        before = Json.serialize(session.ledger.unstructure())
    app.onecmd("do 1 Dana Reyes")
    assert "not available" in app.stdout.getvalue()
    with app.service_manager.open_session(user_id=app.user_id) as session:
        assert Json.serialize(session.ledger.unstructure()) == before


def _typing(app: StoryTanglCLI, *lines: str) -> None:
    """Answer the CLI's prompts with these lines, then end the input."""
    app.use_rawinput = False
    app.echo = True
    app.stdin = io.StringIO("".join(f"{line}\n" for line in lines))


def _state(app: StoryTanglCLI) -> str:
    with app.service_manager.open_session(user_id=app.user_id) as session:
        return Json.serialize(session.ledger.unstructure())


@pytest.mark.parametrize(("accepts", "prompt", "typed"), [
    (TextAccepts(placeholder="Your name"), "Your name (blank cancels)> ", "  Dana  Reyes "),
    (TextAccepts(required=False), "Answer> ", ""),
])
def test_cli_asks_for_a_text_choices_text_and_submits_the_line_as_typed(
    accepts: TextAccepts, prompt: str, typed: str,
) -> None:
    # `do N` given no text asks for it, as pygame's text modal does. The line
    # is submitted exactly as typed; where text is optional, a blank line is
    # its empty answer.
    app = _cli(accepts)
    _typing(app, typed)
    app.onecmd("do 1")
    output = app.stdout.getvalue()
    assert f"{prompt}{typed}" in output and "Answer saved." in output
    with app.service_manager.open_session(user_id=app.user_id) as session:
        assert session.ledger.graph.locals["answer"] == typed
        assert session.ledger.graph.locals["effect_count"] == 1


def test_cli_asks_again_when_the_story_refuses_the_text() -> None:
    app = _cli(TextAccepts(validators=[LengthValidator(min=2, max=8)]))
    _typing(app, "x", "Dana")
    app.onecmd("do 1")
    output = app.stdout.getvalue()
    assert output.index("at least 2") < output.index("Answer saved.")
    with app.service_manager.open_session(user_id=app.user_id) as session:
        assert session.ledger.graph.locals["answer"] == "Dana"
        assert session.ledger.graph.locals["effect_count"] == 1


@pytest.mark.parametrize("cancel", ["blank line", "end of input", "ctrl-d"])
def test_cli_cancels_a_required_text_prompt_and_keeps_the_choice(
    cancel: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _cli(TextAccepts())
    before = _state(app)
    if cancel == "ctrl-d":
        def ctrl_d(_prompt: str) -> str:
            raise EOFError
        monkeypatch.setattr(app, "read_input", ctrl_d)
    else:
        _typing(app, *([""] if cancel == "blank line" else []))
    app.onecmd("do 1")
    assert "Cancelled." in app.stdout.getvalue()
    assert _state(app) == before
    monkeypatch.undo()
    app.onecmd("do 1 Dana")
    with app.service_manager.open_session(user_id=app.user_id) as session:
        assert session.ledger.cursor.label == "end"
