# Command Payload Widget Review Appendix

> Status: reference note from the April 2026 UI handoff package.
> Canonical contract lives in `docs/src/design/story/INTERACTION_VOCABULARY.md`
> and `docs/src/design/service/FRAGMENT_STREAM_CONTRACT.md`.

The design review proposed a useful compromise for classic interactive-fiction
commands: keep the backend authoritative, but let capable clients provide a
command bar and partial local affordances over the visible action surface.

The important idea is not "write a parser in the client." The important idea is
that a command bar can be another payload widget over the same choices that a
button, menu, CLI prompt, or Ren'Py menu would submit.

## Adopt

- Backend resolves all natural-language commands and validates every payload.
- A rich client may use advisory grammar hints for autocomplete, preview,
  highlighting, and did-you-mean UI.
- A plain CLI can submit raw text to the same reserved command choice without
  implementing grammar or autocomplete.
- `choice.accepts` should describe payload shape, not widget class.
- Explicit payloads stay boring:
  - `{}` for pick/button choices
  - `{text: "..."}`
  - `{quantity: 3}`
  - `{piece_ids: ["..."]}`
  - `{parts: {role: subpayload}}` later for composed forms
- Backend failures should return renderable interpretation feedback such as
  ambiguous, unknown noun, blocked, impossible, or validation failed.

## Adjust

- Keep `ProjectedState` as the durable sidecar for ledgers and status; do not
  introduce `projected_value` as an in-stream fragment until the backend has a
  real need for it.
- Keep `zone` and `piece` references id-based and renderable. If an open choice
  references a target zone, that zone must be visible or reachable in the current
  client shell.
- Treat grammar as advisory metadata. It must be derived from the visible turn
  surface and must not contain hidden verbs, nouns, aliases, or target ids.
- Prefer backend raw-command fallback whenever the client is unsure. Local
  resolution is an optimization for ergonomics, not a contract requirement.
- Add `compose` after the simpler payload widgets have settled.

## CLI Floor

The minimum conforming client only needs to reach the gateway API, render text,
and read input. It should still be able to provide every interaction:

- Render prose and known state as text.
- Render zones as labeled lists.
- Render choices as numbered rows with locked reasons.
- For `accepts.kind="text"`, prompt for a line and submit `{text}`.
- For `accepts.kind="quantity"`, prompt for an integer and submit `{quantity}`.
- For `accepts.kind="pieces"`, number the visible target-zone entries and submit
  `{piece_ids}`.
- For `accepts.kind="raw_command"`, prompt for a command line and submit
  `{text}` to the reserved interpretation edge.
- For `compose`, ask the parts sequentially once that payload shape is adopted.

Rich clients can compress those prompts into widgets, but cannot require hidden
client-side rules to make the turn playable.

## Implementation Bias

The next implementation should stay narrow:

1. Make `ChoiceInputView` support `pick`, `text`, `quantity`, and `pieces`.
2. Add canonical fixtures for quantity and sandbox-ish piece/text interactions.
3. Add `raw_command`, grammar preview, and `interpretation` rendering in a later
   slice.
4. Add `compose` after the simple payload shapes are tested.
5. Save browser E2E for after payload widgets and command feedback are stable.
