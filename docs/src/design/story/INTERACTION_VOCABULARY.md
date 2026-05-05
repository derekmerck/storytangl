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

## Client Capability Floor

The gateway API is the only capability every client can be assumed to have:
the service-facing create/update/resolve-choice and info-read operations
described in `docs/src/design/service/FRAGMENT_STREAM_CONTRACT.md`. Every
interaction shape must therefore degrade to text, numbered choices, and simple
prompts.

The CLI floor is:

- render prose and visible state as readable text
- render choices in order, including locked choices and reasons
- collect `text`, `quantity`, and visible `token` selections through prompts
- submit the same `choice_id` plus payload that a rich widget submits
- optionally submit raw command text to a reserved interpretation choice

Web, Ren'Py, Godot, or tabletop-like clients may render richer controls, but
those controls are affordances over the same visible fragments. They are not a
client-side rules runtime.

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

### Payload Contract

`choice.accepts` describes the payload shape requested by an open affordance.
It should stay explicit enough that a CLI can ask for the same value without a
special widget library.

Near-term accepted shapes:

| `accepts.kind` | Payload | CLI rendering |
| --- | --- | --- |
| `pick` or absent | `{}` or no payload | numbered choice |
| `text` | `{text: string}` | line prompt with optional validators |
| `quantity` | `{quantity: int}` | integer prompt with min/max and reason text |
| `tokens` | `{token_ids: string[]}` | numbered entries from a visible target zone |
| `raw_command` | `{text: string}` | command prompt submitted to interpretation edge |

Later, `compose` can combine those simple parts:

```text
accepts:
  kind: compose
  parts:
    - role: amount
      accepts: {kind: quantity, min: 1, max: 7, unit: coin}
    - role: target
      accepts:
        kind: tokens
        min: 1
        max: 1
        constraints: {target_zone_ref: z-room}
```

The corresponding payload should remain explicit:

```text
{
  parts: {
    amount: {quantity: 2},
    target: {token_ids: ["guard"]}
  }
}
```

The client may enforce simple visible validators to avoid bad submissions, but
backend validation is authoritative.

### Command Resolution

Classic IF-style command input is a second affordance over the visible action
surface, not a requirement that every client embed a language parser.

The preferred model is backend-authoritative:

1. The runtime emits ordinary visible choices for the turn.
2. If raw command input is authorized, the runtime also emits a reserved choice
   such as `edge_id="interpret_command"` with `accepts.kind="raw_command"`.
3. A client may render that choice as a command bar or as a CLI prompt.
4. A capable client may use advisory grammar hints for autocomplete, preview,
   and token highlighting.
5. On submit, the backend resolves or rejects the command and returns a normal
   `RuntimeEnvelope`.

Grammar hints are optional and must be treated as denormalized convenience
metadata derived from the visible turn surface. They must not contain hidden
verbs, nouns, aliases, or targets.

When a raw command does not advance the story, the backend should return a
renderable feedback fragment. A future `interpretation` fragment can cover:

- `ambiguous`
- `unknown_verb`
- `unknown_noun`
- `blocked`
- `impossible`
- `validation_failed`

A client without a dedicated interpretation renderer can show the message as
ordinary content.

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
- A CLI command prompt may submit raw text to `interpret_command` without local
  grammar support.
- A Ren'Py view may show a menu plus a small status panel.
- A client without zone support may show the unknown group fallback but should
  still let ordinary choices work.

`ui_hints` can request icons, hotkeys, widget families, or layout preferences,
but hints are advisory. `accepts` and blockers are the portable contract.

## Mechanic Coverage Targets

The vocabulary should cover the current mechanics survey without creating a
client-side rules runtime:

- Classic sandbox IF: visible location state, exits, inventory, blocked actions,
  command text, and backend interpretation feedback.
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

1. Keep `zone` and `token` widgets small and generic; do not add game-specific
   board logic to the client.
2. Add `ChoiceInputView` for `pick`, `text`, `quantity`, and `tokens`.
3. Add canonical fixtures for a quantity interaction and a small sandbox-like
   turn with visible room/inventory zones.
4. Add raw command input only after the payload widgets are tested. It should
   submit to a reserved `raw_command` choice and fall back to backend
   interpretation when no local hint is available.
5. Add `interpretation` rendering after the backend shape exists; fallback to
   content is acceptable before then.
6. Add `compose` after the simple payload widgets are stable.
7. Add browser E2E only after payload widgets and command feedback settle enough
   that tests will not cement an interim UI shape.

## Non-Goals

- No universal rules DSL at the client boundary.
- No client-side game handler or scoring runtime.
- No new fragment hierarchy separate from `BaseFragment` and
  `tangl.journal.fragments`.
- No hard dependency on one UI framework's widget taxonomy.
- No requirement that every client render every rich surface.
