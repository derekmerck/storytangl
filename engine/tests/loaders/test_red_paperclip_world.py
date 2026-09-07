"""Tests for the Red Paperclip trading world bundle."""

from __future__ import annotations

from pathlib import Path

import pytest

from tangl.core import Selector
from tangl.journal.fragments import ContentFragment
from tangl.loaders import WorldBundle
from tangl.loaders.compiler import WorldCompiler
from tangl.service.response import KvListValue
from tangl.service.story_info import resolve_story_info_projector
from tangl.service.world_registry import WorldRegistry
from tangl.story import Action, InitMode
from tangl.vm import Ledger
from tangl.vm.dispatch import do_provision
from tangl.vm.runtime.frame import PhaseCtx

from red_paperclip.domain import RedPaperclipHub
from red_paperclip.trade_graph import TradeGraph, TradeParseError


def _repo_worlds_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "worlds"


def _red_paperclip_root() -> Path:
    return _repo_worlds_dir() / "red_paperclip"


def _start() -> Ledger:
    bundle = WorldBundle.load(_red_paperclip_root())
    world = WorldCompiler().compile(bundle)
    result = world.create_story("red_paperclip", init_mode=InitMode.EAGER)
    ledger = Ledger.from_graph(result.graph, entry_id=result.graph.initial_cursor_id)
    opening = next(
        edge
        for edge in ledger.cursor.edges_out()
        if isinstance(edge, Action) and edge.text == "Take the paperclip and go"
    )
    ledger.resolve_choice(opening.uid)
    return ledger


def _ctx(ledger: Ledger) -> PhaseCtx:
    return PhaseCtx(graph=ledger.graph, cursor_id=ledger.cursor.uid)


def _actions(ledger: Ledger) -> list[Action]:
    assert isinstance(ledger.cursor, RedPaperclipHub)
    do_provision(ledger.cursor, ctx=_ctx(ledger))
    return list(ledger.cursor.edges_out(Selector(has_kind=Action)))


def _pick(actions: list[Action], **hints: str) -> Action:
    for action in actions:
        action_hints = action.ui_hints.model_dump() if action.ui_hints else {}
        if all(action_hints.get(key) == value for key, value in hints.items()):
            return action
    raise AssertionError(f"no action matched {hints!r}")


def _find(ledger: Ledger, **hints: str) -> Action:
    return _pick(_actions(ledger), **hints)


def _choose(ledger: Ledger, **hints: str) -> Action:
    action = _find(ledger, **hints)
    ledger.resolve_choice(action.uid, choice_payload=action.payload)
    return action


def _go(ledger: Ledger, hub: str) -> None:
    """Travel from the road to ``hub``, or back to the road from a hub."""
    if ledger.cursor.label == "road":
        _choose(ledger, contribution="movement", target=hub)
    else:
        _choose(ledger, contribution="movement", direction="out")


def _trade(ledger: Ledger, trader: str) -> Action:
    return _choose(ledger, contribution="trade", trader=trader)


def _content(ledger: Ledger) -> list[str]:
    return [
        fragment.content
        for fragment in ledger.get_journal()
        if isinstance(fragment, ContentFragment)
    ]


class TestRedPaperclipTradeGraph:
    """The trade file is the world, so it is checked as data first."""

    def test_the_district_parses_into_items_and_traders(self) -> None:
        trades = TradeGraph.load()

        assert len(trades.hubs()) == 6
        mira = trades.traders["mira"]
        assert mira.hub == "harbor"
        assert mira.offers == "fish_pen"
        assert mira.accepts == ["red_paperclip", "brass_doorknob"]
        assert mira.short_name == "Mira"

    def test_every_item_is_reachable_from_the_paperclip(self) -> None:
        trades = TradeGraph.load()

        routes = trades.routes()

        assert set(routes) == set(trades.items)

    def test_the_interesting_ends_are_the_far_ones(self) -> None:
        trades = TradeGraph.load()
        routes = trades.routes()

        lengths = {
            item.label: len(routes[item.label]) for item in trades.endings()
        }

        # The trap is two trades from the start and the ostrich farm is six:
        # a player can end the story before they understand it.
        assert lengths["sourdough_starter"] == 2
        assert lengths["lighthouse_keys"] == 4
        assert lengths["ostrich_share"] == 6

    def test_a_trader_may_only_have_one_thing_to_give(self) -> None:
        source = (
            "clip: a clip\n"
            "pen: a pen\n"
            "mug: a mug\n"
            "mira: Mira @ harbor\n"
            "clip -> mira -> pen\n"
            "mug -> mira -> mug\n"
        )

        with pytest.raises(TradeParseError, match="one thing to give"):
            TradeGraph.parse(source)


class TestRedPaperclipWorld:
    """Tests for the real trading world bundle."""

    def test_world_registry_discovers_red_paperclip(self) -> None:
        registry = WorldRegistry([_repo_worlds_dir()])

        assert "red_paperclip" in registry.bundles
        bundle = registry.bundles["red_paperclip"]
        assert bundle.manifest.label == "red_paperclip"
        assert bundle.manifest.metadata["title"] == "One Red Paperclip"

    def test_the_road_offers_travel_to_every_hub(self) -> None:
        ledger = _start()

        assert ledger.cursor.label == "road"
        targets = {
            (action.ui_hints.model_dump().get("target"))
            for action in _actions(ledger)
            if (action.ui_hints.model_dump().get("contribution")) == "movement"
        }

        assert targets == {"harbor", "market", "garage", "campus", "station", "airfield"}

    def test_a_trade_you_cannot_make_is_offered_and_refused(self) -> None:
        ledger = _start()
        _go(ledger, "harbor")

        # Both from one planning pass: re-provisioning replaces the edges.
        offered = _actions(ledger)
        holding = _pick(offered, trader="mira", given="red_paperclip")
        wanting = _pick(offered, trader="mira", given="brass_doorknob")

        # Both of Mira's trades are on the list. Which one you can take is a
        # matter of availability, not of whether the choice is drawn: reading
        # the dimmed one is how you learn she would take a doorknob too.
        assert holding.available(ctx=_ctx(ledger))
        assert not wanting.available(ctx=_ctx(ledger))

    def test_trading_up_to_the_lighthouse(self) -> None:
        ledger = _start()

        _go(ledger, "harbor")
        _trade(ledger, "mira")
        _go(ledger, "road")
        _go(ledger, "market")
        _trade(ledger, "cass")
        _go(ledger, "road")
        _go(ledger, "garage")
        _trade(ledger, "olsen")
        _go(ledger, "road")
        _go(ledger, "harbor")
        _trade(ledger, "gunnar")

        projected = resolve_story_info_projector(ledger).project(ledger=ledger)
        holding = next(
            section
            for section in projected.sections
            if section.section_id == "red_paperclip_holding"
        )
        assert isinstance(holding.value, KvListValue)
        assert [(row.key, row.value) for row in holding.value.items] == [
            ("Holding", "the keys to the Rock Point light"),
            ("Trades", 4),
            ("Journeys", 7),
        ]

        # Nobody in the district trades for a lighthouse, so the only thing
        # left to do is stop.
        stop = _choose(ledger, contribution="stop")

        assert stop.ui_hints.model_dump()["holding"] == "lighthouse_keys"
        assert ledger.cursor.label == "ending"
        content = _content(ledger)
        assert "The harbourmaster needs a motor more than he needs a lighthouse he is not allowed to sell. The keys are cold." in content
        assert any("one ruled line left for you" in line for line in content)
        assert any("a red paperclip -> a fish-shaped pen" in line for line in content)

    def test_a_spent_trader_stops_offering(self) -> None:
        ledger = _start()
        _go(ledger, "harbor")
        _trade(ledger, "mira")

        # Mira gave away the one pen she had, so her trades are not dimmed —
        # they are gone. What is left is the doorknob she took, which nobody
        # can trade for again.
        for action in _actions(ledger):
            assert action.ui_hints.model_dump().get("trader") != "mira"

    def test_the_two_trade_trap_ends_the_story_early(self) -> None:
        ledger = _start()

        _go(ledger, "market")
        _trade(ledger, "wick")
        _trade(ledger, "pia")
        _choose(ledger, contribution="stop")

        assert ledger.cursor.label == "ending"
        assert any("comes up like it never left" in line for line in _content(ledger))
