"""Run a StoryTangl world in the pygame client.

    PYTHONPATH=engine/src:apps/pygame/src python -m tangl.pygame_client \
        --world repartee_loop --assets worlds/repartee_loop/media

Every click and key resolves to a choice ``edge_id``, never to a bespoke action,
so a later hotspot commits the same payload as the numbered list.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import pygame

from .bridge import PygameSessionBridge
from .models import Turn
from .stage import Stage

logger = logging.getLogger(__name__)


def _turns(bridge: PygameSessionBridge, envelope) -> list[Turn]:
    return bridge.build_turns(list(getattr(envelope, "fragments", []) or []))


def _merge(turns: list[Turn]) -> Turn:
    """Collapse a batch of turns into the one frame the player acts on.

    Time Parity: the client may show intermediate steps, but must never trap the
    player below the CLI floor, which presents the whole batch at once.
    """

    merged = Turn(step=turns[-1].step if turns else 0)
    for turn in turns:
        merged.images.extend(turn.images)
        merged.lines.extend(turn.lines)
    merged.choices.extend(turns[-1].choices if turns else [])
    return merged


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--world", default="repartee_loop")
    parser.add_argument("--assets", type=Path, default=None)
    parser.add_argument("--screenshot", type=Path, help="render one frame, save it, and exit")
    args = parser.parse_args(argv)

    bridge = PygameSessionBridge()
    envelope = bridge.start(args.world)
    stage = Stage(asset_dir=args.assets, title=f"StoryTangl — {args.world}")
    frame = _merge(_turns(bridge, envelope))
    stage.draw(frame)

    if args.screenshot is not None:
        pygame.image.save(stage.window, str(args.screenshot))
        return 0

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if (hit := stage.hit(event.pos)) is not None:
                    envelope = bridge.choose(*hit)
                    frame = _merge(_turns(bridge, envelope))
                    stage.draw(frame)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif pygame.K_1 <= event.key <= pygame.K_9:
                    index = event.key - pygame.K_1
                    available = [c for c in frame.choices if c.available]
                    if index < len(available):
                        choice = available[index]
                        envelope = bridge.choose(choice.edge_id, choice.payload)
                        frame = _merge(_turns(bridge, envelope))
                        stage.draw(frame)
    pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
