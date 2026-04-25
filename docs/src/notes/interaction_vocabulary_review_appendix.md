# Interaction Vocabulary Review Appendix

> Status: Non-normative source notes
> Sources: `/Users/derek/Desktop/agent_comments_on_interactivity.md` and
> `/Users/derek/Desktop/storytangl_game_mechanics_survey.md`, reviewed during
> the April 2026 fragment-renderer design pass.

This appendix preserves the useful pressure from the interaction vocabulary
review without making every brainstormed mechanism part of the current contract.
The normative contract lives in
`docs/src/design/service/FRAGMENT_STREAM_CONTRACT.md` and
`docs/src/design/story/INTERACTION_VOCABULARY.md`.

## Central Framing

The review argued that StoryTangl should not try to define a universal game
engine vocabulary. The missing layer is narrower and more useful:

> a cross-client interaction-rendering vocabulary between authored/runtime logic
> and concrete UI affordances.

That layer lets a rich web client render cards, zones, hidden hands, and media
while a CLI still renders the same interaction as text, state, and numbered
choices.

## Adjacent Systems

The review compared StoryTangl with several neighboring systems.

| Reference family | Useful lesson |
| --- | --- |
| Ludii / ludemes | Use containers, components, moves, and end conditions as coverage checks. |
| GDL / General Game Playing | Enumerate legal moves, but keep rule reasoning inside the engine. |
| Zillions / board-game DSLs | Borrow board, piece, move, capture, and skinning ideas without centering boards. |
| BoardGameGeek mechanisms | Use mechanism names as coverage tags, not primitive schema fields. |
| Inform 7 | Preserve scope, visibility, and the distinction between observing and changing. |
| Ink / Yarn / Twine / Ren'Py | Keep runner/view separation and graceful line/option degradation. |
| Vassal / tabletop platforms | Use zones, decks, hands, tokens, logs, and permissions as UI surface examples. |
| WAI-ARIA | Compile StoryTangl semantics down to accessible widgets; do not use ARIA as the game vocabulary. |
| Machinations / Petri nets | Model resource loops as places, tokens, transitions, rates, and ledgers. |
| ECS | Prefer small capabilities/components over a subclass for every interaction kind. |
| xAPI / Open Game Data | Treat interaction requests, user actions, and state transitions as auditable records. |

## Mechanics Survey Highlights

The mechanics survey found a stable engine-side pattern:

- `Game` is the mutable round state.
- `GameHandler` is the stateless rules engine.
- `RoundRecord` is immutable history.
- strategy registries encode opponent behavior and scoring policy.
- handlers expose legal moves and resolve committed moves.

Known mechanics already fit this model:

- rock-paper-scissors and trivial test games
- Blackjack/21/22 sketches
- Nim and token games
- Bag RPS typed-resource commitments
- credentials/Papers-Please-like inspection loops
- Calvin Cards contested card checks
- incremental/resource loops

The conclusion was that UI vocabulary should mirror exposed player surfaces
rather than invent a second game model.

## Adopted Design Pressures

These ideas were adopted into the current vocabulary:

- separate rules, interaction, presentation, and narrative projection
- distinguish affordance from handler-facing move
- represent zones and entities as renderable fragments or group members
- make hidden/visible/revealed state explicit
- keep unavailable choices visible with blocker diagnostics
- preserve action history as an audit trail
- support graceful degradation from rich widgets to text choices
- treat resource and token pools as first-class interaction surfaces

## Deferred Ideas

These remain useful but are intentionally deferred:

- full Ludii-like formal game descriptions
- client-side general game playing or rule inference
- universal board topology
- full telemetry/xAPI compatibility
- a complete interaction record model replacing `RoundRecord`
- presentation-profile negotiation beyond current `ui_hints`
- browser E2E for rich interaction widgets before the widgets stabilize

## Coverage Checklist For Future Fixtures

Future fixtures should exercise one interaction family at a time:

- visible zone plus selectable token
- hidden card or document with reveal state
- unavailable affordance with structured blockers
- quantity or resource-spend payload
- inspect/reveal action that changes visible state
- control update/delete that mutates a prior fragment
- result or user-event fragment that explains an outcome

If a fixture cannot still degrade into readable state plus choices, the contract
is probably leaking too much client-specific UI structure.
