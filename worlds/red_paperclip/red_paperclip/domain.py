"""The Red Paperclip world: `trades.d2` compiled into a sandbox.

The world's places, prose, and map plate are ordinary near-native blocks in
`script.yaml`. Everything that makes it a *game* — twenty-one items, twenty-one
traders, and every trade between them — is read from `trades.d2` and compiled
here, because that graph is the thing the author edits and it wants to be seen
as a graph rather than as four hundred lines of YAML.

Three handlers do the whole job:

- `setup_red_paperclip` parks a trader mob in each hub, once, before planning.
- `project_red_paperclip_trades` projects one action per live trade, plus the
  choice to stop when nobody will trade for what you are holding.
- `contribute_red_paperclip_symbols` publishes the holding and the two helpers
  those actions call.

The holding is deliberately *not* a sandbox asset. Sandbox assets model things
you can pick up and put down, and project take/drop/give affordances to say so;
a trade is an atomic swap of the single thing you are carrying, and there is
never a moment where the paperclip is on the ground. So the holding is one
scoped value, and the traded-away item leaves the world with the person who
wanted it.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from tangl.core import BaseFragment, BehaviorRegistry, Graph, Priority, Selector
from tangl.core.runtime_op import Effect, Predicate
from tangl.journal.fragments import ContentFragment
from tangl.mechanics.sandbox import SandboxLocation, SandboxMob, SandboxScope

# Load-bearing despite being unused: the sandbox package deliberately does not
# import its own story-info adapter, so a world that wants ordinary sandbox
# disclosure -- location, time, exits, presence, and the map plate geometry the
# pygame client needs to draw a district -- has to ask for the module by name.
# Dropping this line costs the world every one of those sections and nothing
# says so; the map simply stops being a map.
import tangl.mechanics.sandbox.story_info  # noqa: F401
from tangl.presentation.intent import Blocker
from tangl.presentation.projection import (
    InfoAffordance,
    ItemListValue,
    KvListValue,
    ProjectedItem,
    ProjectedSection,
    ProjectionRequest,
)
from tangl.presentation.values import KvRow
from tangl.story import Action, StoryGraph
from tangl.vm import on_gather_ns, on_provision
from tangl.vm.dispatch import on_compose_journal
from tangl.vm.ctx import VmPhaseCtx

from .trade_graph import START_ITEM, TradeGraph, Trader


TRADES = TradeGraph.load()

red_paperclip_dispatch = BehaviorRegistry(
    label="red_paperclip.presentation_dispatch"
)

SCOPE_LABEL = "the_district"
ENDING_BLOCK = "ending"


class RedPaperclipHub(SandboxLocation):
    """A place on the map where traders stand."""


# ---------------------------------------------------------------- state

def _initial_state() -> dict[str, Any]:
    """Return a fresh opening state.

    Fresh, not a copy of a module constant: the chain and the spent list are
    mutated in place all game, and a shallow copy would hand every district
    the same two lists.
    """
    return {
        "world_turn": 0,
        "holding": START_ITEM,
        "chain": [START_ITEM],
        "spent": [],
    }


def _maybe_scope(location: RedPaperclipHub) -> SandboxScope | None:
    for candidate in location.ancestors:
        if isinstance(candidate, SandboxScope):
            return candidate
    return None


def _scope(location: RedPaperclipHub) -> SandboxScope:
    scope = _maybe_scope(location)
    if scope is None:
        raise ValueError(f"{location.get_label()!r} is not under its sandbox scope")
    return scope


def _state(location: RedPaperclipHub) -> dict[str, Any]:
    """Return the district's state, or its opening values before there is one.

    A hub's namespace is gathered once to check whether it can be entered,
    which happens before the hub is provisioned and therefore before the
    district exists. Nothing has been traded at that point, so the opening
    values are the true answer rather than a placeholder.
    """
    scope = _maybe_scope(location)
    if scope is None:
        return _initial_state()
    return scope.locals


def _holding(location: RedPaperclipHub) -> str:
    return str(_state(location)["holding"])


def _chain(location: RedPaperclipHub) -> list[str]:
    chain = _state(location)["chain"]
    if not isinstance(chain, list):
        raise TypeError("chain must be a list")
    return chain


def _spent(location: RedPaperclipHub) -> list[str]:
    spent = _state(location)["spent"]
    if not isinstance(spent, list):
        raise TypeError("spent must be a list")
    return spent


def _live_traders(location: RedPaperclipHub) -> list[Trader]:
    """Return the traders in this hub who still have their offer."""
    spent = _spent(location)
    return [
        trader
        for trader in TRADES.traders_in(location.get_label())
        if trader.label not in spent
    ]


def _stuck(location: RedPaperclipHub) -> bool:
    """Return whether nobody left in the district wants what you hold."""
    spent = _spent(location)
    return not [
        trader
        for trader in TRADES.acceptors(_holding(location))
        if trader.label not in spent
    ]


def _trade(location: RedPaperclipHub, trader_label: str) -> str:
    """Hand over the holding, take the offer, and spend the trader."""
    trader = TRADES.traders[trader_label]
    locals_ = _scope(location).locals
    locals_["holding"] = trader.offers
    _chain(location).append(trader.offers)
    _spent(location).append(trader.label)
    return trader.offers


def _ending_text(location: RedPaperclipHub) -> str:
    holding = _holding(location)
    item = TRADES.items[holding]
    if item.ending:
        return item.ending
    return (
        f"Nobody left in the district will trade for {item.name}. You stop "
        "where you are, which is how the trading always ends."
    )


def _chain_text(location: RedPaperclipHub) -> str:
    return " -> ".join(TRADES.items[label].name for label in _chain(location))


# ---------------------------------------------------------------- setup

def _hubs(graph: Graph) -> dict[str, RedPaperclipHub]:
    return {
        node.get_label(): node
        for node in graph.find_all(Selector(has_kind=RedPaperclipHub))
        if isinstance(node, RedPaperclipHub)
    }


def _ensure_district(graph: Graph) -> None:
    """Park every trader in their hub, once, before the first plan."""
    if graph.find_one(Selector.from_identifier(SCOPE_LABEL)) is not None:
        return

    scope = SandboxScope(
        label=SCOPE_LABEL,
        locals=_initial_state(),
        wait_enabled=False,
    )
    graph.add(scope)

    hubs = _hubs(graph)
    for hub in hubs.values():
        hub.sandbox_scope = SCOPE_LABEL
        scope.add_child(hub)

    for trader in TRADES.traders.values():
        if trader.hub not in hubs:
            raise ValueError(
                f"{trader.label!r} stands in {trader.hub!r}, which is not a hub "
                f"in this world: {sorted(hubs)}"
            )
        mob = SandboxMob(
            label=trader.label,
            name=trader.name,
            kind="trader",
            location=trader.hub,
            present_text=trader.here,
        )
        graph.add(mob)
        scope.add_child(mob)
        scope.mobs.append(mob)


@on_provision(
    wants_caller_kind=RedPaperclipHub,
    wants_exact_kind=False,
    priority=Priority.FIRST,
)
def setup_red_paperclip(
    *,
    caller: RedPaperclipHub,
    ctx: VmPhaseCtx,
    **_kw: object,
) -> None:
    """Attach the district's shared sandbox state before hub planning."""
    _ = ctx
    _ensure_district(caller.graph)
    return None


# ---------------------------------------------------------- projection

def _clear_trade_actions(location: RedPaperclipHub, ctx: VmPhaseCtx) -> None:
    for edge in list(location.edges_out(Selector(has_kind=Action))):
        if {"dynamic", "sandbox", "trade"}.issubset(edge.tags or set()):
            location.graph.remove(edge.uid, _ctx=ctx)


def _trade_payload(**extra: object) -> dict[str, object]:
    return {
        "sandbox_time_cost": {"kind": "trade", "duration": 0},
        **extra,
    }


@on_provision(
    wants_caller_kind=RedPaperclipHub,
    wants_exact_kind=False,
    priority=Priority.LAST,
)
def project_red_paperclip_trades(
    *,
    caller: RedPaperclipHub,
    ctx: VmPhaseCtx,
    **_kw: object,
) -> None:
    """Project every trade on offer in this hub, and the way to stop.

    A trade the reader cannot currently make is still projected — it renders
    dimmed, and reading it is how you learn that Wick would take a fish pen.
    A trader who has already given their one thing away projects nothing at
    all, because the offer no longer exists to be dimmed.

    PLANNING runs before UPDATE, so the frame that takes Mira's pen was
    planned while she still had it: her rows survive into that one journal
    and are dropped by the next plan. They are refused while they survive
    without needing a second guard, because a trader never accepts what they
    offer — `TradeGraph.check` refuses that outright — so no surviving row can
    match what the completed trade just put in your hand.
    """
    if not caller.auto_provision:
        return None
    graph = caller.graph
    if graph is None or (isinstance(graph, StoryGraph) and graph.frozen_shape):
        return None

    _clear_trade_actions(caller, ctx)

    for trader in _live_traders(caller):
        for held in trader.accepts:
            Action(
                registry=graph,
                label=f"trade_{caller.get_label()}_{trader.label}_{held}",
                predecessor_id=caller.uid,
                successor_id=caller.uid,
                text=trader.offer_text(held, TRADES.items),
                availability=[Predicate(expr=f"holding == {held!r}")],
                blockers=[
                    Blocker(
                        code="not_holding",
                        message=trader.refusal(held, TRADES.items),
                        replaces_text=True,
                    )
                ],
                effects=[Effect(expr=f"paperclip_trade({trader.label!r})")],
                journal_text=trader.line_for(held, TRADES.items),
                payload=_trade_payload(trade=trader.label, given=held),
                tags={"dynamic", "sandbox", "trade"},
                ui_hints={
                    "source": "red_paperclip",
                    "source_kind": "world_authority",
                    "contribution": "trade",
                    "trader": trader.label,
                    "given": held,
                    "taken": trader.offers,
                },
            )

    ending = graph.find_one(Selector.from_identifier(ENDING_BLOCK))
    if ending is not None and _stuck(caller):
        Action(
            registry=graph,
            label=f"trade_{caller.get_label()}_stop",
            predecessor_id=caller.uid,
            successor_id=ending.uid,
            text=f"Stop here, and keep {TRADES.items[_holding(caller)].name}",
            journal_text=(
                f"{_ending_text(caller)}\n\n{_chain_text(caller)}\n\n"
                f"{len(_chain(caller)) - 1} trades, "
                f"{int(_state(caller)['world_turn'])} journeys."
            ),
            payload=_trade_payload(stop=True),
            tags={"dynamic", "sandbox", "trade"},
            ui_hints={
                "source": "red_paperclip",
                "source_kind": "world_authority",
                "contribution": "stop",
                "holding": _holding(caller),
            },
        )
    return None


# ---------------------------------------------------------- namespace

@on_gather_ns(
    wants_caller_kind=RedPaperclipHub,
    wants_exact_kind=False,
)
def contribute_red_paperclip_symbols(
    *,
    caller: RedPaperclipHub,
    **_kw: object,
) -> dict[str, Any] | None:
    """Publish the holding, its story, and the one effect that changes it."""
    if not isinstance(caller.graph, Graph):
        return None
    holding = _holding(caller)
    return {
        "holding": holding,
        "holding_name": TRADES.items[holding].name,
        "holding_ending": _ending_text(caller),
        "chain_text": _chain_text(caller),
        "trade_count": len(_chain(caller)) - 1,
        "journey_count": int(_state(caller)["world_turn"]),
        "paperclip_trade": lambda trader: _trade(caller, str(trader)),
    }


@on_compose_journal(
    wants_caller_kind=RedPaperclipHub,
    wants_exact_kind=False,
    priority=Priority.LATE,
)
def compose_spent_trader_lines(
    *,
    caller: RedPaperclipHub,
    ctx: VmPhaseCtx,
    fragments: list[BaseFragment],
    **_kw: object,
) -> list[BaseFragment] | None:
    """Say what a trader with nothing left is doing instead.

    Their rows are gone, which is right — an offer that no longer exists is
    not a refusal — but they are still standing in the hub, and a person
    described as mending a net while silently offering nothing is the kind of
    gap that turns a puzzle into a hunt. The row was right to go; the fact
    belongs in the prose, so it goes there.
    """

    _ = ctx
    scope = _maybe_scope(caller)
    if scope is None:
        return None
    spent = set(_spent(caller))
    lines = {
        mob.uid: TRADES.traders[mob.get_label()].gone_text(TRADES.items)
        for mob in scope.mobs
        if mob.get_label() in spent
    }
    if not lines:
        return None

    swapped = False
    composed: list[BaseFragment] = []
    for fragment in fragments:
        # Type first: only a content fragment carries the source that says
        # which mob spoke, and a choice fragment has no `source_id` at all.
        line = lines.get(fragment.source_id) if isinstance(fragment, ContentFragment) else None
        if line is not None:
            composed.append(fragment.model_copy(update={"content": line}))
            swapped = True
        else:
            composed.append(fragment)
    return composed if swapped else None


# ---------------------------------------------------------- story info


def advertise_red_paperclip_info(
    *, caller: RedPaperclipHub, **_kw: object
) -> list[InfoAffordance]:
    """Advertise the world's two exact trade-state channels."""

    return [
        InfoAffordance(channel_id="ui-trade-status", label="Holding"),
        InfoAffordance(channel_id="ui-trade-history", label="Trade history"),
    ]


red_paperclip_dispatch.register(
    advertise_red_paperclip_info,
    task="advertise_info_channels",
    wants_caller_kind=RedPaperclipHub,
    wants_exact_kind=False,
)


def project_red_paperclip_holding(
    *,
    caller: RedPaperclipHub,
    request: ProjectionRequest,
    **_kw: object,
) -> list[ProjectedSection] | None:
    """Contribute what is being held and how it was got.

    Only these two sections. Location, time, exits and presence are ordinary
    sandbox disclosure and the sandbox handler contributes them for every
    world; reproducing them here would give this one a second, divergent copy
    of a surface it does not own.
    """

    requested = request.requested_channels()
    if not requested or requested.isdisjoint({"ui-trade-status", "ui-trade-history"}):
        return None

    holding = _holding(caller)
    sections: list[ProjectedSection] = []
    if "ui-trade-status" in requested:
        sections.append(
            ProjectedSection(
                section_id="red_paperclip_holding",
                title="Holding",
                kind="status",
                value=KvListValue(
                    items=[
                        KvRow(key="Holding", value=TRADES.items[holding].name),
                        KvRow(key="Trades", value=len(_chain(caller)) - 1),
                        KvRow(
                            key="Journeys",
                            value=int(_state(caller)["world_turn"]),
                        ),
                    ]
                ),
            )
        )
    if "ui-trade-history" in requested:
        sections.append(
            ProjectedSection(
                section_id="red_paperclip_chain",
                title="Chain",
                kind="history",
                value=ItemListValue(
                    items=[
                        ProjectedItem(label=TRADES.items[label].name)
                        for label in _chain(caller)
                    ]
                ),
            )
        )
    return sections or None


red_paperclip_dispatch.register(
    project_red_paperclip_holding,
    task="get_story_info",
    wants_caller_kind=RedPaperclipHub,
    wants_exact_kind=False,
)


def get_authorities() -> list[BehaviorRegistry]:
    """Expose the world's ordinary presentation authority."""
    return [red_paperclip_dispatch]


RedPaperclipHub.model_rebuild(_types_namespace={"UUID": UUID})
