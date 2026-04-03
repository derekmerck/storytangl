from __future__ import annotations

from uuid import UUID

from tangl.core import Priority, Selector
from tangl.mechanics.games import (
    BagRpsGame,
    BagRpsGameHandler,
    BuildSpec,
    GamePhase,
    GameResult,
    HasGame,
    IncrementalGame,
    IncrementalGameHandler,
    PromotionSpec,
    TaskSpec,
)
from tangl.story import Block
from tangl.vm import on_prereqs


FORCE_TYPES = ("rock", "paper", "scissors")


class ColonyShellGame(IncrementalGame):
    """Outer incremental shell for the colony composite proof."""

    starting_resources: dict[str, int] = {"food": 1, "rock": 1}
    starting_workers: int = 1
    task_specs: dict[str, TaskSpec] = {
        "forage": TaskSpec(produces={"food": 1}),
    }
    build_specs: dict[str, BuildSpec] = {
        "tribute_store": BuildSpec(cost={"scrap": 2}, resource_gain={"prestige": 1}),
    }
    promotion_specs: dict[str, PromotionSpec] = {
        "guard": PromotionSpec(cost={"food": 1}, output={"rock": 1}),
    }
    upkeep: dict[str, int] = {"food": 1}
    unlocked_tasks: list[str] = ["forage"]
    unlocked_builds: list[str] = []
    unlocked_promotions: list[str] = ["guard"]


class ColonyContestGame(BagRpsGame):
    """Inner Bag-RPS spike for the colony proof."""

    opponent_opening_reserve: dict[str, int] = {"paper": 1}
    max_commit_size: int = 2
    opponent_strategy: str = "aggregate_force_greedy"


class ColonyShellBlock(HasGame, Block):
    """Outer shell block."""

    _game_class = ColonyShellGame
    _game_handler_class = IncrementalGameHandler


class ColonyContestBlock(HasGame, Block):
    """Inner contest spike block."""

    _game_class = ColonyContestGame
    _game_handler_class = BagRpsGameHandler


class ColonyVictoryAftermathBlock(Block):
    """Victory aftermath block for the raid."""


class ColonyDefeatAftermathBlock(Block):
    """Defeat aftermath block for the raid."""


class ColonyDrawAftermathBlock(Block):
    """Draw aftermath block for the raid."""


def _find_shell(graph) -> ColonyShellBlock:
    shell = graph.find_one(Selector(has_kind=ColonyShellBlock))
    assert isinstance(shell, ColonyShellBlock)
    return shell


def _find_contest(graph) -> ColonyContestBlock:
    contest = graph.find_one(Selector(has_kind=ColonyContestBlock))
    assert isinstance(contest, ColonyContestBlock)
    return contest


def _force_profile_from_resources(resources: dict[str, int]) -> dict[str, int]:
    return {label: max(resources.get(label, 0), 0) for label in FORCE_TYPES}


def _write_back_force(shell: ColonyShellBlock, contest: ColonyContestBlock) -> None:
    for label in FORCE_TYPES:
        shell.game.resources[label] = contest.game.player_reserve.get(label, 0)


@on_prereqs(
    wants_caller_kind=ColonyContestBlock,
    wants_exact_kind=False,
    priority=Priority.FIRST,
)
def prepare_colony_contest(*, caller, ctx, **_kw):
    """Snapshot shell force into the contest spike before setup."""

    if not isinstance(caller, ColonyContestBlock):
        return None

    shell = _find_shell(caller.graph)
    caller.game.player_opening_reserve = _force_profile_from_resources(shell.game.resources)
    caller.locals["shell_id"] = shell.uid
    return None


@on_prereqs(
    wants_caller_kind=ColonyVictoryAftermathBlock,
    wants_exact_kind=False,
    priority=Priority.FIRST,
)
def apply_colony_victory_aftermath(*, caller, ctx, **_kw):
    """Write contest victory back into the shell."""

    if not isinstance(caller, ColonyVictoryAftermathBlock):
        return None
    if caller.locals.get("aftermath_applied"):
        return None

    shell = _find_shell(caller.graph)
    contest = _find_contest(caller.graph)
    _write_back_force(shell, contest)
    shell.game.resources["scrap"] = shell.game.resources.get("scrap", 0) + 2
    if "tribute_store" not in shell.game.unlocked_builds:
        shell.game.unlocked_builds.append("tribute_store")
    shell.locals["tribute_active"] = True
    shell.locals["rival_defeated"] = True
    shell.game.score["player"] = 1
    shell.game.result = GameResult.WIN
    shell.game.phase = GamePhase.READY
    caller.locals["aftermath_applied"] = True
    return None


@on_prereqs(
    wants_caller_kind=ColonyDefeatAftermathBlock,
    wants_exact_kind=False,
    priority=Priority.FIRST,
)
def apply_colony_defeat_aftermath(*, caller, ctx, **_kw):
    """Write contest defeat back into the shell."""

    if not isinstance(caller, ColonyDefeatAftermathBlock):
        return None
    if caller.locals.get("aftermath_applied"):
        return None

    shell = _find_shell(caller.graph)
    contest = _find_contest(caller.graph)
    _write_back_force(shell, contest)
    shell.game.score["opponent"] = 1
    shell.game.result = GameResult.LOSE
    shell.game.phase = GamePhase.READY
    caller.locals["aftermath_applied"] = True
    return None


@on_prereqs(
    wants_caller_kind=ColonyDrawAftermathBlock,
    wants_exact_kind=False,
    priority=Priority.FIRST,
)
def apply_colony_draw_aftermath(*, caller, ctx, **_kw):
    """Write contest draw attrition back into the shell without ending it."""

    if not isinstance(caller, ColonyDrawAftermathBlock):
        return None
    if caller.locals.get("aftermath_applied"):
        return None

    shell = _find_shell(caller.graph)
    contest = _find_contest(caller.graph)
    _write_back_force(shell, contest)
    caller.locals["aftermath_applied"] = True
    return None


ColonyShellBlock.model_rebuild(_types_namespace={"UUID": UUID})
ColonyContestBlock.model_rebuild(_types_namespace={"UUID": UUID})
ColonyVictoryAftermathBlock.model_rebuild(_types_namespace={"UUID": UUID})
ColonyDefeatAftermathBlock.model_rebuild(_types_namespace={"UUID": UUID})
ColonyDrawAftermathBlock.model_rebuild(_types_namespace={"UUID": UUID})
