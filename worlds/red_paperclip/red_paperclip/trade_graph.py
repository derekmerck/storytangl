"""The trade graph: `trades.d2` read as items, traders, and trades.

The file is authored to read as d2 — node declarations, arrows, and labels
after a colon — because the thing being authored *is* a graph, and the
author wants to see it as one. Three line shapes carry the whole world:

    fish_pen: a fish-shaped pen              an item
    mira: Mira, who mends nets @ harbor      a trader, standing in one hub
    red_paperclip -> mira -> fish_pen: ...   a trade, and the line it prints

A trader has one thing to give, so the offered item is declared once and
inherited by every later line that names the trader. Dotted keys carry the
rest: `mira.here` is what you see when she is in front of you,
`ostrich_share.ending` is how the story ends holding it.

Nothing here knows about StoryTangl. `domain.py` compiles this into sandbox
locations, mobs, and interactions; `python -m red_paperclip` reads the same
model to check the graph and draw it.
"""

from __future__ import annotations

from collections import deque
from pathlib import Path

from pydantic import BaseModel, Field


TRADES_FILE = Path(__file__).resolve().parent.parent / "trades.d2"

START_ITEM = "red_paperclip"


class TradeParseError(ValueError):
    """A line in the trade file that cannot mean anything."""


class TradeItem(BaseModel):
    """One thing you can be holding."""

    label: str
    name: str
    ending: str = ""


class Trader(BaseModel):
    """One person, in one hub, with one thing to give."""

    label: str
    name: str
    hub: str
    here: str = ""
    offers: str = ""
    accepts: list[str] = Field(default_factory=list)
    lines: dict[str, str] = Field(default_factory=dict)
    """Journal line per accepted item, keyed by the item given up."""

    @property
    def short_name(self) -> str:
        """Return the name to use mid-sentence, without the description.

        A trader is introduced by the whole of their name and then referred
        to by the front of it, so `Mira, who mends nets` offers you a pen as
        `Mira`. The break is the first comma, or the preposition that starts
        the description; a name with neither is short already.
        """
        head = self.name.split(",")[0]
        for preposition in (" at ", " in ", " on ", " under ", " who ", " going ", " of "):
            head = head.split(preposition)[0]
        return head.strip()

    def line_for(self, held: str, items: dict[str, TradeItem]) -> str:
        """Return the journal line for trading ``held`` here."""
        authored = self.lines.get(held)
        if authored:
            return authored
        return (
            f"You trade {items[held].name} to {self.short_name} "
            f"for {items[self.offers].name}."
        )

    def offer_text(self, held: str, items: dict[str, TradeItem]) -> str:
        """Return the choice text for trading ``held`` here.

        Who, then what you get, then what it costs — in that order, because a
        narrow client truncates the tail and the tail is the thing the reader
        already knows: they are holding it. Phrased so it stays true whether
        or not the reader can take it; why they cannot is the blocker's job.
        """
        return (
            f"{self.short_name} will trade {items[self.offers].name} "
            f"for {items[held].name}"
        )

    def refusal(self, held: str, items: dict[str, TradeItem]) -> str:
        """Return why this trade is not on offer to the reader right now."""
        return (
            f"{self.short_name} would take {items[held].name}, "
            "but you don't have one to offer."
        )


class TradeGraph(BaseModel):
    """Every item, trader, and trade in the world."""

    items: dict[str, TradeItem] = Field(default_factory=dict)
    traders: dict[str, Trader] = Field(default_factory=dict)

    # ---------------------------------------------------------------- read

    @classmethod
    def load(cls, path: Path | None = None) -> "TradeGraph":
        """Parse and check the world's trade file."""
        source = (path or TRADES_FILE).read_text(encoding="utf-8")
        graph = cls.parse(source)
        graph.check()
        return graph

    @classmethod
    def parse(cls, source: str) -> "TradeGraph":
        """Parse the d2-shaped trade source into items, traders, and trades."""
        graph = cls()
        lines = deque(source.splitlines())
        while lines:
            raw = lines.popleft()
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            key, sep, value = line.partition(":")
            value = value.strip()
            if value == "|":
                value = _block(lines)
            if "->" in key:
                graph._add_trade(key, value)
            elif not sep:
                raise TradeParseError(f"not a declaration, an attribute, or a trade: {line!r}")
            elif "." in key:
                graph._add_attribute(key.strip(), value)
            else:
                graph._declare(key.strip(), value)
        return graph

    def _declare(self, label: str, value: str) -> None:
        name, at, hub = value.partition(" @ ")
        if at:
            self.traders[label] = Trader(label=label, name=name.strip(), hub=hub.strip())
        else:
            self.items[label] = TradeItem(label=label, name=name.strip())

    def _add_attribute(self, key: str, value: str) -> None:
        label, _, attribute = key.partition(".")
        if attribute == "ending" and label in self.items:
            self.items[label].ending = value
        elif attribute == "here" and label in self.traders:
            self.traders[label].here = value
        else:
            raise TradeParseError(f"no {attribute!r} to set on {label!r}")

    def _add_trade(self, key: str, line: str) -> None:
        parts = [part.strip() for part in key.split("->")]
        if len(parts) == 3:
            held, trader_label, offered = parts
        elif len(parts) == 2:
            held, trader_label = parts
            offered = ""
        else:
            raise TradeParseError(f"a trade is 'held -> trader [-> offered]': {key!r}")
        trader = self.traders.get(trader_label)
        if trader is None:
            raise TradeParseError(f"no trader named {trader_label!r}")
        if offered:
            if trader.offers and trader.offers != offered:
                raise TradeParseError(
                    f"{trader_label!r} already offers {trader.offers!r}, "
                    f"not also {offered!r} — a trader has one thing to give"
                )
            trader.offers = offered
        if held in trader.accepts:
            raise TradeParseError(f"{trader_label!r} already accepts {held!r}")
        trader.accepts.append(held)
        if line:
            trader.lines[held] = line

    def check(self) -> None:
        """Raise unless every trade names items and traders that exist."""
        for trader in self.traders.values():
            if not trader.offers:
                raise TradeParseError(f"{trader.label!r} has nothing to trade")
            for label in [trader.offers, *trader.accepts]:
                if label not in self.items:
                    raise TradeParseError(f"{trader.label!r} names no such item: {label!r}")
            if trader.offers in trader.accepts:
                raise TradeParseError(f"{trader.label!r} trades {trader.offers!r} for itself")
        if START_ITEM not in self.items:
            raise TradeParseError(f"the world has no {START_ITEM!r} to start from")

    # ---------------------------------------------------------------- ask

    def acceptors(self, held: str) -> list[Trader]:
        """Return every trader who would take ``held``, in file order."""
        return [trader for trader in self.traders.values() if held in trader.accepts]

    def is_terminal(self, held: str) -> bool:
        """Return whether nobody in the world trades for ``held``."""
        return not self.acceptors(held)

    def traders_in(self, hub: str) -> list[Trader]:
        """Return the traders standing in one hub, in file order."""
        return [trader for trader in self.traders.values() if trader.hub == hub]

    def hubs(self) -> list[str]:
        """Return every hub a trader stands in, in file order."""
        seen: list[str] = []
        for trader in self.traders.values():
            if trader.hub not in seen:
                seen.append(trader.hub)
        return seen

    def routes(self, start: str = START_ITEM) -> dict[str, list[Trader]]:
        """Return one shortest route of trades to every reachable item.

        Breadth-first from ``start``, so the route found for an item is the
        one with the fewest trades in it — which is the question the puzzle
        asks. Ties are broken by file order, not by hub.
        """
        routes: dict[str, list[Trader]] = {start: []}
        queue = deque([start])
        while queue:
            held = queue.popleft()
            for trader in self.acceptors(held):
                if trader.offers in routes:
                    continue
                routes[trader.offers] = [*routes[held], trader]
                queue.append(trader.offers)
        return routes

    def endings(self) -> list[TradeItem]:
        """Return the items the story can end on, in file order."""
        return [item for item in self.items.values() if self.is_terminal(item.label)]


def _block(lines: deque[str]) -> str:
    """Consume an indented block after a ``|`` and return it as one string."""
    block: list[str] = []
    while lines and (not lines[0].strip() or lines[0].startswith((" ", "\t"))):
        block.append(lines.popleft().strip())
    return " ".join(part for part in block if part)
