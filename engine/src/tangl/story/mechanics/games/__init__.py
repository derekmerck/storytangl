"""
Game mechanics integration with the story VM.

This package bridges Layer 2 game core (:mod:`tangl.mechanics.games`) with
Layer 3 narrative traversal. Use :class:`HasGame` to attach a game instance
and handler to a node.
"""
from __future__ import annotations

from .has_game import HasGame
from .handlers import (
    generate_game_journal,
    inject_game_context,
    process_game_move,
    provision_game_moves,
    setup_game_on_first_visit,
)

__all__ = [
    "HasGame",
    "generate_game_journal",
    "inject_game_context",
    "process_game_move",
    "provision_game_moves",
    "setup_game_on_first_visit",
]
