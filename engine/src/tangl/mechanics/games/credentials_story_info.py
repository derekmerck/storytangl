"""Story-info channels for the credentials checkpoint shift (Bridge.2b).

Registers ``advertise`` / ``get_story_info`` dispatch handlers (the side-channel
surface from ``STORYTANGL_WIDGET_VOCAB.md`` §1.6) so a client can pull
supplementary projected state on demand: the day's rules, the player's shift
progress, and the findings surfaced so far for the active candidate.

Disclosure discipline ("a disclosed projection of world state, not world state
itself"):

- ``rules`` -- the posted checkpoint rulebook; public by construction.
- ``roster_progress`` -- the player's *own* rulings and how far through the
  shift they are. It does **not** reveal whether each ruling was correct: the
  expected disposition is hidden truth, surfaced only when the shift resolves.
- ``case_summary`` -- only the findings the player has already revealed for the
  active candidate (inspection + mediation outcomes). No unrevealed packet
  truth, no expected disposition.

Service-layer imports are isolated to this module (mirroring
``tangl.mechanics.sandbox.story_info``); importing it registers the handlers.
"""
from __future__ import annotations

from tangl.service.dispatch import on_advertise_info_channels, on_get_story_info
from tangl.service.response import (
    InfoAffordance,
    KvListValue,
    KvRow,
    ProjectedSection,
    ScalarValue,
    StoryInfoRequest,
    TableValue,
)
from tangl.vm.runtime.frame import PhaseCtx

from .credentials_game import CredentialsGame
from .has_game import HasGame

RULES_KIND = "rules"
PROGRESS_KIND = "roster_progress"
CASE_SUMMARY_KIND = "case_summary"


def _credentials_game(caller: HasGame) -> CredentialsGame | None:
    """Return the active game if it is a CredentialsGame, else None.

    The handlers register for every ``HasGame`` caller, so ``caller.game`` is the
    typed accessor; the isinstance check discriminates the credentials mechanic
    from the other game types that share the same story-info dispatch.
    """

    game = caller.game
    return game if isinstance(game, CredentialsGame) else None


@on_advertise_info_channels(wants_caller_kind=HasGame, wants_exact_kind=False)
def advertise_credentials_info_channels(
    *,
    caller: HasGame,
    ctx: PhaseCtx,
    **_kw: object,
) -> list[InfoAffordance]:
    """Advertise the credentials side-channels for a checkpoint-shift block."""

    if _credentials_game(caller) is None:
        return []
    return [
        InfoAffordance(
            kind=RULES_KIND,
            label="Today's rules",
            shortcuts=["r", "rules"],
            query={"kinds": [RULES_KIND]},
        ),
        InfoAffordance(
            kind=PROGRESS_KIND,
            label="Shift progress",
            shortcuts=["p", "shift"],
            query={"kinds": [PROGRESS_KIND]},
        ),
        InfoAffordance(
            kind=CASE_SUMMARY_KIND,
            label="Findings",
            shortcuts=["c", "findings"],
            query={"kinds": [CASE_SUMMARY_KIND]},
        ),
    ]


@on_get_story_info(wants_caller_kind=HasGame, wants_exact_kind=False)
def project_credentials_info(
    *,
    caller: HasGame,
    ctx: PhaseCtx,
    request: StoryInfoRequest,
    **_kw: object,
) -> list[ProjectedSection] | None:
    """Project the requested credentials channels for the active shift."""

    game = _credentials_game(caller)
    if game is None:
        return None

    kinds = request.requested_kinds()
    sections: list[ProjectedSection] = []
    if RULES_KIND in kinds:
        sections.append(_rules_section(game))
    if PROGRESS_KIND in kinds:
        sections.extend(_progress_sections(game))
    if CASE_SUMMARY_KIND in kinds:
        summary = _case_summary_section(game)
        if summary is not None:
            sections.append(summary)
    return sections or None


def _rules_section(game: CredentialsGame) -> ProjectedSection:
    """The day's restriction map -- public checkpoint rules."""

    rows: list[KvRow] = []
    for rule in game.restriction_map.rules:
        rows.append(
            KvRow(
                key=f"{rule.indication} ({rule.region})",
                value=rule.level.value,
            )
        )
    return ProjectedSection(
        section_id="credential_rules",
        title="Checkpoint Rules",
        kind=RULES_KIND,
        value=KvListValue(items=rows),
    )


def _progress_sections(game: CredentialsGame) -> list[ProjectedSection]:
    """Shift progress: how far along, and the rulings made so far.

    Deliberately omits correctness -- whether a past ruling was right is hidden
    truth until the shift resolves.
    """

    total = game._total_cases()
    decided = len(game.case_results)
    progress_text = (
        "Shift complete"
        if game.shift_complete
        else f"Candidate {min(decided + 1, total)} of {total}"
    )
    summary = ProjectedSection(
        section_id="credential_progress",
        title="Shift Progress",
        kind=PROGRESS_KIND,
        value=ScalarValue(value=progress_text),
    )
    if not game.case_results:
        return [summary]

    rulings = ProjectedSection(
        section_id="credential_rulings",
        title="Rulings So Far",
        kind=PROGRESS_KIND,
        value=TableValue(
            columns=["Candidate", "Your ruling"],
            rows=[
                [result.candidate_name, result.chosen_disposition.value]
                for result in game.case_results
            ],
        ),
    )
    return [summary, rulings]


def _case_summary_section(game: CredentialsGame) -> ProjectedSection | None:
    """Findings the player has surfaced for the active candidate.

    Discloses only revealed document/packet findings and mediation outcomes --
    never unrevealed truth or the expected disposition.
    """

    rows: list[KvRow] = []
    for target, finding in game.revealed_findings.items():
        rows.append(KvRow(key=target, value=finding, emphasis="warn"))
    for target, finding in game.packet_findings.items():
        rows.append(KvRow(key=target, value=finding, emphasis="danger"))
    _mediation_emphasis = {"cleared": "ok", "verified": "subtle", "confirmed": "danger"}
    for target, status in game.finding_status.items():
        rows.append(
            KvRow(key=target, value=status, emphasis=_mediation_emphasis.get(status, "subtle"))
        )
    if not rows:
        return None
    return ProjectedSection(
        section_id="credential_case_summary",
        title="Findings",
        kind=CASE_SUMMARY_KIND,
        value=KvListValue(items=rows),
    )
