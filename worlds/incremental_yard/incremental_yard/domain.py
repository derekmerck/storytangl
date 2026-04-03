from __future__ import annotations

from uuid import UUID

from tangl.mechanics.games import BuildSpec, HasGame, IncrementalGame, IncrementalGameHandler, TaskSpec
from tangl.story import Block


class YardGame(IncrementalGame):
    """Deterministic incremental shell setup for the demo world."""

    starting_resources: dict[str, int] = {"scrap": 0}
    starting_workers: int = 1
    task_specs: dict[str, TaskSpec] = {
        "scavenge": TaskSpec(produces={"scrap": 1}),
    }
    build_specs: dict[str, BuildSpec] = {
        "signal_fire": BuildSpec(cost={"scrap": 1}, resource_gain={"prestige": 1}),
    }
    unlocked_tasks: list[str] = ["scavenge"]
    unlocked_builds: list[str] = ["signal_fire"]
    unlocked_promotions: list[str] = []
    victory_resources: dict[str, int] = {"prestige": 1}


class IncrementalYardBlock(HasGame, Block):
    """Story block hosting the incremental shell proof."""

    _game_class = YardGame
    _game_handler_class = IncrementalGameHandler


IncrementalYardBlock.model_rebuild(_types_namespace={"UUID": UUID})
