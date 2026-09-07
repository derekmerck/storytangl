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

The map plate is not drawn yet: `script.yaml` names `district_map.png` and no
such image exists, so every client falls back to the numbered list, which is
the behaviour that is supposed to happen when a world has no art.

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
hand-written apartment-management scenario. It adds no dependency here: the
emitter is text, and nothing in the world or the engine imports a solver.
