from __future__ import annotations

from uuid import UUID

from tangl.mechanics.games import HasGame
from tangl.mechanics.simulation import QueueSimulation, QueueSimulationHandler, QueueStationSpec
from tangl.story import Block


class EdQueueSimulation(QueueSimulation):
    """Deterministic ED queue configuration for the demo world."""

    patient_arrivals: dict[str, int] = {
        "P1": 0,
        "P2": 2,
        "P3": 4,
        "P4": 8,
    }
    station_specs: dict[str, QueueStationSpec] = {
        "triage": QueueStationSpec(capacity=1, service_turns=3, next_station="imaging"),
        "imaging": QueueStationSpec(capacity=1, service_turns=5, next_station="disposition"),
        "disposition": QueueStationSpec(capacity=1, service_turns=2, next_station=None),
    }
    entry_station: str = "triage"


class EdQueueBlock(HasGame, Block):
    """Story block hosting the ED queueing simulation."""

    _game_class = EdQueueSimulation
    _game_handler_class = QueueSimulationHandler


EdQueueBlock.model_rebuild(_types_namespace={"UUID": UUID})
