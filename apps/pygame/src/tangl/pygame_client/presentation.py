"""Ephemeral ordered visual presentation, using the same stage fold as scrolling."""
from __future__ import annotations

from dataclasses import replace
from uuid import UUID

from tangl.service.response import RuntimeEnvelope

from .bridge import PygameSessionBridge
from .models import Finding, Piece, StageImage, Turn, Zone
from .stage import BACKGROUND_ROLES, MAP_ROLES, PORTRAIT_ROLES, STAGED_ROLES


ROOM_ROLES = ("narrative_im", *STAGED_ROLES)
"""What states the room. A cover is persistent chrome, not a room, so it does not."""


def merge_turns(turns: list[Turn]) -> Turn:
    """Collapse a batch of turns into the one frame the player acts on.

    Time Parity: the client may show intermediate steps, but must never trap the
    player below the CLI floor, which presents the whole batch at once.

    Media is stage state rather than a transcript, so it is merged by identity
    rather than concatenated. Consecutive steps in one batch restate the scene —
    the dockhand contest and its aftermath both carry the same background and
    portrait — and concatenating them draws a character twice, at two default
    slots, since unslotted duplicates take successive positions.

    One background, last one wins. Speaker-associated avatar/dialog portraits
    share a slot keyed by speaker and optional presentation handle; later faces
    inherit omitted staging and replace in place. Unassociated media keeps its
    role/source/slot key. First-appearance order stays stable for default slots.

    A turn that states the room -- a backdrop or any staged figure -- replaces
    the figures before it and retires omitted associated portraits. Matching
    speaker/handle presentations retain their established staging. A turn that
    states nothing keeps the room, and a cover is chrome and replaces none. This
    is how this client collapses a stream into frames, not a stream contract:
    which figures a statement holds is the backend's to say.
    """

    merged = Turn(step=turns[-1].step if turns else 0)
    staged: dict[tuple[str, ...], StageImage] = {}
    pieces: dict[str, Piece] = {}
    zones: dict[UUID, Zone] = {}
    findings: dict[str, Finding] = {}
    for turn in turns:
        # Pieces and zones are stage state too, and a re-entrant block restates
        # them every turn. Keyed by identity so a restatement updates the piece
        # in place instead of listing the same document twice.
        for piece in turn.pieces:
            pieces[piece.piece_id] = piece
        for zone in turn.zones:
            zones[zone.uid] = zone
        for finding in turn.findings:
            findings[finding.key] = finding
        if any(image.role in ROOM_ROLES for image in turn.images):
            restated = {_slot(image) for image in turn.images
                        if image.role in PORTRAIT_ROLES and image.speaker_id is not None}
            staged = {key: image for key, image in staged.items()
                      if image.role not in STAGED_ROLES and (
                          image.role not in PORTRAIT_ROLES
                          or image.speaker_id is None or key in restated
                      )}
        for image in turn.images:
            key = _slot(image)
            previous = staged.get(key)
            if image.role in PORTRAIT_ROLES and image.speaker_id is not None and previous:
                image = _inherit_portrait(image, previous)
            staged[key] = image
        merged.lines.extend(turn.lines)
    merged.images.extend(staged.values())
    merged.pieces.extend(pieces.values())
    merged.zones.extend(zones.values())
    merged.findings.extend(findings.values())
    merged.choices.extend(turns[-1].choices if turns else [])
    return merged


def _slot(image: StageImage) -> tuple[str, ...]:
    """One backdrop/map; associated portraits by speaker/handle; others by asset/slot.

    A plate is stage state like a background: a batch that crosses between two
    maps must not keep the old one and pair it with the new geometry. Both
    collapse to one slot, last one wins.
    """

    if image.role in BACKGROUND_ROLES:
        return ("background",)
    if image.role in MAP_ROLES:
        return ("map",)
    if image.role in PORTRAIT_ROLES and image.speaker_id is not None:
        return ("portrait", str(image.speaker_id), image.presentation_handle or "")
    return (image.role, image.source, image.x_slot or "")


def _inherit_portrait(image: StageImage, previous: StageImage) -> StageImage:
    """Keep established staging; a supplied axis replaces both its slot and fraction."""
    inherit_x = image.x_slot is None and image.x_frac is None
    inherit_y = image.y_slot is None and image.y_frac is None
    return replace(
        image,
        x_slot=previous.x_slot if inherit_x else image.x_slot,
        x_frac=previous.x_frac if inherit_x else image.x_frac,
        y_slot=previous.y_slot if inherit_y else image.y_slot,
        y_frac=previous.y_frac if inherit_y else image.y_frac,
        keep=previous.keep if image.keep is None else image.keep,
        flip_h=previous.flip_h if image.flip_h is None else image.flip_h,
        clip=previous.clip if image.clip is None else image.clip,
        timing=previous.timing if image.timing is None else image.timing,
        visibility=previous.visibility if image.visibility is None else image.visibility,
        clip_binding=previous.clip_binding if image.clip_binding is None else image.clip_binding,
    )


def visual_passages(
    bridge: PygameSessionBridge, envelope: RuntimeEnvelope, previous: Turn | None = None,
) -> list[Turn]:
    """Deterministic local snapshots; never dispatch effects or synchronize audio."""
    state = Turn(step=0, images=[image for image in previous.images
        if image.role in BACKGROUND_ROLES + STAGED_ROLES
        or image.role in PORTRAIT_ROLES and image.speaker_id is not None] if previous else [])
    snapshots: list[Turn] = []
    for block in bridge.build_passages(envelope.fragments):
        restated = {_slot(image) for passage in block for image in passage.images
                    if image.role in PORTRAIT_ROLES and image.speaker_id is not None}
        # Preserve established hints for speakers restated later in this block;
        # their future assets are not applied ahead of their attributed line.
        retained = [image for image in state.images
                    if image.role in PORTRAIT_ROLES and image.speaker_id is not None
                    and _slot(image) in restated]
        block[0] = replace(block[0], images=[*retained, *block[0].images])
        for passage in block:
            state = merge_turns([replace(state, lines=[], choices=[]), passage])
            state.source_id = passage.source_id
            snapshots.append(state)
    return snapshots


