"""
Markov analysis of no-choice track layouts.

A race board with no assignment decision is a Markov chain: the path is fully
determined by the roll sequence, so the *layout* — not the play — is what
produces the drama. That makes tension curves computable rather than a matter
of taste, which is the operational form of the family's verisimilitude stance:
if authored bias is legitimate, it should at least be measurable.

The headline number is expected rolls to finish. Compared against the same
board with its redirects removed, it says whether a layout accelerates the race
or drags it out.

Scope
-----
This models **one token racing alone**. Contested races add eviction and roll
assignment, which are not captured by a chain over a single token's position.
Use it to tune a layout, then play the layout in whichever configuration the
world wants.

Design heuristics worth knowing, from published analyses of commercial boards:
roughly a 1:1 ladder-to-chute ratio, modifiers on about 20% of squares, long
ladders early, entangled modifiers in the middle, and long chutes near the end
for late reversals. Those are one publisher's engineering choices rather than
laws, which is why nothing here enforces them — they only inform the advisory
classification below.
"""
from __future__ import annotations

from dataclasses import dataclass

from .track_game import TrackGame


@dataclass(frozen=True)
class TrackAnalysis:
    """Computed shape of a no-choice track layout."""

    expected_rolls: float
    baseline_rolls: float
    ladder_count: int
    chute_count: int
    modifier_density: float
    net_vector: int
    character: str

    @property
    def drag_ratio(self) -> float:
        """Expected rolls relative to the same board with no redirects."""

        if not self.baseline_rolls:
            return 1.0
        return self.expected_rolls / self.baseline_rolls


def _transitions(game: TrackGame, position: int) -> list[int]:
    """Return the reachable positions from one square, one entry per roll face."""

    results: list[int] = []
    for roll in range(game.min_roll, game.max_roll + 1):
        if position + roll > game.finish_distance:
            # Exact-landing rule: an unusable roll is forfeited in place.
            results.append(position)
            continue
        results.append(game.landing_from(position, roll))
    return results


def _solve(matrix: list[list[float]], vector: list[float]) -> list[float]:
    """Solve a small dense linear system by Gaussian elimination."""

    size = len(vector)
    rows = [row[:] + [vector[index]] for index, row in enumerate(matrix)]

    for col in range(size):
        pivot = max(range(col, size), key=lambda r: abs(rows[r][col]))
        if abs(rows[pivot][col]) < 1e-12:
            raise ValueError("Track layout produces a singular system; is the finish reachable?")
        rows[col], rows[pivot] = rows[pivot], rows[col]

        divisor = rows[col][col]
        rows[col] = [value / divisor for value in rows[col]]

        for other in range(size):
            if other == col:
                continue
            factor = rows[other][col]
            if factor:
                rows[other] = [
                    value - factor * pivot_value
                    for value, pivot_value in zip(rows[other], rows[col])
                ]

    return [row[size] for row in rows]


def expected_rolls_to_finish(game: TrackGame) -> float:
    """Return the expected number of rolls for one token to finish alone.

    Solves ``E[p] = 1 + mean(E[next(p, roll)])`` with ``E[finish] = 0``.
    """

    size = game.finish_distance
    if size <= 0:
        return 0.0

    faces = game.max_roll - game.min_roll + 1
    probability = 1.0 / faces

    matrix = [[0.0] * size for _ in range(size)]
    vector = [1.0] * size

    for position in range(size):
        matrix[position][position] += 1.0
        for landing in _transitions(game, position):
            if landing >= game.finish_distance:
                continue  # absorbing: contributes zero
            matrix[position][landing] -= probability

    return _solve(matrix, vector)[0]


def finish_distribution(game: TrackGame, max_rolls: int = 100) -> list[float]:
    """Return the cumulative probability of having finished by each roll count.

    Index ``n`` is the probability the race is over within ``n + 1`` rolls. A
    long flat tail here is the signature of a punishing endgame.
    """

    faces = game.max_roll - game.min_roll + 1
    probability = 1.0 / faces

    state = [0.0] * (game.finish_distance + 1)
    state[0] = 1.0
    cumulative: list[float] = []

    for _ in range(max_rolls):
        nxt = [0.0] * (game.finish_distance + 1)
        nxt[game.finish_distance] = state[game.finish_distance]
        for position in range(game.finish_distance):
            mass = state[position]
            if not mass:
                continue
            for landing in _transitions(game, position):
                nxt[landing] += mass * probability
        state = nxt
        cumulative.append(state[game.finish_distance])

    return cumulative


def analyze_track(game: TrackGame) -> TrackAnalysis:
    """Return the computed shape and an advisory character for a layout."""

    ladders = 0
    chutes = 0
    net = 0
    for origin, destination in game.redirects.items():
        if destination == origin:
            continue
        net += destination - origin
        if destination > origin:
            ladders += 1
        else:
            chutes += 1

    density = (ladders + chutes) / game.track_length if game.track_length else 0.0
    expected = expected_rolls_to_finish(game)

    baseline_game = game.model_copy(update={"redirects": {}})
    baseline = expected_rolls_to_finish(baseline_game)

    analysis = TrackAnalysis(
        expected_rolls=expected,
        baseline_rolls=baseline,
        ladder_count=ladders,
        chute_count=chutes,
        modifier_density=density,
        net_vector=net,
        character=_character(ladders + chutes, density, expected, baseline),
    )
    return analysis


def _character(modifiers: int, density: float, expected: float, baseline: float) -> str:
    """Name the dramatic shape a layout produces.

    Advisory only — a world is free to want any of these.
    """

    if not modifiers:
        return "footrace"
    ratio = expected / baseline if baseline else 1.0
    if ratio >= 1.4:
        # Long chutes late: leaders get flung back and the tail goes fat.
        return "heartbreak"
    if density > 0.25:
        return "chaotic"
    if density < 0.15:
        return "sparse"
    return "balanced"
