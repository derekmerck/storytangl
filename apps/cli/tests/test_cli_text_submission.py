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
    ("do 1", TextAccepts(required=False), "", {}),
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
