"""Tests for the Red Paperclip trading world bundle."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tangl.core import Selector
from tangl.journal.fragments import ChoiceFragment, ContentFragment
from tangl.loaders import WorldBundle
from tangl.loaders.compiler import WorldCompiler
from tangl.service.response import KvListValue
from tangl.service.story_info import resolve_story_info_projector
from tangl.service.world_registry import WorldRegistry
from tangl.story import Action, InitMode
from tangl.vm import Ledger
from tangl.vm.dispatch import do_provision
from tangl.vm.runtime.frame import PhaseCtx

from red_paperclip.domain import RedPaperclipHub, _holding, _state
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
    """Take the trade this trader offers for what is being held.

    Keyed on the holding, because a trader who accepts several things has a
    row per accepted item and all but one of them are dimmed.
    """
    return _choose(
        ledger,
        contribution="trade",
        trader=trader,
        given=_holding(ledger.cursor),
    )


def _hint(fragment: ChoiceFragment, key: str) -> object:
    return fragment.ui_hints.model_dump().get(key) if fragment.ui_hints else None


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

    def test_the_emitted_model_travels_through_the_real_map(self) -> None:
        """The ASP model's hub is read from the world, not named twice.

        Travel is half the cost of a plan, so a model that kept its own idea
        of which place is the map would silently describe a different world
        the first time one was renamed.
        """

        from red_paperclip.__main__ import asp, map_hub

        script = yaml.safe_load(
            (_red_paperclip_root() / "script.yaml").read_text()
        )
        owner = [
            label
            for scene in script["scenes"].values()
            for label, block in scene["blocks"].items()
            if isinstance(block, dict) and "map" in block
        ]

        assert map_hub() == owner[0]
        assert f"init(at({owner[0]}))." in asp(TradeGraph.load(), "ostrich_share")

    def test_a_trader_may_not_accept_what_they_offer(self) -> None:
        """The rule that makes a planned-then-spent row harmless.

        A trade is planned before its own effect runs, so a trader's rows
        outlive the trade that spends them by one frame. They are refused
        anyway — the holding has changed and no row of theirs can match it —
        and this is the reason no row can: nobody trades a thing for itself.
        """

        source = (
            "clip: a clip\n"
            "pen: a pen\n"
            "mira: Mira @ harbor\n"
            "clip -> mira -> pen\n"
            "pen -> mira\n"
        )

        with pytest.raises(TradeParseError, match="for itself"):
            TradeGraph.parse(source).check()

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

    def test_a_refused_trade_says_what_it_would_take(self) -> None:
        """The refusal is the puzzle, so it is written rather than coded.

        `unavailable_reason` alone is `guard_failed_or_unavailable`, which
        tells a player nothing about a district they are trying to learn.
        """

        ledger = _start()
        _go(ledger, "harbor")

        refused = next(
            fragment
            for fragment in ledger.get_journal()
            if isinstance(fragment, ChoiceFragment)
            and _hint(fragment, "trader") == "mira"
            and _hint(fragment, "given") == "brass_doorknob"
        )

        assert refused.available is False
        assert refused.unavailable_reason == "not_holding"
        assert refused.blockers[0].message == (
            "Mira would take a hand-turned brass doorknob, "
            "but you don't have one to offer."
        )
        # The sentence stands on its own, so a client may render it instead of
        # the offer rather than beside a paraphrase of the same offer.
        assert refused.blockers[0].replaces_text is True

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

    def test_the_solver_plan_is_playable(self) -> None:
        """Walk the plan the solver returns for the emitted contract.

        `python -m red_paperclip --asp ostrich_share` writes this world in the
        vocabulary of the archived proof of concept, and its minimum-horizon
        plan is thirteen moves: six trades and seven journeys, with two pairs
        of trades taken in one hub. Playing it here is the differential check
        that the emitted model and the running world are the same game — a
        model that disagreed would produce a plan that stalls partway.
        """

        ledger = _start()

        _go(ledger, "harbor")
        _trade(ledger, "mira")
        _go(ledger, "road")
        _go(ledger, "market")
        _trade(ledger, "cass")
        _go(ledger, "road")
        _go(ledger, "garage")
        _trade(ledger, "olsen")
        _trade(ledger, "rusev")
        _go(ledger, "road")
        _go(ledger, "airfield")
        _trade(ledger, "ilse")
        _trade(ledger, "whina")

        assert _holding(ledger.cursor) == "ostrich_share"
        assert int(_state(ledger.cursor)["world_turn"]) == 7

        _choose(ledger, contribution="stop")

        assert ledger.cursor.label == "ending"
        assert any("being looked at" in line for line in _content(ledger))

    def test_a_spent_trader_stops_offering(self) -> None:
        ledger = _start()
        _go(ledger, "harbor")
        _trade(ledger, "mira")

        # PLANNING runs before UPDATE, so the frame that takes the pen was
        # planned while Mira still had it and her rows survive into this one
        # journal. They must be refused while they do: read as the client
        # reads them, not through a provisioning pass the client never makes.
        surviving = [
            fragment
            for fragment in ledger.get_journal()
            if isinstance(fragment, ChoiceFragment)
            and _hint(fragment, "trader") == "mira"
        ]
        assert surviving, "expected Mira's planned rows to survive her own trade"
        assert not any(fragment.available for fragment in surviving[-2:])

        # The next plan drops them: a trader with nothing to give is not a
        # dimmed offer, it is no offer.
        for action in _actions(ledger):
            assert action.ui_hints.model_dump().get("trader") != "mira"

    def test_a_spent_trader_says_so_in_the_prose(self) -> None:
        """The row goes; the account of it does not.

        A trader with nothing left is not a refused offer, so their rows are
        dropped — but they are still standing in the hub, and describing them
        mending a net while silently offering nothing is the gap that turns a
        puzzle into a hunt.
        """

        ledger = _start()
        _go(ledger, "harbor")
        _trade(ledger, "mira")
        _go(ledger, "road")
        _go(ledger, "harbor")

        content = _content(ledger)[-4:]

        assert any("nothing else to spare" in line for line in content)
        assert not any("spool of orange twine" in line for line in content)
        # Her neighbours are untouched: they still have their one thing.
        assert any("re-lashing a rack" in line for line in content)

    def test_the_two_trade_trap_ends_the_story_early(self) -> None:
        ledger = _start()

        _go(ledger, "market")
        _trade(ledger, "wick")
        _trade(ledger, "pia")
        _choose(ledger, contribution="stop")

        assert ledger.cursor.label == "ending"
        assert any("comes up like it never left" in line for line in _content(ledger))
