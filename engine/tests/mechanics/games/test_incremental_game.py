"""Tests for the incremental shell kernel."""

from __future__ import annotations

from tangl.core import Graph
from tangl.mechanics.games import BuildSpec, HasGame, IncrementalGame, IncrementalGameHandler, PromotionSpec, TaskSpec
from tangl.mechanics.games.incremental_game import IncrementalMove
from tangl.mechanics.games.handlers import inject_game_context, provision_game_moves
from tangl.story import Action, Block
from tangl.vm import Frame, Ledger, TraversableEdge as ChoiceEdge


class IncrementalBlock(HasGame, Block):
    """Test block embedding an incremental shell."""

    _game_class = IncrementalGame
    _game_handler_class = IncrementalGameHandler


def _sample_game(**kwargs) -> IncrementalGame:
    config = {
        "starting_resources": {"food": 1, "scrap": 0},
        "starting_workers": 1,
        "task_specs": {
            "forage": TaskSpec(produces={"food": 1}),
            "scavenge": TaskSpec(produces={"scrap": 1}),
        },
        "build_specs": {
            "workshop": BuildSpec(cost={"food": 1}, unlock_builds=["forge"]),
            "forge": BuildSpec(cost={"scrap": 1}, resource_gain={"prestige": 1}),
            "barracks": BuildSpec(cost={"food": 1}, infrastructure_gain={"barracks": 1}),
        },
        "promotion_specs": {
            "guard": PromotionSpec(
                cost={"food": 1},
                output={"rock": 1},
                requires_infrastructure={"barracks": 1},
            )
        },
        "upkeep": {"food": 0},
        "victory_resources": {"prestige": 1},
        "unlocked_tasks": ["forage", "scavenge"],
        "unlocked_builds": ["workshop", "barracks"],
        "unlocked_promotions": ["guard"],
    }
    config.update(kwargs)
    game = IncrementalGame(
        **config,
    )
    return game


class TestIncrementalCore:
    """Core shell behavior tests."""

    def test_assignment_persists_across_end_cycle(self) -> None:
        game = _sample_game()
        handler = IncrementalGameHandler()
        handler.setup(game)

        handler.receive_move(game, IncrementalMove(kind="assign", target="forage"))
        result = handler.receive_move(game, IncrementalMove(kind="end_cycle"))

        assert result.name == "CONTINUE"
        assert game.cycle == 1
        assert game.task_assignments["forage"] == 1
        assert game.resources["food"] == 2

    def test_upkeep_failure_can_lose_the_shell(self) -> None:
        game = _sample_game(starting_resources={"food": 0}, upkeep={"food": 1})
        handler = IncrementalGameHandler()
        handler.setup(game)

        result = handler.receive_move(game, IncrementalMove(kind="end_cycle"))

        assert result.name == "LOSE"
        assert game.result.name == "LOSE"

    def test_build_unlocks_follow_on_build_option(self) -> None:
        game = _sample_game()
        handler = IncrementalGameHandler()
        handler.setup(game)

        handler.receive_move(game, IncrementalMove(kind="build", target="workshop"))

        assert "forge" in game.unlocked_builds

    def test_promotion_respects_infrastructure_gate(self) -> None:
        game = _sample_game(starting_resources={"food": 2, "scrap": 0})
        handler = IncrementalGameHandler()
        handler.setup(game)

        before = handler.get_available_moves(game)
        assert IncrementalMove(kind="promote", target="guard") not in before

        handler.receive_move(game, IncrementalMove(kind="build", target="barracks"))
        after = handler.get_available_moves(game)

        assert IncrementalMove(kind="promote", target="guard") in after

    def test_pending_rewards_are_consumed_on_cycle_resolution(self) -> None:
        game = _sample_game(starting_resources={"food": 0})
        handler = IncrementalGameHandler()
        handler.setup(game)
        game.pending_rewards = {"food": 1}

        handler.receive_move(game, IncrementalMove(kind="end_cycle"))

        assert game.resources["food"] == 1
        assert game.pending_rewards == {}


class TestIncrementalIntegration:
    """VM and HasGame integration tests for the incremental shell."""

    def test_move_labels_cover_assign_build_and_cycle(self) -> None:
        graph = Graph(label="incremental_labels")
        block = graph.add_node(kind=IncrementalBlock, label="yard")
        block._game = _sample_game()
        block.game_handler.setup(block.game)

        frame = Frame(graph=graph, cursor=block)
        ctx = frame._make_ctx()
        object.__setattr__(ctx, "_frame", frame)

        actions = provision_game_moves(block, ctx=ctx)
        labels = [action.label for action in actions]

        assert "Assign 1 worker to forage" in labels
        assert "Build workshop" in labels
        assert "End cycle" in labels

    def test_incremental_shell_can_cycle_then_build_to_victory(self) -> None:
        graph = Graph(label="incremental_flow")
        intro = graph.add_node(kind=Block, label="intro")
        victory = graph.add_node(kind=Block, label="victory")
        defeat = graph.add_node(kind=Block, label="defeat")

        block = IncrementalBlock.create_game_block(
            graph=graph,
            game_class=IncrementalGame,
            handler_class=IncrementalGameHandler,
            victory_dest=victory,
            defeat_dest=defeat,
            label="yard",
        )
        block._game = _sample_game(
            starting_resources={"food": 0, "scrap": 0},
            build_specs={"signal_fire": BuildSpec(cost={"scrap": 1}, resource_gain={"prestige": 1})},
            unlocked_tasks=["scavenge"],
            unlocked_builds=["signal_fire"],
            unlocked_promotions=[],
            victory_resources={"prestige": 1},
        )
        block.game_handler.setup(block.game)

        intro_to_yard = ChoiceEdge(
            graph=graph,
            predecessor_id=intro.uid,
            successor_id=block.uid,
            label="Run the yard",
        )

        ledger = Ledger.from_graph(graph=graph, entry_id=intro.uid)
        ledger.resolve_choice(intro_to_yard.uid)

        assign = next(
            action
            for action in ledger.cursor.edges_out()
            if isinstance(action, Action) and action.label == "Assign 1 worker to scavenge"
        )
        ledger.resolve_choice(assign.uid, choice_payload=assign.payload)

        end_cycle = next(
            action
            for action in ledger.cursor.edges_out()
            if isinstance(action, Action) and action.label == "End cycle"
        )
        ledger.resolve_choice(end_cycle.uid, choice_payload=end_cycle.payload)

        build = next(
            action
            for action in ledger.cursor.edges_out()
            if isinstance(action, Action) and action.label == "Build signal_fire"
        )
        ledger.resolve_choice(build.uid, choice_payload=build.payload)

        assert ledger.cursor_id == victory.uid
        content = " ".join(getattr(fragment, "content", "") for fragment in ledger.get_journal())
        assert "you build signal_fire" in content.lower()

    def test_context_exports_shell_state(self) -> None:
        graph = Graph(label="incremental_context")
        block = graph.add_node(kind=IncrementalBlock, label="yard")
        block._game = _sample_game()
        block.game_handler.setup(block.game)

        frame = Frame(graph=graph, cursor=block)
        ctx = frame._make_ctx()
        object.__setattr__(ctx, "_frame", frame)

        namespace = inject_game_context(block, ctx=ctx)

        assert namespace["incremental_worker_pool"] == 1
        assert "forage" in namespace["incremental_unlocked_tasks"]
