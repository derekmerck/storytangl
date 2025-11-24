"""
Tests exploring step/turn/round distinctions for re-entrant cursor patterns.

Terminology:
- **step**: Total edge follows in the session (already tracked by Frame.step)
- **turn**: Visits to unique cursor positions (not currently tracked)  
- **round**: Game-specific iteration count (tracked in game state)

These tests validate what exists and propose what might be needed.
"""
from __future__ import annotations
from uuid import UUID
from dataclasses import dataclass, field

import pytest

from tangl.core import Graph, StreamRegistry
from tangl.vm import Frame, ChoiceEdge, Ledger


# ─────────────────────────────────────────────────────────────────────────────
# Current behavior: step counts all follows
# ─────────────────────────────────────────────────────────────────────────────

class TestCurrentStepBehavior:
    """Validate that step increments on every follow, including self-loops."""
    
    def test_step_increments_on_forward_progress(self):
        """Step increments when moving to a new node."""
        g = Graph(label="forward")
        a = g.add_node(label="A")
        b = g.add_node(label="B")
        c = g.add_node(label="C")
        
        ab = ChoiceEdge(graph=g, source_id=a.uid, destination_id=b.uid)
        bc = ChoiceEdge(graph=g, source_id=b.uid, destination_id=c.uid)
        
        frame = Frame(graph=g, cursor_id=a.uid)
        assert frame.step == 0
        
        frame.follow_edge(ab)
        assert frame.step == 1
        assert frame.cursor_id == b.uid
        
        frame.follow_edge(bc)
        assert frame.step == 2
        assert frame.cursor_id == c.uid
    
    def test_step_increments_on_backtrack(self):
        """Step increments even when returning to a previously visited node."""
        g = Graph(label="backtrack")
        a = g.add_node(label="A")
        b = g.add_node(label="B")
        
        ab = ChoiceEdge(graph=g, source_id=a.uid, destination_id=b.uid)
        ba = ChoiceEdge(graph=g, source_id=b.uid, destination_id=a.uid)
        
        frame = Frame(graph=g, cursor_id=a.uid)
        
        frame.follow_edge(ab)  # A → B
        assert frame.step == 1
        
        frame.follow_edge(ba)  # B → A (backtrack)
        assert frame.step == 2
        
        frame.follow_edge(ab)  # A → B again
        assert frame.step == 3
    
    def test_step_increments_on_self_loop(self):
        """Step increments on self-referential edges."""
        g = Graph(label="loop")
        node = g.add_node(label="game")
        
        loop = ChoiceEdge(graph=g, source_id=node.uid, destination_id=node.uid)
        
        frame = Frame(graph=g, cursor_id=node.uid)
        
        for expected_step in range(1, 6):
            frame.follow_edge(loop)
            assert frame.step == expected_step
            assert frame.cursor_id == node.uid


# ─────────────────────────────────────────────────────────────────────────────
# Proposed: cursor_history for tracking path
# ─────────────────────────────────────────────────────────────────────────────

class TestCursorHistoryProposal:
    """
    Tests demonstrating cursor_history tracking.
    
    Proposal: Add `cursor_history: list[UUID]` to Frame or Ledger that
    records the cursor_id after each follow_edge.
    
    Benefits:
    - Replay/debugging: see exact path taken
    - Analytics: count unique visits, detect loops
    - First-visit detection: `cursor_id not in cursor_history[:-1]`
    """
    
    def test_manual_history_tracking_pattern(self):
        """Demonstrate manual history tracking (what we'd automate)."""
        g = Graph(label="history")
        a = g.add_node(label="A")
        b = g.add_node(label="B")
        
        ab = ChoiceEdge(graph=g, source_id=a.uid, destination_id=b.uid)
        ba = ChoiceEdge(graph=g, source_id=b.uid, destination_id=a.uid)
        bb = ChoiceEdge(graph=g, source_id=b.uid, destination_id=b.uid)
        
        frame = Frame(graph=g, cursor_id=a.uid)
        
        # Manual tracking (would be automated in Frame)
        cursor_history: list[UUID] = [frame.cursor_id]
        
        frame.follow_edge(ab)
        cursor_history.append(frame.cursor_id)
        
        frame.follow_edge(bb)  # self-loop
        cursor_history.append(frame.cursor_id)
        
        frame.follow_edge(bb)  # self-loop again
        cursor_history.append(frame.cursor_id)
        
        frame.follow_edge(ba)
        cursor_history.append(frame.cursor_id)
        
        # History shows complete path including loops
        assert cursor_history == [a.uid, b.uid, b.uid, b.uid, a.uid]
        
        # Unique cursors visited
        unique_cursors = set(cursor_history)
        assert unique_cursors == {a.uid, b.uid}
        
        # Count visits per node
        from collections import Counter
        visit_counts = Counter(cursor_history)
        assert visit_counts[a.uid] == 2  # start + return
        assert visit_counts[b.uid] == 3  # visit + 2 self-loops
    
    def test_derive_turn_from_history(self):
        """
        Demonstrate deriving 'turn' (unique position changes) from history.
        
        Turn increments only when cursor_id differs from previous.
        """
        g = Graph(label="turn")
        a = g.add_node(label="A")
        b = g.add_node(label="B")
        
        ab = ChoiceEdge(graph=g, source_id=a.uid, destination_id=b.uid)
        ba = ChoiceEdge(graph=g, source_id=b.uid, destination_id=a.uid)
        bb = ChoiceEdge(graph=g, source_id=b.uid, destination_id=b.uid)
        
        frame = Frame(graph=g, cursor_id=a.uid)
        cursor_history: list[UUID] = [frame.cursor_id]
        
        frame.follow_edge(ab)
        cursor_history.append(frame.cursor_id)
        
        frame.follow_edge(bb)  # self-loop - NOT a new turn
        cursor_history.append(frame.cursor_id)
        
        frame.follow_edge(ba)  # return to A - IS a new turn
        cursor_history.append(frame.cursor_id)
        
        # Derive turn count
        def count_turns(history: list[UUID]) -> int:
            """Count cursor changes (excluding consecutive duplicates)."""
            if not history:
                return 0
            turns = 1  # Initial position counts as turn 1
            for i in range(1, len(history)):
                if history[i] != history[i-1]:
                    turns += 1
            return turns
        
        assert frame.step == 3  # Total follows
        assert count_turns(cursor_history) == 3  # A(1) → B(2) → B(skip) → A(3)
    
    def test_first_visit_detection(self):
        """Demonstrate detecting first visit to a node."""
        g = Graph(label="first_visit")
        start = g.add_node(label="start")
        shrine = g.add_node(label="shrine")
        
        to_shrine = ChoiceEdge(graph=g, source_id=start.uid, destination_id=shrine.uid)
        back = ChoiceEdge(graph=g, source_id=shrine.uid, destination_id=start.uid)
        
        frame = Frame(graph=g, cursor_id=start.uid)
        cursor_history: list[UUID] = [frame.cursor_id]
        
        def is_first_visit(history: list[UUID]) -> bool:
            """True if current cursor hasn't been seen before."""
            if len(history) <= 1:
                return True
            current = history[-1]
            return current not in history[:-1]
        
        # First visit to start
        assert is_first_visit(cursor_history) is True
        
        # Visit shrine
        frame.follow_edge(to_shrine)
        cursor_history.append(frame.cursor_id)
        assert is_first_visit(cursor_history) is True  # First time at shrine
        
        # Return to start
        frame.follow_edge(back)
        cursor_history.append(frame.cursor_id)
        assert is_first_visit(cursor_history) is False  # Been to start before


# ─────────────────────────────────────────────────────────────────────────────
# Game-specific round tracking
# ─────────────────────────────────────────────────────────────────────────────

class TestGameRoundTracking:
    """
    Game rounds are distinct from VM steps/turns.
    
    - VM step: total edge follows
    - VM turn: unique cursor changes  
    - Game round: iterations through the game loop since setup()
    
    Round tracking belongs in game state, not VM infrastructure.
    """
    
    def test_round_tracked_separately_from_step(self):
        """Game round count is independent of VM step count."""
        g = Graph(label="game")
        
        intro = g.add_node(label="intro")
        game = g.add_node(label="game")
        outro = g.add_node(label="outro")
        
        to_game = ChoiceEdge(graph=g, source_id=intro.uid, destination_id=game.uid)
        play = ChoiceEdge(graph=g, source_id=game.uid, destination_id=game.uid)
        to_outro = ChoiceEdge(graph=g, source_id=game.uid, destination_id=outro.uid)
        
        # Game state (would be in Game entity)
        game_round = 0
        
        frame = Frame(graph=g, cursor_id=intro.uid)
        
        # Step 1: Enter game
        frame.follow_edge(to_game)
        game_round = 1  # Game starts, round 1
        assert frame.step == 1
        
        # Steps 2-4: Play rounds
        for _ in range(3):
            game_round += 1
            frame.follow_edge(play)
        
        assert frame.step == 4
        assert game_round == 4  # 4 rounds played
        
        # Step 5: Exit game
        frame.follow_edge(to_outro)
        assert frame.step == 5
        # game_round stays at 4 - it's game-specific, doesn't track exits
    
    def test_round_resets_on_new_game(self):
        """Round count resets when game is re-entered (if designed that way)."""
        g = Graph(label="replay")
        
        hub = g.add_node(label="hub")
        game = g.add_node(label="game")
        
        to_game = ChoiceEdge(graph=g, source_id=hub.uid, destination_id=game.uid)
        play = ChoiceEdge(graph=g, source_id=game.uid, destination_id=game.uid)
        back = ChoiceEdge(graph=g, source_id=game.uid, destination_id=hub.uid)
        
        frame = Frame(graph=g, cursor_id=hub.uid)
        
        # First playthrough
        game_round = 0
        frame.follow_edge(to_game)
        game_round = 1
        frame.follow_edge(play)
        game_round += 1
        frame.follow_edge(back)
        
        first_play_rounds = game_round
        assert first_play_rounds == 2
        
        # Second playthrough - round resets
        game_round = 0  # Reset on re-entry
        frame.follow_edge(to_game)
        game_round = 1
        
        assert game_round == 1  # Fresh game
        assert frame.step == 4  # But VM step continues


# ─────────────────────────────────────────────────────────────────────────────
# Ledger-level tracking
# ─────────────────────────────────────────────────────────────────────────────

class TestLedgerLevelTracking:
    """
    Ledger could optionally maintain cursor history for persistence.
    
    Current: Ledger.step syncs from Frame.step after resolution
    Proposal: Ledger.cursor_history syncs from Frame tracking
    """
    
    def test_ledger_step_syncs_from_frame(self):
        """Verify current pattern: ledger.step = frame.step after resolution."""
        g = Graph(label="sync")
        a = g.add_node(label="A")
        b = g.add_node(label="B")
        
        ab = ChoiceEdge(graph=g, source_id=a.uid, destination_id=b.uid)
        
        ledger = Ledger(graph=g, cursor_id=a.uid, records=StreamRegistry())
        ledger.push_snapshot()
        
        assert ledger.step == 0
        
        frame = ledger.get_frame()
        frame.follow_edge(ab)
        
        # Sync pattern (done by orchestrator)
        ledger.cursor_id = frame.cursor_id
        ledger.step = frame.step
        
        assert ledger.step == 1
        assert ledger.cursor_id == b.uid
    
    def test_proposed_history_sync_pattern(self):
        """
        Demonstrate proposed pattern for syncing cursor history.
        
        This could be added to Frame and synced to Ledger like step.
        """
        g = Graph(label="history_sync")
        a = g.add_node(label="A")
        b = g.add_node(label="B")
        
        ab = ChoiceEdge(graph=g, source_id=a.uid, destination_id=b.uid)
        ba = ChoiceEdge(graph=g, source_id=b.uid, destination_id=a.uid)
        
        ledger = Ledger(graph=g, cursor_id=a.uid, records=StreamRegistry())
        ledger.push_snapshot()
        
        # Proposed: ledger.cursor_history = []
        cursor_history: list[UUID] = [ledger.cursor_id]  # Initial position
        
        frame = ledger.get_frame()
        
        frame.follow_edge(ab)
        cursor_history.append(frame.cursor_id)
        ledger.cursor_id = frame.cursor_id
        ledger.step = frame.step
        
        frame = ledger.get_frame()  # Fresh frame with new cursor
        
        frame.follow_edge(ba)
        cursor_history.append(frame.cursor_id)
        ledger.cursor_id = frame.cursor_id
        ledger.step = frame.step
        
        # Proposed: ledger.cursor_history = cursor_history
        assert cursor_history == [a.uid, b.uid, a.uid]
        assert ledger.step == 2


# ─────────────────────────────────────────────────────────────────────────────
# Marker-based round tracking (alternative approach)
# ─────────────────────────────────────────────────────────────────────────────

class TestMarkerBasedRoundTracking:
    """
    Alternative: Use record markers to distinguish step types.
    
    The records stream already has markers like "step-0001".
    Could add marker_type="round" vs "step" to distinguish game rounds
    from story progression.
    """
    
    def test_markers_already_track_steps(self):
        """Verify that step markers are created on each follow."""
        g = Graph(label="markers")
        node = g.add_node(label="game")
        
        loop = ChoiceEdge(graph=g, source_id=node.uid, destination_id=node.uid)
        
        records = StreamRegistry()
        frame = Frame(graph=g, cursor_id=node.uid, records=records)
        
        frame.follow_edge(loop)
        frame.follow_edge(loop)
        frame.follow_edge(loop)
        
        # Check for step markers
        step_markers = records.markers['frame']

        # Should have markers for step-0001, step-0002, step-0003
        assert len(step_markers) >= 3
