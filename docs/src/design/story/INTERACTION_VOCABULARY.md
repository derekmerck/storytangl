# Interaction Vocabulary

> Status: Directional contract for fragment-era interactivity
> Authority: Story owns interaction meaning; service transports fragments;
> clients render affordances and gracefully degrade unsupported widgets.

StoryTangl is not trying to turn every client into a general game engine. The
engine and handlers own legality, state transitions, scoring, and hidden state.
The client-facing vocabulary should instead describe what kind of player action
is being requested, what state is legible, and how a renderer may collect a
payload.

The current `choice` fragment is the minimal form of this contract. The broader
vocabulary below describes the features we are building toward as fixtures and
widgets grow beyond plain story choices.

## Design Split

Do not collapse these four vocabularies:

| Layer | Question | StoryTangl owner |
| --- | --- | --- |
| Rules model | What is legal and what changes state? | `GameHandler`, VM/story handlers |
| Interaction model | What action shape is requested? | journal fragments and choice `accepts` |
| Presentation profile | What can this client render well? | web, CLI, Ren'Py, future clients |
| Narrative projection | What does this mean in story terms? | prose, dialog, outcome routing |

The renderer consumes interaction requests. It does not infer legal moves from
rules and it does not execute rules locally.

## Core Terms

### Surface

A surface is a renderable interaction area: a choice list, hand, board, document
packet, token pool, shop, map, status panel, or resource economy.

In the fragment stream, surfaces are usually represented by `group` fragments
plus member fragments. `group_type="scene"` is the current top-level shell;
future groups such as `zone`, `hand`, `board`, or `packet` should follow the
same id-reference pattern.

### Entity

An entity is a renderable or targetable object: card, token, document, die,
credential, clue, actor, location, board cell, generator, or inventory item.

At the client boundary, entities should appear as fragments or group members
with small capability fields rather than as deep class hierarchies. A card-like
token might carry `kind`, `display_state`, `zone_ref`, labels, and hints. The
handler still owns the live graph object.

### Zone

A zone is a container or locus for entities: deck, discard, hand, field, bag,
wallet, credential packet, shop, queue, board cell, or inventory.

Zones matter because many interactions are target-constrained:

```text
accepts:
  kind: tokens
  min: 1
  max: 1
  constraints:
    target_zone_ref: f-zone-player-hand
```

Decision legibility requires the referenced zone to be renderable in the current
shell when the choice is open.

### Affordance

An affordance is the user-facing action offer: select, inspect, reveal, play,
discard, buy, spend, take, put, arrange, confirm, cancel, pass, stand, hit,
deny, arrest, or ask.

Today, `ChoiceFragment` is the concrete affordance carrier. `text`, `available`,
`blockers`, `accepts`, and `ui_hints` describe how the client can present and
collect the action.

### Move

A move is the handler-facing committed action. It is what `resolve_choice` or a
future interaction endpoint receives after the renderer collects any payload.

Keep the distinction sharp:

- Affordance: "Show a card from your hand."
- Payload: `{token_ids: ["rust-map-card"]}`
- Move: handler-valid committed action derived from choice id plus payload

### Procedure

A procedure is a structured interaction cycle: single choice, best-of-N contest,
push-your-luck, inspection loop, drafting, bidding, trick, combat round, shop
transaction, resource tick, puzzle attempt, or timed challenge.

Procedures are handler/runtime concepts. Clients should see their state through
fragments: status, zones, tokens, choices, blockers, outcomes, and events.

### Resource And Transaction

Resources are typed quantities: coin, health, time, action points, suspicion,
influence, generator output, token reserves, or production inputs.

Resource-loop interactions should expose ledgers and transactions as renderable
state rather than burying them in prose. The handler owns arithmetic; the client
shows current quantities, available purchases, unavailable reasons, and audit
events.

### Outcome

Outcome is broader than win/lose/draw. A client may need to render success,
failure, partial success, mixed result, continue, abort, route chosen, or
terminal state. Current game enums remain useful, but fragment-era clients need
result fragments or user events that explain what became true.

### Record

`RoundRecord` is the mechanics-specific form of a more general interaction
ledger. Future interaction records should preserve request id, selected move,
public before/after state, result, and notes so replay, diagnostics, generated
prose, and tests can share the same audit trail.

## Interaction Classes

These classes describe effect and rendering expectations:

| Class | Meaning |
| --- | --- |
| observe | Reveal or present information without changing world state. |
| inspect | Examine a target; may reveal hidden fields or consume an action. |
| select | Choose one or more alternatives without necessarily committing. |
| commit | Irreversible or state-changing decision. |
| manipulate | Move, take, spend, place, arrange, buy, or discard. |
| confirm | Acknowledge a result or advance a phase. |
| query | Ask for explanation, hint, rule, or status. |

Plain story choices are `commit` or `confirm` affordances with no additional
payload. Card, token, credential, and resource interactions add target and
constraint metadata.

## Visibility

Hidden information needs a first-class presentation contract. Do not encode all
non-public information as simply absent.

Useful visibility states include:

- private to handler
- known to narrator
- visible to player
- visible to owner only
- inferable or hinted
- revealed after commit
- intentionally misrepresented
- remembered in history but no longer on the surface

The fragment stream should expose only what the client may render. Narrative
composition may know more than the renderer, but that knowledge must not leak
through interaction payloads.

## Graceful Degradation

Every rich interaction should degrade to choices plus readable state.

Examples:

- A web card UI may render hand zones and selectable tokens.
- A CLI may render the same zone as a numbered list and collect a token id.
- A Ren'Py view may show a menu plus a small status panel.
- A client without zone support may show the unknown group fallback but should
  still let ordinary choices work.

`ui_hints` can request icons, hotkeys, widget families, or layout preferences,
but hints are advisory. `accepts` and blockers are the portable contract.

## Mechanic Coverage Targets

The vocabulary should cover the current mechanics survey without creating a
client-side rules runtime:

- Rock-paper-scissors: simultaneous or staged commit, opponent tell, dominance
  relation, round result, best-of-N scoring.
- Blackjack/21/22: deck, hand zones, hidden dealer state, hit/stand, threshold
  and bust result.
- Nim and token games: shared pools, take/put quantity constraints, shrinking
  legal moves, terminal policy.
- Bag RPS and bidding: commit a typed quantity bundle from a reserve.
- Credentials/Papers-Please-like scenes: inspect documents, reveal mismatches,
  request search, pass/deny/arrest disposition.
- Incremental/resource loops: wallets, generators, costs, production ticks, and
  transaction history.

These are fixture and widget targets, not a mandate to add parallel game logic
to the client.

## Near-Term Implementation Targets

The next web/client work should stay small and contract-driven:

1. Promote `zone` and `token` from unknown fallback into real fragment widgets.
2. Render token-selection `accepts` contracts against visible zone fragments.
3. Keep unknown fragment fallback for unsupported future mechanics.
4. Expand fixtures with one additional non-choice-dominant interaction, such as
   a credential packet or simple token pool.
5. Add browser E2E only after the direct fragment widgets are stable.

## Non-Goals

- No universal rules DSL at the client boundary.
- No client-side game handler or scoring runtime.
- No new fragment hierarchy separate from `BaseFragment` and
  `tangl.journal.fragments`.
- No hard dependency on one UI framework's widget taxonomy.
- No requirement that every client render every rich surface.
