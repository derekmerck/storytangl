# One Red Paperclip

You start with a red paperclip. Somebody will take it off you and give you
something better; somebody will take that. Keep going until nobody in the
district wants what you are holding, and whatever that turns out to be is how
the story ends — so the game is choosing which corner to get stuck in.

There is a two-trade dead end at the market and a six-trade share in an ostrich
farm at the airfield, and no warning which is which except the graph itself.

## The world is a data file

Places and prose are ordinary near-native blocks in `script.yaml`. Everything
that makes it a game — twenty-one items, twenty-one traders, and every trade
between them — is [`trades.d2`](trades.d2), which is authored to read as d2
because the thing being authored is a graph:

```
fish_pen: a fish-shaped pen                items are nodes
mira: Mira, who mends nets @ harbor        traders stand in one hub
red_paperclip -> mira -> fish_pen: ...     a trade, and the line it prints
brass_doorknob -> mira                     ...she takes a doorknob too
```

A trader has exactly one thing to give, so the offered item is declared once
and inherited by every later line that names them. That is what makes the file
short: a trader who accepts four things is four lines, not four trades. Dotted
keys carry the rest — `mira.here` is what you see when she is in front of you,
`ostrich_share.ending` is how the story ends holding it. An item nobody accepts
is an ending; an item with no `.ending` gets a plain one.

`red_paperclip/trade_graph.py` parses it and refuses the mistakes that matter:
a trader with two things to give, a trade naming an item that does not exist, a
trader with nothing to trade at all.

## What the engine already did

The compile in `red_paperclip/domain.py` is three handlers, because sandbox
mechanics already own everything except the trade rule itself.

**Hubs are `SandboxLocation`s and the road is the map.** `road` owns the plate
and names six regions; each hub claims one and links back. Travel is projected
by `project_sandbox_map_travel`, so a client that can draw maps gets hitboxes
and one that cannot gets the same numbered list.

**Traders are `SandboxMob`s.** They are parked in a hub with `present_text`, so
who is in front of you is composed into the journal by
`compose_sandbox_mob_journal` without this world writing any of it.

**Trades are ordinary actions** projected by a world authority, one per
`(trader, item they accept)`, self-looping, with `holding == 'x'` as the guard
and one effect that swaps the holding and spends the trader.

A trade you cannot make is still projected. It renders dimmed, and reading it
is how you learn that Wick would take a fish pen — decision legibility
(widget vocabulary §5.1) is doing real work here, because the dimmed rows *are*
the puzzle. A trader who has already given away their one thing projects
nothing at all: the offer no longer exists to be dimmed.

Each refused row says what it would have taken, because six of the seven rows
in a hub are refusals and `guard_failed_or_unavailable` teaches a player
nothing about a district they are trying to learn:

```
x) Mira will trade a fish-shaped pen for a hand-turned brass doorknob
   [blockers: Mira would take a hand-turned brass doorknob, but you have nothing like it to offer.]
```

That is an authored `Blocker` on the projected edge — `Action.blockers`, which
`_choice_blockers` prefers over anything it computes. The choice text stays
true in both states and the blocker carries the part that is only true in one,
which is why the text says "will trade" rather than "your paperclip for her
pen": a row is planned before the reader's holding is known to it.

And PLANNING runs before UPDATE, so the
frame that takes Mira's pen was planned while she still had it: her rows
survive into that one journal and the next plan drops them. They are refused
while they survive without needing a second guard, because a trader never
accepts what they offer.

### Why the holding is not a sandbox asset

Sandbox assets model things you can pick up and put down, and the generic
projectors say so — a carried asset gets a `Drop` choice, a portable one on the
floor gets `Take`, a mob holding one gets `Take it from them`. All three are
wrong here. There is never a moment where the paperclip is on the ground, and a
trade is atomic: you cannot take Mira's pen without giving her something.

So the holding is one value in `scope.locals`, the traded-away item leaves the
world with the person who wanted it, and there is no inventory to project. If a
second world needs the same shape — a swap that is one transaction rather than
two transfers — that is the moment to promote a trade mechanic into
`tangl.mechanics.sandbox`, not now.

## Playing it

```bash
PYTHONPATH=engine/src:apps/pygame/src:worlds/red_paperclip \
  python -m tangl.pygame_client --world red_paperclip
```

```bash
PYTHONPATH=engine/src:worlds/red_paperclip python -m pytest engine/tests/loaders/test_red_paperclip_world.py
```

## The art

<p align="center">
  <img src="../../.github/assets/red-paperclip-district.png"
       alt="The district plate with its six regions boxed and numbered" width="80%">
</p>

Seven plates in `media/`, conformed to the client's own 320x200 and recorded in
`manifest.json` with the hash of the render they came from. `provenance/` keeps
the workflow that made each one, with the endpoint redacted the way
`repartee_loop` does it — an archived record rather than a resumable one.

The six regions were measured against the plate after it was drawn, which is
the way round it has to be: the geometry lives in `script.yaml` and the art
knows nothing about it, so re-rendering the plate means re-measuring them.

At six travel choices the legend fills the lower third of the frame and covers
part of the harbour and airfield boxes. Nothing is lost — the legend row is the
same choice as the hitbox, and hit-testing runs in reverse draw order so the
row wins the pixels it covers — but a plate with more than about five live
regions wants its landmarks in the upper half.

## Authoring it

The trade file is the level design, so it has a tool:

```bash
PYTHONPATH=worlds/red_paperclip python -m red_paperclip
```

```
21 items, 21 traders, 6 hubs: harbor, market, garage, campus, station, airfield
unreachable: nothing

ends the story:
  sourdough_starter    2 trades: wick -> pia
  lighthouse_keys      4 trades: mira -> cass -> olsen -> gunnar
  stuffed_marlin       4 trades: mira -> junie -> finn -> lost_property
  film_role            5 trades: mira -> cass -> olsen -> rusev -> petra
  ostrich_share        6 trades: mira -> cass -> olsen -> rusev -> ilse -> whina
```

`--mermaid` draws the same graph. Both answer the questions you actually have
while editing it: is everything still reachable, is the good ending still
further away than the bad one, did that edit strand an item.

### And the same graph as a planning problem

`--asp GOAL` emits the world in the vocabulary of the archived formal-solver
proof of concept (issue #396): `action/1`, `pre/2`, `add/2`, `del/2`, `init/1`,
`goal/1`. Holding one thing and spending a trader are both linear resources,
and travel is modelled the way it is played, so a minimal plan counts journeys
as well as trades.

That makes this world a generated second fixture for that proposal's first
lane — bounded reachability, finishability, and resource traps — next to the
hand-written apartment-management scenario now restored to
`docs/src/notes/research/formal_solver_poc/`. It adds no dependency here: the
emitter is text, and nothing in the world or the engine imports a solver.

With `clingo` installed (`poetry install --extras solver`) the archived
`engine.lp` plans over it unmodified:

```
minimum horizon 13: 13 actions, 6 trades
  t= 0  go_road_harbor          t= 7  trade_olsen_crab_trap
  t= 1  trade_mira_red_paperclip  t= 8  trade_rusev_outboard_motor
  ...                           t=11  trade_ilse_panel_van
                                t=12  trade_whina_auckland_tickets
```

Two things fall out of that which the Python report cannot see. The optimum is
**six trades and seven journeys**, not six trades — travel is half the cost, and
`routes()` counts only trades. And the plan takes two pairs of trades in one
hub, which is the actual arbitrage insight: cluster your trades by where the
traders stand.

Forcing the sourdough into the trace (`:- not forced. forced :-
occurs(trade_pia_brass_doorknob, T).`) is UNSAT at every horizon to 18 — the
trap proven fatal the same way `eat_icecream` is in the apartment scenario.

`test_the_solver_plan_is_playable` walks that thirteen-move plan through an
ordinary `Ledger`. A model that had drifted from the running world would
produce a plan that stalls partway, so the test is the differential check that
the contract and the game are the same game.
