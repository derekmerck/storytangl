"""Run a StoryTangl world in the pygame client.

    PYTHONPATH=engine/src:apps/pygame/src python -m tangl.pygame_client \
        --world repartee_loop --assets worlds/repartee_loop/media

Number keys select a choice, arrows and page keys scroll prose, escape quits.
Every click and choice key resolves to a choice ``edge_id``, never to a bespoke
action, so a hotspot commits the same payload as the numbered list.

A choice that wants a value first -- ``accepts.kind = "pieces"`` -- opens a
second numbered list of the pieces it will take. Escape leaves that list without
committing. Only the finished ``(edge_id, payload)`` pair reaches the service,
and it is byte-identical to what the CLI builds for the same choice.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from uuid import UUID

import pygame

from .bridge import PygameSessionBridge, commit_payload, remaining_pieces
from .models import (
    Action,
    BeginSelection,
    CancelSelection,
    Commit,
    PendingSelection,
    Piece,
    PickPiece,
    StageImage,
    Turn,
    Zone,
)
from .stage import BACKGROUND_ROLES, MAP_ROLES, Stage, choice_action

logger = logging.getLogger(__name__)


def _turns(bridge: PygameSessionBridge, envelope) -> list[Turn]:
    return bridge.build_turns(list(getattr(envelope, "fragments", []) or []))


def _merge(turns: list[Turn]) -> Turn:
    """Collapse a batch of turns into the one frame the player acts on.

    Time Parity: the client may show intermediate steps, but must never trap the
    player below the CLI floor, which presents the whole batch at once.

    Media is stage state rather than a transcript, so it is merged by identity
    rather than concatenated. Consecutive steps in one batch restate the scene —
    the dockhand contest and its aftermath both carry the same background and
    portrait — and concatenating them draws a character twice, at two default
    slots, since unslotted duplicates take successive positions.

    The rule is deliberately small: one background, last one wins so a scene
    change during the batch is not stale; other media keyed by role, source, and
    slot, so two genuinely distinct portraits both survive while a restatement
    of the same one does not. Later values replace earlier ones in place, which
    keeps first-appearance order stable for default slot assignment.
    """

    merged = Turn(step=turns[-1].step if turns else 0)
    staged: dict[tuple[str, ...], StageImage] = {}
    pieces: dict[str, Piece] = {}
    zones: dict[UUID, Zone] = {}
    for turn in turns:
        # Pieces and zones are stage state too, and a re-entrant block restates
        # them every turn. Keyed by identity so a restatement updates the piece
        # in place instead of listing the same document twice.
        for piece in turn.pieces:
            pieces[piece.piece_id] = piece
        for zone in turn.zones:
            zones[zone.uid] = zone
        for image in turn.images:
            # A plate is stage state like a background: a batch that crosses
            # between two maps must not keep the old one and pair it with the
            # new geometry. Both collapse to one slot, last one wins.
            if image.role in BACKGROUND_ROLES:
                key: tuple[str, ...] = ("background",)
            elif image.role in MAP_ROLES:
                key = ("map",)
            else:
                key = (image.role, image.source, image.x_slot or "")
            staged[key] = image
        merged.lines.extend(turn.lines)
    merged.images.extend(staged.values())
    merged.pieces.extend(pieces.values())
    merged.zones.extend(zones.values())
    merged.choices.extend(turns[-1].choices if turns else [])
    return merged


def _frame(bridge: PygameSessionBridge, envelope) -> Turn:
    """Merge a batch into one actionable frame and attach the current plate."""

    frame = _merge(_turns(bridge, envelope))
    frame.plate = bridge.map_plate()
    return frame


def _keyed(
    frame: Turn,
    pending: PendingSelection | None,
    number: int,
) -> Action | None:
    """Resolve a number key against whichever numbered list is on screen.

    The renderer numbers every choice, available or not, so the key indexes the
    displayed list rather than a filtered one -- otherwise the number a player
    reads and the number a key selects drift apart.
    """

    if pending is not None:
        if number == 0:
            return CancelSelection()
        candidates = remaining_pieces(frame, pending)
        if number <= len(candidates):
            return PickPiece(piece_id=candidates[number - 1].piece_id)
        return None
    if 1 <= number <= len(frame.choices):
        return choice_action(frame.choices[number - 1])
    return None


def _apply(
    bridge: PygameSessionBridge,
    frame: Turn,
    pending: PendingSelection | None,
    action: Action,
):
    """Advance the input state machine. Returns the new pending state and, when
    the action reached the service, the envelope it produced."""

    match action:
        case CancelSelection():
            return None, None
        case BeginSelection(choice=choice):
            return PendingSelection(choice=choice), None
        case PickPiece(piece_id=piece_id):
            if pending is None:
                return None, None
            pending.picked.append(piece_id)
            if not pending.full and pending.wanted:
                # More pieces still required; keep collecting.
                return pending, None
            payload = commit_payload(pending.choice, pending.picked)
            return None, bridge.choose(pending.choice.edge_id, payload)
        case Commit(edge_id=edge_id, payload=payload):
            return None, bridge.choose(edge_id, payload)
    return pending, None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--world", default="repartee_loop")
    parser.add_argument("--assets", type=Path, default=None)
    parser.add_argument("--screenshot", type=Path, help="render one frame, save it, and exit")
    parser.add_argument(
        "--advance",
        type=int,
        default=0,
        help="take N first-available choices before rendering; for headless checks",
    )
    args = parser.parse_args(argv)

    bridge = PygameSessionBridge()
    envelope = bridge.start(args.world)
    stage = Stage(asset_dir=args.assets, title=f"StoryTangl — {args.world}")
    frame = _frame(bridge, envelope)

    for _ in range(args.advance):
        available = [choice for choice in frame.choices if choice.available]
        if not available:
            break
        envelope = bridge.choose(available[0].edge_id, available[0].payload)
        frame = _frame(bridge, envelope)

    stage.draw(frame)

    if args.screenshot is not None:
        pygame.image.save(stage.window, str(args.screenshot))
        return 0

    pending: PendingSelection | None = None
    running = True
    while running:
        for event in pygame.event.get():
            action: Action | None = None
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                action = stage.hit(event.pos)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    # Escape leaves a selection before it leaves the game: a
                    # player who opened one by mistake should not have to quit.
                    if pending is not None:
                        pending = None
                        stage.draw(frame)
                    else:
                        running = False
                elif event.key in (pygame.K_UP, pygame.K_PAGEUP):
                    stage.scroll_by(-1 if event.key == pygame.K_UP else -4)
                    stage.draw(frame, pending)
                elif event.key in (pygame.K_DOWN, pygame.K_PAGEDOWN):
                    stage.scroll_by(1 if event.key == pygame.K_DOWN else 4)
                    stage.draw(frame, pending)
                elif pygame.K_0 <= event.key <= pygame.K_9:
                    action = _keyed(frame, pending, event.key - pygame.K_0)

            if action is None:
                continue
            pending, envelope = _apply(bridge, frame, pending, action)
            if envelope is not None:
                frame = _frame(bridge, envelope)
            stage.draw(frame, pending)
    pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
