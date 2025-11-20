from __future__ import annotations
from types import SimpleNamespace
from pathlib import Path
from uuid import UUID, uuid4

import pytest
import yaml

from tangl.core import StreamRegistry
from tangl.journal.content import ContentFragment
from tangl.service.controllers.runtime_controller import RuntimeController
from tangl.service.user.user import User
from tangl.story.episode import Action, Block
from tangl.story.story_graph import StoryGraph
from tangl.story.fabula.script_manager import ScriptManager
from tangl.story.fabula.world import World
from tangl.vm import ChoiceEdge, Frame, Ledger, ResolutionPhase

from helpers.fragment_helpers import extract_all_choices


@pytest.fixture()
def runtime_controller() -> RuntimeController:
    return RuntimeController()


@pytest.fixture()
def ledger() -> Ledger:
    graph = StoryGraph(label="demo")
    start = graph.add_node(obj_cls=Block, label="start")
    ledger = Ledger(graph=graph, cursor_id=start.uid, records=StreamRegistry())
    ledger.push_snapshot()
    return ledger


@pytest.fixture()
def demo_world() -> World:
    World.clear_instances()
    script_path = (
        Path(__file__).resolve().parents[2] / "resources" / "demo_script.yaml"
    )
    data = yaml.safe_load(script_path.read_text())
    script_manager = ScriptManager.from_data(data)
    world = World(label="demo_world", script_manager=script_manager)
    yield world
    World.clear_instances()


@pytest.fixture()
def user_with_ledger(ledger: Ledger) -> User:
    user = User(uid=uuid4())
    user.current_ledger_id = ledger.uid
    return user


def _register_journal_handler(frame: Frame) -> None:
    @frame.local_behaviors.register(task=ResolutionPhase.JOURNAL)
    def _journal_handler(*_, ctx, **__) -> list[ContentFragment]:  # type: ignore[override]
        return [ContentFragment(content=f"sp:cursor:{ctx.cursor.label}")]

    frame._invalidate_context()


def test_get_journal_entries_limits_results(runtime_controller: RuntimeController, ledger: Ledger) -> None:
    ledger.records.push_records(
        ContentFragment(content="first"),
        marker_type="journal",
        marker_name="entry-0001",
    )
    ledger.records.push_records(
        ContentFragment(content="second"),
        marker_type="journal",
        marker_name="entry-0002",
    )

    result = runtime_controller.get_journal_entries(
        ledger, limit=1, current_only=False
    )
    assert [fragment.content for fragment in result] == ["second"]


def test_get_journal_entries_defaults_to_latest_step(runtime_controller: RuntimeController, ledger: Ledger) -> None:
    ledger.records.push_records(
        ContentFragment(content="[step 0001]: cursor at start"),
        ContentFragment(content="choice one"),
        marker_type="journal",
        marker_name="step-0001",
    )
    ledger.records.push_records(
        ContentFragment(content="[step 0002]: cursor at end"),
        ContentFragment(content="choice two"),
        ContentFragment(content="choice three"),
        marker_type="journal",
        marker_name="step-0002",
    )

    result = runtime_controller.get_journal_entries(ledger, limit=1)

    assert [fragment.content for fragment in result] == [
        "[step 0002]: cursor at end",
        "choice two",
        "choice three",
    ]


def test_get_journal_entries_supports_marker_range(
    runtime_controller: RuntimeController, ledger: Ledger
) -> None:
    ledger.records.push_records(
        ContentFragment(content="[step 0001]: cursor at start"),
        ContentFragment(content="choice one"),
        marker_type="journal",
        marker_name="step-0001",
    )
    ledger.records.push_records(
        ContentFragment(content="[step 0002]: cursor at middle"),
        ContentFragment(content="choice two"),
        marker_type="journal",
        marker_name="step-0002",
    )
    ledger.records.push_records(
        ContentFragment(content="[step 0003]: cursor at end"),
        ContentFragment(content="choice three"),
        marker_type="journal",
        marker_name="step-0003",
    )

    result = runtime_controller.get_journal_entries(
        ledger, start_marker="step-0002", end_marker="step-0003"
    )

    assert [fragment.content for fragment in result] == [
        "[step 0002]: cursor at middle",
        "choice two",
    ]


def test_get_journal_entries_only_returns_latest_step(
    runtime_controller: RuntimeController, ledger: Ledger
) -> None:
    ledger.records.push_records(
        ContentFragment(content="[step 0001]: cursor at start"),
        marker_type="journal",
        marker_name="entry-0001",
    )
    ledger.records.push_records(
        ContentFragment(content="choice one"),
        marker_type="journal",
        marker_name="entry-0001a",
    )
    ledger.records.push_records(
        ContentFragment(content="[step 0002]: cursor at end"),
        marker_type="journal",
        marker_name="entry-0002",
    )
    ledger.records.push_records(
        ContentFragment(content="final choice"),
        marker_type="journal",
        marker_name="entry-0002a",
    )

    result = runtime_controller.get_journal_entries(ledger, limit=0, current_only=True)

    assert [fragment.content for fragment in result] == [
        "[step 0002]: cursor at end",
        "final choice",
    ]

# todo: _what_ is this testing??
def test_resolve_choice_returns_status_not_fragments(
    runtime_controller: RuntimeController,
    ledger: Ledger,
) -> None:
    graph = ledger.graph
    start = graph.get(ledger.cursor_id)
    end = graph.add_node(label="end")
    choice = ChoiceEdge(graph=graph, source_id=start.uid, destination_id=end.uid, label="choice")
    frame = ledger.get_frame()
    _register_journal_handler(frame)

    result = runtime_controller.resolve_choice(
        ledger=ledger,
        frame=frame,
        choice_id=choice.uid,
    )

    assert result["status"] == "resolved"
    assert result["cursor_id"] == str(end.uid)
    assert result["step"] == ledger.step == frame.step
    assert "fragments" not in result

    fragments = runtime_controller.get_journal_entries(ledger, limit=1)
    assert fragments and "sp:cursor:end" in [f.content for f in fragments]


def test_only_get_journal_returns_fragments(
    runtime_controller: RuntimeController,
    ledger: Ledger,
) -> None:
    graph = ledger.graph
    start = graph.get(ledger.cursor_id)
    end = graph.add_node(label="end")
    choice = ChoiceEdge(graph=graph, source_id=start.uid, destination_id=end.uid, label="choice")
    frame = ledger.get_frame()
    _register_journal_handler(frame)

    result = runtime_controller.resolve_choice(ledger=ledger, frame=frame, choice_id=choice.uid)

    fragments = runtime_controller.get_journal_entries(ledger=ledger, limit=1)
    assert fragments
    assert all(hasattr(fragment, "content") for fragment in fragments)

    assert "fragments" not in result


def test_jump_to_node_teleports_cursor(
    runtime_controller: RuntimeController,
    ledger: Ledger,
) -> None:
    graph = ledger.graph
    target = graph.add_node(label="target")

    result = runtime_controller.jump_to_node(ledger=ledger, node_id=target.uid)

    assert result["status"] == "jumped"
    assert result["cursor_id"] == str(target.uid)
    assert ledger.cursor_id == target.uid
    assert ledger.step == result["step"]


def test_jump_to_node_marks_destination_dirty(
    runtime_controller: RuntimeController,
    ledger: Ledger,
) -> None:
    graph = ledger.graph
    target = graph.add_node(label="target")

    runtime_controller.jump_to_node(ledger=ledger, node_id=target.uid)

    target_node = ledger.graph.get(target.uid)
    assert target_node is not None and target_node.has_tags("dirty")


def test_jump_to_node_with_invalid_node_raises(
    runtime_controller: RuntimeController,
    ledger: Ledger,
) -> None:
    with pytest.raises(ValueError, match="not found"):
        runtime_controller.jump_to_node(ledger=ledger, node_id=uuid4())


def test_jump_to_node_follows_postreq_redirects(
    runtime_controller: RuntimeController,
    ledger: Ledger,
) -> None:
    graph = ledger.graph
    jump_target = graph.add_node(label="jump_target")
    final_dest = graph.add_node(label="final_dest")

    ChoiceEdge(
        graph=graph,
        source_id=jump_target.uid,
        destination_id=final_dest.uid,
        trigger_phase=ResolutionPhase.POSTREQS,
    )

    runtime_controller.jump_to_node(ledger=ledger, node_id=jump_target.uid)

    assert ledger.cursor_id == final_dest.uid


def test_jump_to_node_returns_status_not_fragments(
    runtime_controller: RuntimeController,
    ledger: Ledger,
) -> None:
    graph = ledger.graph
    target = graph.add_node(label="target")

    result = runtime_controller.jump_to_node(ledger=ledger, node_id=target.uid)

    assert "fragments" not in result
    assert result["status"] == "jumped"


def test_get_story_info_reports_metadata(runtime_controller: RuntimeController, ledger: Ledger) -> None:
    info = runtime_controller.get_story_info(ledger)
    assert info["cursor_id"] == ledger.cursor_id
    assert info["journal_size"] == 0
    assert info["title"] == ledger.graph.label


def test_choices_come_from_journal_stream(
    runtime_controller: RuntimeController, ledger: Ledger
) -> None:
    graph = ledger.graph
    start = graph.get(ledger.cursor_id)
    end = graph.add_node(obj_cls=Block, label="end")
    Action(graph=graph, source_id=start.uid, destination_id=end.uid, label="go")

    frame = ledger.get_frame()
    fragments = frame.run_phase(ResolutionPhase.JOURNAL)
    ledger.records.push_records(*fragments, marker_type="fragment")

    fragments = runtime_controller.get_journal_entries(ledger, limit=10)
    choice_fragments = extract_all_choices(fragments)

    assert len(choice_fragments) == 1
    assert choice_fragments[0].content == "go"
    assert choice_fragments[0].active is True


def test_get_journal_entries_rejects_negative_limit(
    runtime_controller: RuntimeController,
    ledger: Ledger,
) -> None:
    with pytest.raises(ValueError):
        runtime_controller.get_journal_entries(ledger, limit=-1)


def test_resolve_choice_requires_choice(
    runtime_controller: RuntimeController,
    ledger: Ledger,
) -> None:
    frame = ledger.get_frame()
    with pytest.raises(ValueError, match="Choice"):
        runtime_controller.resolve_choice(ledger=ledger, frame=frame, choice_id=uuid4())


def test_create_story_materializes_ledger(
    runtime_controller: RuntimeController,
    demo_world: World,
) -> None:
    user = User(label="player")

    result = runtime_controller.create_story(user=user, world_id=demo_world.label)

    ledger_id = UUID(result["ledger_id"])
    assert result["status"] == "created"
    assert user.current_ledger_id == ledger_id
    assert result["world_id"] == demo_world.label
    assert result["title"].startswith("story_")
    assert result["cursor_label"]
    assert result["step"] >= 1

    ledger_obj = result.get("ledger")
    assert isinstance(ledger_obj, Ledger)
    assert ledger_obj.uid == ledger_id
    assert ledger_obj.step >= 1
    assert list(ledger_obj.records.iter_channel("fragment"))


def test_create_story_handles_prereq_redirects(
    runtime_controller: RuntimeController,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _create_redirect_story(_: str, **__) -> StoryGraph:
        graph = StoryGraph(label="redirect_story")
        start = graph.add_node(label="start")
        forced = graph.add_node(label="redirected_destination")
        ChoiceEdge(
            graph=graph,
            source_id=start.uid,
            destination_id=forced.uid,
            trigger_phase=ResolutionPhase.PREREQS,
        )
        graph.initial_cursor_id = start.uid
        return graph

    stub_world = SimpleNamespace(label="stub_world", create_story=_create_redirect_story)

    monkeypatch.setattr(World, "get_instance", lambda _: stub_world)

    user = User(label="player")
    result = runtime_controller.create_story(user=user, world_id="stub_world")

    ledger_obj = result["ledger"]
    cursor_node = ledger_obj.graph.get(ledger_obj.cursor_id)
    assert cursor_node is not None
    assert cursor_node.label == "redirected_destination"
    assert ledger_obj.step >= 1



def test_drop_story_clears_active_ledger(
    runtime_controller: RuntimeController,
    ledger: Ledger,
    user_with_ledger: User,
) -> None:
    result = runtime_controller.drop_story(user=user_with_ledger, ledger=ledger)

    assert user_with_ledger.current_ledger_id is None
    assert result["status"] == "dropped"
    assert result["archived"] is False
    assert result["dropped_ledger_id"] == str(ledger.uid)
    assert result["_delete_ledger_id"] == str(ledger.uid)


def test_drop_story_archive_skips_deletion_marker(
    runtime_controller: RuntimeController,
    ledger: Ledger,
    user_with_ledger: User,
) -> None:
    result = runtime_controller.drop_story(user=user_with_ledger, ledger=ledger, archive=True)

    assert result["archived"] is True
    assert "_delete_ledger_id" not in result


def test_drop_story_without_active_story_raises(runtime_controller: RuntimeController) -> None:
    user = User(uid=uuid4())

    with pytest.raises(ValueError, match="no active story"):
        runtime_controller.drop_story(user=user)
