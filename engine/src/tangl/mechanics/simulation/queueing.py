"""Deterministic queueing simulation kernel."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Any, ClassVar

from pydantic import Field

from tangl.core.bases import BaseModelPlus
from tangl.journal.fragments import ContentFragment
from tangl.mechanics.games import Game, GameHandler
from tangl.mechanics.games.enums import GameResult, RoundResult
from tangl.mechanics.sandbox.time import advance_world_turn_to

from .calendar import EventCalendar, SimulationEvent


@dataclass(frozen=True)
class QueueMove:
    """Move requested by the queueing simulation block."""

    kind: str


class QueueStationSpec(BaseModelPlus):
    """Static service-station configuration."""

    capacity: int = 1
    service_turns: int = 1
    next_station: str | None = None


class QueuePatient(BaseModelPlus):
    """One job moving through the queueing network."""

    label: str
    arrival_turn: int
    current_station: str | None = None
    completed: bool = False
    completion_turn: int | None = None
    queued_at: dict[str, int] = Field(default_factory=dict)
    service_start: dict[str, int] = Field(default_factory=dict)
    service_end: dict[str, int] = Field(default_factory=dict)
    wait_turns: dict[str, int] = Field(default_factory=dict)

    def total_wait(self) -> int:
        """Return total time spent waiting across all stations."""
        return sum(self.wait_turns.values())

    def length_of_stay(self) -> int | None:
        """Return arrival-to-completion duration when complete."""
        if self.completion_turn is None:
            return None
        return self.completion_turn - self.arrival_turn


class QueueStationState(BaseModelPlus):
    """Mutable service-station state."""

    label: str
    capacity: int = 1
    service_turns: int = 1
    next_station: str | None = None
    queue: list[str] = Field(default_factory=list)
    in_service: list[str] = Field(default_factory=list)
    busy_turns: int = 0
    max_queue_length: int = 0
    started_count: int = 0
    completed_count: int = 0


class QueueTraceEvent(BaseModelPlus):
    """One observed fact from a queueing run."""

    turn: int
    kind: str
    text: str
    patient: str | None = None
    station: str | None = None


class QueueMetrics(BaseModelPlus):
    """Simple one-run queueing metrics."""

    completed_count: int = 0
    completed_turn: int = 0
    mean_length_of_stay: float = 0.0
    mean_wait: float = 0.0
    utilization: dict[str, float] = Field(default_factory=dict)
    bottleneck: str = ""


class QueueSimulation(Game[QueueMove]):
    """Deterministic single-run queueing simulation."""

    scoring_strategy: str = "single_round"
    opponent_strategy: str | None = None

    patient_arrivals: dict[str, int] = Field(default_factory=dict)
    station_specs: dict[str, QueueStationSpec] = Field(default_factory=dict)
    entry_station: str = "triage"
    projection_mode: str = "log"

    locals: dict[str, Any] = Field(
        default_factory=dict,
        json_schema_extra={"reset_field": True},
    )
    calendar: EventCalendar = Field(
        default_factory=EventCalendar,
        json_schema_extra={"reset_field": True},
    )
    patients: dict[str, QueuePatient] = Field(
        default_factory=dict,
        json_schema_extra={"reset_field": True},
    )
    stations: dict[str, QueueStationState] = Field(
        default_factory=dict,
        json_schema_extra={"reset_field": True},
    )
    completed: list[str] = Field(
        default_factory=list,
        json_schema_extra={"reset_field": True},
    )
    trace: list[QueueTraceEvent] = Field(
        default_factory=list,
        json_schema_extra={"reset_field": True},
    )
    latest_trace: list[QueueTraceEvent] = Field(
        default_factory=list,
        json_schema_extra={"reset_field": True},
    )
    metrics: QueueMetrics | None = Field(
        default=None,
        json_schema_extra={"reset_field": True},
    )

    def to_namespace(self) -> dict[str, object]:
        """Expose simulation facts to ordinary predicate evaluation."""
        namespace = super().to_namespace()
        namespace.update(
            {
                "simulation_turn": int(self.locals.get("world_turn", 0)),
                "queue_completed_count": len(self.completed),
                "queue_bottleneck": self.metrics.bottleneck if self.metrics else "",
                "queue_metrics": self.metrics,
            }
        )
        return namespace


class QueueSimulationHandler(GameHandler[QueueSimulation]):
    """Stateless rules for deterministic queueing simulations."""

    game_cls: ClassVar[type[Game]] = QueueSimulation

    def on_setup(self, game: QueueSimulation) -> None:
        game.locals["world_turn"] = 0
        game.calendar = EventCalendar()
        game.patients = {
            label: QueuePatient(label=label, arrival_turn=arrival_turn)
            for label, arrival_turn in sorted(
                game.patient_arrivals.items(),
                key=lambda item: item[1],
            )
        }
        game.stations = {
            label: QueueStationState(
                label=label,
                capacity=spec.capacity,
                service_turns=spec.service_turns,
                next_station=spec.next_station,
            )
            for label, spec in game.station_specs.items()
        }
        game.completed = []
        game.trace = []
        game.latest_trace = []
        game.metrics = None
        for patient in game.patients.values():
            game.calendar.push(
                SimulationEvent(
                    label=f"arrival_{patient.label}",
                    at_turn=patient.arrival_turn,
                    kind="arrival",
                    target=patient.label,
                )
            )

    def get_available_moves(self, game: QueueSimulation) -> list[QueueMove]:
        if game.metrics is not None:
            return []
        if game.calendar.is_empty():
            return []
        return [QueueMove("run_next"), QueueMove("run_until_complete")]

    def get_move_label(self, game: QueueSimulation, move: QueueMove) -> str:
        if move.kind == "run_next":
            return "Run next event"
        if move.kind == "run_until_complete":
            return "Run until complete"
        return super().get_move_label(game, move)

    def resolve_round(
        self,
        game: QueueSimulation,
        player_move: QueueMove,
        opponent_move: QueueMove | None,
    ) -> RoundResult:
        if player_move.kind == "run_next":
            latest = self.run_next_event(game)
        elif player_move.kind == "run_until_complete":
            latest = []
            while not game.calendar.is_empty():
                latest.extend(self.run_next_event(game))
        else:
            raise ValueError(f"Unsupported queueing move: {player_move.kind!r}")

        if game.calendar.is_empty():
            game.metrics = self.compute_metrics(game)
            latest.append(self._summary_event(game))
            game.score["player"] = 1

        game.latest_trace = latest
        return RoundResult.WIN if game.metrics is not None else RoundResult.CONTINUE

    def evaluate(self, game: QueueSimulation) -> GameResult:
        if game.metrics is not None:
            return GameResult.WIN
        return GameResult.IN_PROCESS

    def build_round_notes(
        self,
        game: QueueSimulation,
        player_move: QueueMove,
        opponent_move: QueueMove | None,
        round_result: RoundResult,
    ) -> dict[str, Any] | None:
        return {
            "action": player_move.kind,
            "round_result": round_result.value,
            "latest_trace": [event.model_dump() for event in game.latest_trace],
            "metrics": game.metrics.model_dump() if game.metrics is not None else None,
        }

    def get_journal_fragments(self, game: QueueSimulation) -> list[ContentFragment] | None:
        return [
            ContentFragment(content=self.render_trace_event(game, event))
            for event in game.latest_trace
        ]

    def run_next_event(self, game: QueueSimulation) -> list[QueueTraceEvent]:
        """Pop and process the next future event."""
        event = game.calendar.pop_next()
        if event is None:
            return []

        advance_world_turn_to(game, event.at_turn)
        latest: list[QueueTraceEvent] = []
        if event.kind == "arrival":
            self._handle_arrival(game, event, latest)
        elif event.kind == "service_complete":
            self._handle_service_complete(game, event, latest)
        else:
            raise ValueError(f"Unsupported simulation event kind: {event.kind!r}")
        game.trace.extend(latest)
        return latest

    def compute_metrics(self, game: QueueSimulation) -> QueueMetrics:
        """Compute one-run metrics from completed state."""
        completed_patients = [game.patients[label] for label in game.completed]
        stays = [
            stay
            for patient in completed_patients
            if (stay := patient.length_of_stay()) is not None
        ]
        waits = [patient.total_wait() for patient in completed_patients]
        completed_turn = max(
            (patient.completion_turn or 0 for patient in completed_patients),
            default=0,
        )
        utilization = {
            label: (
                station.busy_turns / (completed_turn * station.capacity)
                if completed_turn and station.capacity
                else 0.0
            )
            for label, station in game.stations.items()
        }
        bottleneck = max(utilization, key=utilization.get) if utilization else ""
        return QueueMetrics(
            completed_count=len(completed_patients),
            completed_turn=completed_turn,
            mean_length_of_stay=mean(stays) if stays else 0.0,
            mean_wait=mean(waits) if waits else 0.0,
            utilization=utilization,
            bottleneck=bottleneck,
        )

    def render_trace_event(self, game: QueueSimulation, event: QueueTraceEvent) -> str:
        """Render one trace fact in the configured projection mode."""
        if game.projection_mode == "narrative":
            return self._narrative_text(event)
        return f"{self._clock_label(event.turn)} — {event.text}"

    def _handle_arrival(
        self,
        game: QueueSimulation,
        event: SimulationEvent,
        latest: list[QueueTraceEvent],
    ) -> None:
        patient = game.patients[event.target or ""]
        self._enqueue(game, patient, game.entry_station, latest, arrival=True)
        self._try_start_service(game, game.entry_station, latest)

    def _handle_service_complete(
        self,
        game: QueueSimulation,
        event: SimulationEvent,
        latest: list[QueueTraceEvent],
    ) -> None:
        patient = game.patients[str(event.payload["patient"])]
        station_label = str(event.payload["station"])
        station = game.stations[station_label]
        station.in_service.remove(patient.label)
        station.completed_count += 1
        patient.service_end[station_label] = event.at_turn
        latest.append(
            self._trace(
                game,
                "service_complete",
                f"{patient.label} completes {station_label}.",
                patient=patient.label,
                station=station_label,
            )
        )

        next_station = station.next_station
        if next_station is None:
            patient.completed = True
            patient.completion_turn = event.at_turn
            patient.current_station = None
            game.completed.append(patient.label)
            latest.append(
                self._trace(
                    game,
                    "complete",
                    f"{patient.label} is discharged.",
                    patient=patient.label,
                )
            )
        else:
            self._enqueue(game, patient, next_station, latest)

        self._try_start_service(game, station_label, latest)
        if next_station is not None:
            self._try_start_service(game, next_station, latest)

    def _enqueue(
        self,
        game: QueueSimulation,
        patient: QueuePatient,
        station_label: str,
        latest: list[QueueTraceEvent],
        *,
        arrival: bool = False,
    ) -> None:
        station = game.stations[station_label]
        patient.current_station = station_label
        patient.queued_at[station_label] = int(game.locals["world_turn"])
        station.queue.append(patient.label)
        station.max_queue_length = max(station.max_queue_length, len(station.queue))
        if arrival:
            text = f"{patient.label} arrives and enters {station_label}."
            kind = "arrival"
        else:
            text = f"{patient.label} waits for {station_label}."
            kind = "queued"
        latest.append(
            self._trace(
                game,
                kind,
                text,
                patient=patient.label,
                station=station_label,
            )
        )

    def _try_start_service(
        self,
        game: QueueSimulation,
        station_label: str,
        latest: list[QueueTraceEvent],
    ) -> None:
        station = game.stations[station_label]
        while station.queue and len(station.in_service) < station.capacity:
            patient = game.patients[station.queue.pop(0)]
            now = int(game.locals["world_turn"])
            station.in_service.append(patient.label)
            station.started_count += 1
            station.busy_turns += station.service_turns
            patient.service_start[station_label] = now
            patient.wait_turns[station_label] = now - patient.queued_at[station_label]
            game.calendar.push(
                SimulationEvent(
                    label=f"complete_{patient.label}_{station_label}_{now}",
                    at_turn=now + station.service_turns,
                    kind="service_complete",
                    target=station_label,
                    payload={
                        "patient": patient.label,
                        "station": station_label,
                    },
                )
            )
            latest.append(
                self._trace(
                    game,
                    "service_start",
                    f"{patient.label} starts {station_label}.",
                    patient=patient.label,
                    station=station_label,
                )
            )

    def _summary_event(self, game: QueueSimulation) -> QueueTraceEvent:
        metrics = game.metrics
        if metrics is None:
            raise ValueError("Cannot summarize incomplete queue simulation")
        return self._trace(
            game,
            "summary",
            (
                f"Summary: completed={metrics.completed_count}; "
                f"mean_los={metrics.mean_length_of_stay:.1f}; "
                f"mean_wait={metrics.mean_wait:.1f}; "
                f"bottleneck={metrics.bottleneck}."
            ),
        )

    def _trace(
        self,
        game: QueueSimulation,
        kind: str,
        text: str,
        *,
        patient: str | None = None,
        station: str | None = None,
    ) -> QueueTraceEvent:
        return QueueTraceEvent(
            turn=int(game.locals["world_turn"]),
            kind=kind,
            text=text,
            patient=patient,
            station=station,
        )

    def _narrative_text(self, event: QueueTraceEvent) -> str:
        clock = self._clock_label(event.turn)
        if event.kind == "arrival":
            return f"{clock}: the doors open for {event.patient}."
        if event.kind == "queued":
            return f"{clock}: {event.patient} joins the wait for {event.station}."
        if event.kind == "service_start":
            return f"{clock}: {event.station} takes {event.patient} into service."
        if event.kind == "service_complete":
            return f"{clock}: {event.patient} clears {event.station}."
        if event.kind == "complete":
            return f"{clock}: {event.patient} leaves the department."
        if event.kind == "summary":
            return f"{clock}: the run settles; {event.text}"
        return f"{clock}: {event.text}"

    def _clock_label(self, turn: int) -> str:
        return f"{turn:02d}:00"
