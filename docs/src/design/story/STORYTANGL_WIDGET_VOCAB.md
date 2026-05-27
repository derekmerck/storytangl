# StoryTangl Widget Vocabulary

**Version:** v1.5 · supersedes v1.4
**Layer:** UI Vocabulary (Layer 1 of 3). **Implementation status** across reference clients (Layer 2: web/CLI/Tk), API transport, and engine backend (Layer 3) is tracked in `WIDGET_CONTRACT_RECONCILIATION.md`. **This document is target-truth.**
**Audience:** anyone implementing a StoryTangl client (Vue, CLI, tkinter, Godot, Ren'Py, bespoke), or extending the engine's emitted contract
**Source of truth (for engine model alignment):**
- `tangl.journal.fragments` (fragment types, presentation hints)
- `tangl.service.response` (`RuntimeEnvelope`, `ProjectedState`, section value union)
- `tangl.journal.intent` (typed `Accepts`/`UIHints`; next-pass `Blocker` — see §6)

This document defines the framework-independent rendering contract for the
engine's `RuntimeEnvelope.fragments` and `ProjectedState.sections`. Visual
treatments are author-swappable via bundle customization (§4); the
vocabulary itself is not.

> The Vue components in `apps/web/src/components/story/` are **one**
> reference rendering. A CLI port, a tkinter port, and a Godot port are
> equally valid — they each realize the same widget contract in their own
> medium.

**v1.5 changes summary (against v1.4).** v1.5 adopts the v1.4 genre-audit
additions and reconciles them against the current repo implementation. No
contract breaks; no new top-level vocabulary surfaces:

- Keeps the new **§0.8 "Journal as narrative"** sidebar alongside §0.6
  narrative authoring stance. Codifies the claim that v1.5-conforming envelope
  streams produce legible narrative transcripts as a consequence of
  traversal, without authored prose beyond per-location flavor. Elefant
  Hunt is the worked proof-of-concept.
- Keeps the §1.5 "**Per-cursor projection of shared state**"
  paragraph naming the recipe: shared world, per-cursor visibility,
  same `cursor_id` keyed projection. Resolves an ambiguity that
  credentials, training, and elefant_hunt all hit.
- Keeps the §0.9 **"Genre extensions index"** — short pointer table to all
  `bundles/<name>/EXTENSIONS.md` documents, with one line about what
  each genre stresses in the vocabulary. Helps readers find prior art.
- Updates implementation-status wording for the repo-current typed
  `Accepts` / `UIHints` work: those engine surfaces are implemented;
  `Blocker`, `InterpretationFragment`, full info-channel typing, and
  several Tier P2 surfaces remain pending.
- Aligns the conformance fixture list with the current repository,
  including `compose_payload.json` and the existing proposal fixtures.
- Clarifies `place` payloads as carrying `source_zone_ref` when the
  client selected from a visible source zone.

---

## 0 · Conventions and principles

### 0.1 Tier tags

Every section in this document carries one of four tier tags. These are
not aspirations; they are operational. A reader should always know what's
in the engine right now, what's a near-term proposal, and what's a
longer-horizon direction.

| Tag | Meaning |
|---|---|
| **Tier S** (Stable) | Stable target contract. Clients MAY rely on the subset marked current in `WIDGET_CONTRACT_RECONCILIATION.md`; proposal-only surfaces remain Tier P until implemented and covered by the CLI floor. |
| **Tier P1** (Proposed, next engine epoch) | Concrete proposal with typed Pydantic models below. Additive. Backwards-compatible coercion path planned. |
| **Tier P2** (Proposed, larger) | Architectural direction with sketch-level types. Pending settlement of §7 ontology. |
| **Tier P3** (Genre extensions) | Domain-specific layers (carwars, hana-smuta, etc.). Defer until P1+P2 stabilize. Live in `bundles/<name>/EXTENSIONS.md`. |

Each section's tier is given in its header. Subsections inherit unless
overridden.

### 0.2 The CLI Floor Rule

> A new widget, accepts kind, hint, fragment type, or `value_type` does
> not enter Tier S until a worked CLI rendering exists in
> `engine/contrib/conformance/cli_reference_port.py` and produces output
> for every state described in its spec entry.

This is the single rule that prevents the contract from drifting toward
web-shaped affordances. Drag-drop, animation, hover preview — those are
*reference renderings on top of* a contract that a CLI could fully
execute. A widget whose semantics requires more than a CLI can do is not
in the vocabulary; it is a renderer flourish.

The Python `cli_reference_port.py` is the gating artifact. If a Tier
P1/P2 proposal lands without a CLI rendering, it stays Tier P; it does
not graduate.

**The CLI Floor Rule is the *capability parity* axis of the contract.**
Three sibling parity rules — *information parity* (§5.1 Decision
Legibility), *time parity* (§5.2 Time Parity), and *input parity* (§5.3
Input Parity) — extend the same discipline to other dimensions of the
player's experience. Together they form a four-legged stool: every
richer port may exceed the CLI port, but never trap the player below
CLI-floor accessibility on any axis.

### 0.3 Backend authority

> The backend is authoritative for all state changes. The client MAY
> preview, validate, and decorate, but the client never decides anything
> that affects state without backend confirmation.

§0.3 has three consequences:

1. **The client cannot mutate state without backend confirmation.**
   Grammar hints are advisory; client-side validators are advisory;
   capacity bars compute on the backend; predicates evaluate on the
   backend.
2. **The client cannot perceive state the backend has not sent.** Hidden
   information stays hidden because it never crosses the wire, not
   because the client agrees to look the other way. The client cannot
   implement game logic — including but not limited to: rule resolution,
   win/loss determination, predicate evaluation, hidden-information
   tracking, RNG, scoring, and pacing.
3. **The client cannot assume a coherent backend world model.** State
   may be authored on demand, retroactively committed, or refused. Each
   envelope is self-consistent at render time; the contract makes no
   guarantee that two envelopes describing "the same" world surface are
   explanations of a stable underlying truth. The client renders
   fragments; the backend is the story.

### 0.4 Records over tuples

All ordered key/value structures in this document are arrays of records,
not arrays of tuples. This applies to `KvRow` (§2.5), `compose.parts`
payloads (§6.1.1), and any future ordered-pair surface. Records are
extensible, narrow cleanly in TypeScript and Pydantic, and survive
schema evolution. Tuples are not used at any wire boundary.

### 0.5 Naming changes from prior drafts

Renames ratified in moving from v0.x through v1.5. Applied throughout;
implementations migrating from prior versions update on the schedule in
`WIDGET_CONTRACT_RECONCILIATION.md`.

| Prior | Current | Reason |
|---|---|---|
| `token` (UI piece) | `piece` | Collides with `tangl.core.token.Token` (singleton wrapper). |
| `ledger` (UI section type) | *removed* | Subsumed by annotated `kv_list` rows (§2.5). The engine's `tangl.vm.runtime.ledger.Ledger` keeps the name. |
| `choice_id` (HTTP body) | `edge_id` | Reconciles with `ChoiceFragment.edge_id`. |
| `interpretation.outcome` / `command_text` | `interpretation.result` / `text` | Spec-final names. |
| `token_ids` / `offer_ids` (commit payload) | `piece_ids` | Follows `piece` rename; offers and pieces share one namespace. |
| `cost_preview` (singular field) | `cost_previews: list[CostPreview]` | Multi-axis costs are common (money + time + reputation). Length-1 lists handle singular. |
| `token_offer` fragment type | *removed* | Subsumed by `PieceFragment.realized: bool` (§7.1). |
| `dice_roll` content_format | *removed* | Subsumed by `RollFragment` (§7.3); generalizes to card draws, random tables, etc. |
| `accepts.kind="tokens"` | `accepts.kind="pieces"` | The kind name "tokens" collided with the deprecated `Token` fragment type. The rename to `pieces` mirrors the payload field `piece_ids` and the `PieceFragment` it operates on. (A v1.2 draft proposed `select`; rejected in v1.2.1 review because the payload is specifically `piece_ids`, not a generic selection. `select` stays reserved for a hypothetical future generic selection accepts.) |

### 0.6 Narrative authoring stance

StoryTangl's contract is shaped to interactive fiction rather than
digital tabletop simulation. The runtime is free to author state lazily,
generatively, or in response to player input — there is no
client-readable world model, no determinism guarantee, and no
requirement that previously-rendered fragments correspond to a still-
existing backend object beyond what later envelopes assert.

Games built on StoryTangl are **interactive narrative opportunities**,
not simulated worlds with computable invariants. Bundles that want
simulation-like behavior (deterministic rules, queryable state, fair
RNG) implement those guarantees on the backend; the contract does not
provide them.

Practically, this means:

- A piece's identity might be authored at the moment it's revealed, not
  when the zone is first rendered. A memory game's facedown cards have
  no identity until the player flips them.
- A predicate need not be referentially transparent. The same predicate
  may return different answers on different turns; the contract is that
  the backend has decided, not that any client can reproduce the
  decision.
- An offer (`PieceFragment.realized=False`) need not promise a stable
  catalog. The runtime may synthesize offers on demand and let unsold
  ones evaporate when the player leaves the shop.
- A "world" is whatever the transcript has committed to so far, plus
  whatever the backend is willing to commit to next. The contract makes
  no commitment beyond what the current envelope renders.

This stance is what makes the contract small enough to be portable
across CLI / web / Godot / Ren'Py without losing expressiveness. The
constraints in §0.2 and §5 are downstream consequences of this design
choice.

### 0.7 Three-layer architecture

This document is **Layer 1** of a three-layer separation:

| Layer | Document | What it specifies |
|---|---|---|
| **L1 — UI Vocabulary** | this doc (`STORYTANGL_WIDGET_VOCAB.md`) + `bundles/<name>/EXTENSIONS.md` | What data shapes the player-facing client needs, and at what levels of expressiveness. Target-truth. |
| **L2 — API Transport** | `API_SPEC.md` (forthcoming) | REST endpoints (and other transport mechanisms) that route L1 data needs to L3 capabilities. Optional. Clients sharing an address space with the engine (CLI, embedded ports) skip this layer entirely. |
| **L3 — Engine Capabilities** | `ENGINE_CAPABILITIES.md` (forthcoming) | Python callables that produce the data L1 wants. Ground truth of what's implementable in the current engine. |

Per-surface, the three layers MAY be at different states. A typed
`PiecesAccepts` may be Tier P1 in this spec, partial in the API, and
freshly typed in the engine — all simultaneously, all
during a settling phase. **`WIDGET_CONTRACT_RECONCILIATION.md` tracks
per-surface status across the three layers.** When a row in the
reconciliation tracker reads "implemented" across all three columns,
the surface is settled.

The negotiation direction is **UI-out**: the spec proposes target
contract; the API and engine chase. CLI ports skip L2 and call L3
directly (in-process or via whatever shim a port chooses).

### 0.8 Journal as narrative

A v1.5-conforming envelope stream produces a legible narrative
transcript as a consequence of traversal — without authored prose
beyond per-location and per-event flavor. This is the StoryTangl
thesis claim, made testable.

A rendered CLI transcript of a complete play session — for any
bundle whose envelope stream is contract-correct — should read as a
coherent story. The arc structure (a Proppian arc, in the
narratological sense: departure → trials → boons → return →
recognition, or any equivalent ordering) emerges from the bundle's
graph topology and the sequence of `content`, `attributed`, `roll`,
and `control` fragments, not from a separate narration layer.

The strongest demonstration is **bundle/elefant_hunt** (see
Appendix C): a board game whose mechanics produce a recognizable
naturalist's-journal arc from pure procedural mechanics. The
bundle's per-location prose is thin; the structure does the work.

**Implications for bundle authors.** The journal-as-story claim
holds when:

- Each location, encounter, and outcome emits a `content` fragment
  with enough specificity to be re-readable in transcript form.
  ("Camp. Consumed 3 supplies." is enough; an empty envelope is
  not.)
- `RollFragment.narrative` is populated when the outcome carries
  story weight — losses, captures, revelations.
- `attributed` fragments give recurring NPCs stable speaker names
  so the transcript reads as a cast.
- `update` and `delete` control fragments carry a `content`
  fragment companion when the state change is narratively
  significant ("Zartan is lost to the river.").

**Implications for the contract.** The journal-as-narrative claim
is a **bundle-authoring discipline**, not a contract enforcement
rule. v1.5 does not gate conformance on it. But the conformance
fixture suite SHOULD include at least one "render a complete
session to transcript" test per genre, asserting the transcript is
non-trivial and contains key narrative events. See §10.4.

### 0.9 Genre extensions index

Tier P3 genre conventions live in `bundles/<name>/EXTENSIONS.md`.
The current set:

| Bundle | What it stresses | EXTENSIONS doc |
|---|---|---|
| `carwars` | Vehicle outfitting; slot zones with capacity constraints; RNG stat checks; drag-and-drop with click-pick parity | `bundles/carwars/EXTENSIONS.md` |
| `credentials` | Inspection / verification gameplay; severity-coded findings; mediation move sequencing; backend-authored discrepancies | `bundles/credentials/EXTENSIONS.md` |
| `training` | Scheduled skill progression; mood as growth modulator; scheduled-event checks; per-tag situational effects | `bundles/training/EXTENSIONS.md` |
| `elefant_hunt` | Graph-traversal sandbox; backend-private token pools; hunt resolution as composite roll; journal-as-story validation | `bundles/elefant_hunt/EXTENSIONS.md` |
| `hana_smuta` (sketch) | Card play with `pieces` constraints; hand/field/pile/score zones | `bundles/hana_smuta/EXTENSIONS.md` (TBD) |

Cross-paradigm patterns that emerged from drafting the above and were
NOT lifted to a shared `_common/EXTENSIONS.md` because they're each
already covered by main-spec conventions:

- **Severity emphasis** — `ui_hints.emphasis` and `KvRow.emphasis`
  carry author-stable severity. No genre needed to invent its own;
  the main-spec vocabulary covers credentials findings, carwars
  hazards, training mood states, elefant_hunt threat exits.
- **Gate-check previews** — every genre that surfaces a "you're about
  to roll against difficulty N" preview uses the same shape via
  `ui_hints` with bundle-specific sub-keys (`stat_check` in carwars
  and training, `validity_check` in credentials, `encounter_check`
  in elefant_hunt). These are open hint surfaces by §6.2.1; a unified
  `gate_check` was considered but each genre's preview text and
  callout fields differ enough that forcing a single shape would
  obscure intent. **Genres keep their own; the underlying pattern is
  documented per-extension.**
- **Owner-bound pieces with state** — carwars hunters, training
  inventory unlocks, elefant_hunt mobs all use the same
  `PieceFragment` shape with `owner` and `properties`. No
  cross-genre extension needed.

If a fourth cross-paradigm pattern emerges from future genre work,
`bundles/_common/EXTENSIONS.md` becomes the right home for it. Today
it is not.

---

## 1 · Top-level contract — Tier S

### 1.1 RuntimeEnvelope

```python
# tangl/service/response.py — current shape (Tier S)
class RuntimeEnvelope(InfoModel):
    cursor_id: UUID | None = None
    step: int | None = None
    fragments: list[BaseFragment] = Field(default_factory=list)
    last_redirect: dict[str, Any] | None = None
    redirect_trace: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
```

Each runtime turn produces one envelope **for one cursor** (§1.5). Fields:

- **`cursor_id`** — identifies the journal channel. Stable within a
  session. Changes when state advances; unchanged across `interpretation`
  fragments.
- **`step`** — monotonic counter, per-channel, incremented per state-
  changing turn. Unchanged by `interpretation` fragments.
- **`fragments`** — ordered stream; see §2 for fragment types.
- **`last_redirect` / `redirect_trace`** — runtime introspection for the
  ledger's most recent and historical redirects. Author/debug surface
  only; reader clients ignore.
- **`metadata`** — open dict for cross-cutting hints. Reserved sub-keys:
  `metadata.grammar` (§6.6), `metadata.info_affordances` and
  `metadata.info_state` (§1.6).

### 1.2 Fragment registry and UID stability

Every fragment carries a stable `uid`. Clients maintain a registry keyed
by `uid` across envelopes within a session. The registry is the source
of truth for the rendered scene; envelopes are diffs into it.

Two registry-mutating fragment types exist (§2.7):

- **`update`** control fragments mutate the registry entry at `ref_id`
  by merging `payload` into the existing fragment. The same UID is re-
  rendered in place; **no layout shift**.
- **`delete`** control fragments remove the registry entry at `ref_id`.

**Clients MUST NOT drop fragments they do not understand.** They MUST
render a textual fallback (see §9 parity table) so UIDs remain
resolvable by future control fragments.

### 1.3 ProjectedState

```python
# tangl/service/response.py — current shape (Tier S)
class ProjectedState(InfoModel):
    sections: list[ProjectedSection] = Field(default_factory=list)

class ProjectedSection(BaseModel):
    section_id: str
    title: str
    kind: str | None = None
    value: SectionValue       # discriminated union, see §3
    hints: PresentationHints | None = None
```

`ProjectedState` is a **sidecar** to `RuntimeEnvelope`. Sections are
re-projected every state-changing turn (i.e. when `step` advances).
Shells MAY animate deltas. The `kind` field is a free string for
semantic tagging (`wallet`, `score`, `inventory`, `world_time`, etc.);
ports MAY use it to choose between visual treatments. See §1.6 for the
current conventional `kind` values.

### 1.4 Flow vs rail

A useful organizing distinction for shell designers:

- **Flow content** comes from `RuntimeEnvelope.fragments`. It is
  scene-bound, accumulates as a transcript, and is the locus of player
  interaction.
- **Rail content** comes from `ProjectedState.sections`. It is durable
  across turns, refreshes in place, and represents the world's
  persistent state visible to the player (purse, stats, inventory).

Some widgets exist in both worlds — `kv` (§2.5) is the canonical
example, appearing as a scene-bound *fragment* and as a durable
*section value*. The shape is identical (§2.5); only the routing
differs.

### 1.5 Cursors and journal channels — Tier P1

> Each cursor has its own journal channel. Envelopes are per-channel.
> The backend coordinates shared world state across channels; the
> contract makes no commitment about turn ordering or simultaneous input
> — those are bundle concerns.

**Status (L1):** committed target contract. **Status (L3):**
single-cursor today; multi-cursor channel routing is a proposed extension
awaiting an MVP author. The vocabulary commits to the framing; current
engine and reference UI behave as if there is one cursor.

A **cursor** identifies one participant's traversal through a story.
For solo play, there's one cursor and one channel. For multi-
participant play — Discord-style shared reading, head-to-head gamebooks,
asynchronous group play — there are N cursors, each with its own
channel, each receiving its own envelope stream.

**The contract is cursor-local.** `RuntimeEnvelope.cursor_id` identifies
the channel an envelope belongs to. `step` is monotonic per channel.
Fragment registries are per channel. Two channels may render the same
underlying world state differently (per-participant visibility) and at
different paces (asynchronous turn-taking).

**Shared world coordination is bundle territory.** When two cursors
interact with shared state — one player buys an item from a shop the
other player also frequents — the bundle decides:

- How the runtime serializes commits across channels.
- Whether turn order is round-robin, speed-first, GM-paced, or
  freeform.
- How `update` control fragments propagate to other channels' registries.

The contract makes none of these decisions cheap. It just guarantees
that each channel sees a self-consistent envelope stream.

**`visibility` and the cursor.** `visibility="owner_only"` is
interpreted *against the channel's owner*. A fragment with
`visibility="owner_only"` and `owner=A` is rendered in cursor A's
channel and never crosses into cursor B's. `visibility="hidden"` means
the fragment never reaches *any* channel — it lives backend-side only.

**`visibility` accepts a list of participant IDs.** When a fragment is
visible to a defined audience (team-mates, allies, the GM), the field
takes a list instead of a singleton:

```python
class BaseFragment:
    # ...
    visibility: VisibilityLevel | list[ParticipantId] = "public"
```

Where `VisibilityLevel` is `Literal["public", "owner_only", "hidden"]`
and `ParticipantId` is the cursor's owning account. A list value means
"rendered in any channel whose owner appears in this list." Teams,
asymmetric cooperative roles, and "show this to the GM only" surfaces
all use this form. Routing is a Service-layer concern.

**Per-cursor projection of shared world state.** Many multi-cursor
games share a world surface — a board, a market catalog, an event
queue — across cursors. The rendering recipe is:

1. **The shared element exists once in backend world state.** A market
   zone, a board zone, an animal pool — one canonical object on the
   backend.
2. **Each cursor receives its own projected envelope.** The same
   shared element appears in each cursor's envelope as a fragment.
   `PieceFragment.owner` and `visibility` (per-fragment) control
   which cursor sees what about it.
3. **Updates to shared state propagate as control fragments to
   every relevant cursor's channel.** When cursor A captures an
   animal, cursor B's channel receives a `delete` control fragment
   removing that animal from the shared encounter zone and a
   `content` fragment narrating ("Hunter Red bags a hippo at the
   north watering hole.").

This recipe lets a bundle implement Elefant Hunt's shared animal
pool, a shared trick in trick-taking, a shared marketplace, or
shared narrative arcs without needing a new fragment type. The
`owner` field on pieces (Tier P2; §7.1) is the routing key for
ownership-specific projection. `visibility="public"` means "render
in every cursor's channel"; `owner_only` means "render only in the
owner's channel"; the audience-list form (`visibility: list[ParticipantId]`,
Tier P2 proposal fixture) handles team-scoped visibility.

**The backend is the sole coordinator.** No cursor sees another
cursor's intent before commit. No cursor's projection depends on
inference about another cursor's state beyond what the backend has
chosen to reveal. This is §0.3 backend authority applied to
multi-cursor: the contract for cursor A makes no claim about
cursor B's state that the backend hasn't explicitly projected.

**Single-cursor is the floor case.** Most of this contract is written
as if there's one cursor. The CLI port assumes one cursor. The
`crossroads_inn.json` fixture assumes one cursor. Multi-cursor is the
parallelizable extension; nothing in §§2–4 changes for it.

**What is *not* in scope.** Couch multiplayer (two participants sharing
one rendering surface and one input device) is out of scope by design;
ports that want to host it run two independent client instances
side-by-side, each with its own cursor, and the contract doesn't try to
help. Mechanics that require simultaneous concealed input across
channels (closed drafting, sealed-bid auctions) require cross-channel
coordination that the contract treats as a bundle concern; they are
expressible only via backend orchestration the spec does not make
cheap.

### 1.6 Info channels — Tier P1

> An info channel is an advisory side-projection of world state the
> player MAY query. Info channels are **discovery hints, not mandatory
> client UI**.

**Status (L1):** committed Tier P1 target contract. **Status (L2):** reference
webapp implements `info_affordances` with `query` descriptors against
`/story/info`. **Status (L3):** engine defines typed `InfoAffordance`,
`InfoState`, and `StoryInfoRequest` models, advertises available channels on
runtime envelopes, and routes `/story/info` through the service-info dispatch
surface. Fine-grained dirty-kind tracking remains conservative in v1.

A bundle MAY expose **info channels** — typed sub-surfaces of world
state the player can pull on demand: a map, an inventory, a watch
showing world time, a character sheet, a help screen, a list of active
objectives.

The runtime advertises these channels through two optional metadata
keys on `RuntimeEnvelope`:

```python
class InfoAffordance(BaseModel):
    kind: str               # stable info-channel identifier
    label: str              # short, player-facing
    shortcuts: list[str]    # CLI/keyboard aliases
    query: dict[str, Any] | None = None
    # Opaque query descriptor the backend interprets.
    # Hand-it-back semantic: clients pass it to the info endpoint without
    # inspecting its contents. Bundles decide what query keys mean.
    # Examples: { "type": "map", "format": "tiles" },
    #           { "kinds": ["party", "followers"] },
    #           None  (no descriptor; default info kind is the channel itself)

class InfoState(BaseModel):
    version: int                          # monotonic per cursor
    dirty_kinds: list[str] = []           # changed since prior turn
    available_kinds: list[str] = []       # what's queryable this turn

# RuntimeEnvelope.metadata reserved sub-keys:
#   metadata.info_affordances: list[InfoAffordance]
#   metadata.info_state: InfoState
```

**Advisory, not authoritative.** A port that has room for an info-pill
bar renders the affordances as buttons. A port without that affordance
(CLI, narrow mobile, accessibility-mode) surfaces them through some
other path — a `?` menu, slash commands, keyboard shortcuts, a hidden
drawer. Per §5.3 Input Parity, every info channel MUST be reachable by
some CLI-floor mode; how *prettily* is port-specific.

**Rich rendering is a render-profile concern, not a contract entry.**
An info channel of `kind="map"` might be rendered on the web as an
animated tile grid, on the CLI as `[map: 12 known locations, 3
unexplored]`, on Godot as a 3D minimap. The *data* is canonical; the
*rendering* is the port's call. The contract does not grow
`format: "tiles" | "graph" | "ascii"` fields on sections. Bundles
choose visual treatments via `hints.style_tags`, bundle widget
variants (§4.2), or port-specific profiles (§4.3).

**Every info channel has a `ProjectedState` fallback.** Any `kind`
exposed as an info affordance MUST also be expressible as one of the
five canonical `value_type`s (`scalar`, `kv_list`, `item_list`,
`table`, `badges`) — either directly in `ProjectedState.sections` or
via an info-channel query (§6.7). The fallback exists so a port
that doesn't implement the rich rendering still has *something* to
show. The fallback is the contract surface; the rich rendering is
ornament.

**Conventional `kind` values** (non-normative; bundles MAY add more):
`world_time`, `location`, `inventory`, `agenda`, `objectives`,
`roster`, `wallet`, `help`, `presence`. Ports MAY honor these for
visual treatment selection — a `kind="world_time"` section might
render with a clock icon by default; `kind="map"` might earn a fold-
out treatment. None of this is contract; it's recommended convention.

**Cache invalidation.** `info_state.version` is monotonic per cursor.
`info_state.dirty_kinds` tells the client which channels' cached
projections went stale since the prior turn. A client that does not
cache info channels can ignore `info_state` entirely.

**Single-cursor default.** All info channels are scoped to the cursor
they're advertised in. Per §1.5, multi-cursor bundles project
per-cursor channels; there is no global info-channel surface.

---

## 2 · Fragment widgets — Tier S

Every fragment widget section has the same structure: a Pydantic shape,
a behavior table (required/optional/states/a11y/fallback), and concrete
port sketches.

### 2.1 `content` — Prose block

```python
class ContentFragment(BaseFragment):
    fragment_type: str | Enum = "content"
    content: Any = None              # usually str; may be richer
    source_id: UUID | None = None
    content_format: str | None = Field(None, alias="format")  # md/plain/html
    presentation_hints: PresentationHints | None = Field(None, alias="hints")
```

| | |
|---|---|
| **Required** | `uid`, `fragment_type="content"` |
| **Optional** | `content` (any; usually str), `content_format` (`md`/`plain`/`html`), `hints.style_tags[]`, `hints.style_dict`, `hints.icon`, `source_id` |
| **Container rule** | Flows into the active `scene` group. Interrupts any preceding caption region. |
| **States** | **empty** → skip. **loading** → stream chunks in as they arrive. **error** → render raw string with visible marker. **stale** (after `update` arrives) → re-render in place with same UID; no layout shift. |
| **A11y** | Plain text selectable; if `hints.style_tags` contains `establishing` or `chapter`, treat as `<h*>` landmark. Honor `prefers-reduced-motion`. Time Parity (§5.2): typewriter / staggered-reveal effects MUST be skippable to canonical-instant rendering with a single user action. |
| **Fallback** | Unknown `content_format` → plain text. Unknown hint tag → ignore. |

**Port sketches.** Web: `<p>` or `<article>` honoring `style_tags` via classes. CLI: hard-wrap to terminal width; blank line above/below. tkinter: `Text` widget segment with tag set. Ren'Py / Godot: `RichTextLabel` / narrator say.

### 2.2 `attributed` — Dialog line

```python
class AttributedFragment(ContentFragment):
    fragment_type: Literal["attributed"] = Field("attributed", alias="type")
    who: str
    how: str
    media: str
```

Note the `alias="type"` on `fragment_type` — the wire shape may use
either `fragment_type: "attributed"` or `type: "attributed"`. Clients
MUST accept both. (This is a legacy-compat surface; future fragment
types should not introduce aliases.)

| | |
|---|---|
| **Required** | `uid`, `who`, `how`, `media` (modality: `speech` / `text` / etc.), `content` |
| **Optional** | `hints` |
| **Container rule** | Almost always inside a group with `group_type="dialog"`. The immediately-following `media` fragment with `media_role ∈ {avatar_im, dialog_im}` binds to this line. |
| **States** | **empty** → hide entire line. **loading** → placeholder avatar + ellipsis body. **error** → render `who: content` with `how` dropped. **stale** → same UID swap. |
| **A11y** | Containing dialog group is `role="group" aria-label="dialog"`, `aria-live="polite"`. `who` MUST be announced before content. |
| **Fallback** | If `media` modality is unknown, render as speech. |

**Port sketches.** Web: avatar chip + speaker label + body. CLI: `who [how]> content`, wrapped. tkinter: `Frame` per line: image + label stack. Ren'Py: `define s = Character("Stranger")` + `s "content" (how="low")`. Godot: dialog bubble node with portrait slot.

### 2.3 `media` — Media frame

```python
class MediaFragment(ContentFragment):
    fragment_type: str = "media"
    content: Pathlike | bytes | str | dict | MediaRIT
    content_format: Literal["url", "data", "xml", "json", "rit"]
    media_role: str | None = None       # see below
    scope: str | None = "world"
    staging_hints: StagingHints | None = None
```

| | |
|---|---|
| **Required** | `uid`, `content`, `content_format` |
| **Optional** | `media_role` ∈ `cover_im` / `narrative_im` / `avatar_im` / `dialog_im` / `sfx` / `bgm` / `video`; `scope` ∈ `world` / `scene` / `turn`; `staging_hints` (shape, size, position, transition, duration, timing) |
| **Container rule** | Routed by `media_role`, not by order. `cover_im` is persistent chrome; `narrative_im` belongs to the active content region; `avatar_im` / `dialog_im` bind to the nearest preceding `attributed`; `bgm` is timelined against `staging_hints.media_timing`. |
| **States** | **empty** → hide. **loading** → placeholder box with role label; ARIA busy. **pending** (`content_format="rit"` unresolved) → placeholder marked `data-pending`; swapped in place by later `update` to `url` or `data` — same widget, same DOM node, no reflow. **error** → placeholder + error text; preserve layout. |
| **A11y** | Images need `content` labeled via `hints` or sibling text. Audio/video must expose native controls or keyboard toggle. `prefers-reduced-motion` disables `media_transition`. Time Parity (§5.2): the player MUST always be able to advance past time-bound media (audio/video) with a single action; the player MAY independently choose to let media continue playing. |
| **Fallback** | Unknown `media_role` → render inline. `content_format="rit"` unresolved → pending placeholder. |

**Port sketches.** Web: `<img>` / `<video>` / `<audio>` / placeholder; role maps to CSS class. CLI: `[img: <url>]` / `[♪ <url>]` single-line tokens. tkinter: `Label(image=…)` or placeholder `Frame`; audio/video out-of-band. Ren'Py: `scene <bg>` / `show <sprite>` / `play music` / `play sound`. Godot: `TextureRect` / `VideoStreamPlayer` / `AudioStreamPlayer`.

### 2.4 `group` — Container

```python
class GroupFragment(BaseFragment, extra="allow"):
    fragment_type: Literal["group"] = "group"
    group_type: str | Enum | None = None
    member_ids: list[UUID] = Field(default_factory=list)
    layout_hints: ZoneLayoutHints | None = None       # visual layout (Tier P2; §7.2)
    constraints: ZoneConstraints | None = None        # semantic constraints (Tier P2; §7.2)
```

Note: `DialogFragment(GroupFragment)` exists as a distinct fragment type
(`fragment_type: "dialog"`) with the same structural role. Clients MAY
treat `DialogFragment` and `GroupFragment(group_type="dialog")`
identically.

| | |
|---|---|
| **Required** | `uid`, `member_ids[]` |
| **Optional** | `group_type`, `layout_hints` (Tier P2; visual), `constraints` (Tier P2; semantic) |
| **Canonical `group_type`** | `scene` (turn boundary); `dialog` (consecutive `attributed` lines); `turn` (implicit cursor advancement); `overlay` (modal over active scene; one level of nesting); `status_sidecar` (in-stream kv/item_list rail). Tier P2 adds `zone` (§7.2). |
| **Recommended `zone_role` tags** (Tier P2, non-normative) | `field` (open play area), `hand` (private to owner), `pile` (stack, top-only), `discard`, `slot` (a zone with `constraints.capacity` set), `catalog` (a zone whose members are unrealized pieces, §7.1), `connection` (an edge-shaped placement target, §7.2). These are visual-treatment tags only; their semantics derive from `constraints` and member contents, not from the tag itself. |
| **Container rule** | `scene` defines turn boundaries. `dialog` groups consecutive `attributed`. `turn` is implicit cursor advancement. `overlay` is modal over current scene. `status_sidecar` is an in-stream rail. |
| **States** | **loading** → render members as they arrive, in order. **partial** → ok; finalize on next `update`. **empty** → hide entire group, except: empty zones referenced by an open choice's `accepts.constraints.target_zone_ref` MUST render as a placeholder per §5.1. |
| **A11y** | `overlay` traps focus and exposes `role="dialog" aria-modal="true"`. `dialog` is the `aria-live` host. |
| **Fallback** | Unknown `group_type` → render members flat, no wrapper. |

`group_type` is currently typed as `str | Enum | None` — it accepts any
value. The canonical list above is recommended; ports MUST handle
unknown types via the fallback rule.

### 2.5 `kv` — Key/value rows (unified shape)

The `kv` surface appears in two places — as a scene-bound fragment, and
as a projected section's `value_type`. **Both use the same `KvRow`
shape.** This unification supersedes the older `OrderedTupleDict` form
for `KvFragment` and the simpler `{key, value}` form for
`ProjectedKVItem`.

```python
# tangl/journal/intent.py (Tier P1; ratifies the unified shape)
class KvRow(BaseModel, extra="allow"):
    """Unified key/value row for both scene-bound and projected surfaces."""
    key: str
    value: PrimitiveValue                                          # always primitive

    # Semantic fields — informs rendering across all ports
    max: PrimitiveValue | None = None                              # for "bar" / "fraction" rendering
    delta: int | float | None = None                               # for "+2" deltas
    unit: str | None = None                                        # display unit (e.g. "coin")
    hint: Literal["bar", "fraction", "delta", "tag"] | None = None # rendering mode
    emphasis: Literal["ok", "warn", "danger", "subtle"] | None = None

    # Presentational hints — port-specific styling passthrough
    presentation_hints: PresentationHints | None = Field(None, alias="hints")
```

`KvRow` carries two categories of metadata:

- **Semantic fields** (`max`, `delta`, `unit`, `hint`, `emphasis`)
  inform rendering across *all* ports. CLI honors them by choice of
  glyph/format; web by choice of widget; Godot by choice of scene
  variant.
- **Presentational hints** (`presentation_hints`, the engine's existing
  `PresentationHints` model) are port-specific styling (`style_dict`,
  `style_tags`, `style_name`, `icon`). Ports that don't recognize them
  ignore them — this is correct.

#### 2.5.1 Type narrowing via field population

The flat optional-field shape supports type narrowing without
proliferating `value_type`s. A port that wants to render specific
subshapes does so by narrowing on populated fields:

```python
# Pydantic — required-field overrides for typed authoring/consumption
class StyledKvRow(KvRow):
    presentation_hints: PresentationHints = Field(..., alias="hints")  # required

class BarRow(KvRow):
    max: PrimitiveValue = Field(...)            # required
    hint: Literal["bar"] = Field(...)           # required

class DeltaRow(KvRow):
    delta: int | float = Field(...)             # required
```

```typescript
// TypeScript — intersection narrowing
type StyledKvRow = KvRow & { hints: PresentationHints };
type BarRow      = KvRow & { max: PrimitiveValue; hint: 'bar' };

const isBarRow = (row: KvRow): row is BarRow =>
  row.max !== undefined && row.hint === 'bar';
```

The wire schema is unchanged — exactly one shape, with optional fields.
The narrowing happens at read time in the consumer's type system. This
is also why the project does not add `value_type: "ledger"` or
`value_type: "capacity_ledger"` to `SectionValue`: those subtypes are
populated `kv_list`s, not new value types.

#### 2.5.2 The `kv` fragment

```python
class KvFragment(BaseFragment, extra="allow"):
    fragment_type: Literal["kv"] = "kv"
    content: list[KvRow]                 # was: OrderedTupleDict (Tier P1 migration)
    presentation_hints: PresentationHints | None = Field(None, alias="hints")
```

| | |
|---|---|
| **Required** | `uid`, `content` (list of `KvRow`) |
| **Optional** | `hints.style_tags` (e.g. `status-inline`, `sidecar`) |
| **Container rule** | Inside `status_sidecar` group → side rail; otherwise inline where it appears in the stream. Scene-bound (distinct from durable projected `kv_list` value, §3.2). |
| **States** | **empty** → hide. **loading** → skeleton rows. **error** → render known rows; mark failed. |
| **A11y** | Informational; not focusable by default. Screen readers announce as a list. |
| **Fallback** | Render as `key: value` lines. `hint`/`emphasis` lost in fallback is acceptable. |

**Port sketches.** Web: chip row inline; rail rows in sidecar. CLI: `[status] time=late coin=63 weather=rain`. tkinter: `Frame` of `Label` pairs. Ren'Py / Godot: stat screen / `HBoxContainer`.

### 2.6 `choice` — Player commit point

```python
class ChoiceFragment(BaseFragment, extra="allow"):
    fragment_type: Literal["choice"] = "choice"
    edge_id: UUID | None = None
    text: str = ""
    available: bool = True
    unavailable_reason: str | None = None
    blockers: list["Blocker"] | None = None         # Tier P1 type, see §6.3
    accepts: "Accepts | None" = None                # Tier P1 type, see §6.1
    ui_hints: "UIHints | None" = None               # Tier P1 type, see §6.2
    activation_payload: Any = Field(None, alias="payload")
```

The current engine emits typed `accepts` and `ui_hints`; `blockers`
remain dictionary-shaped until the next intent pass.

| | |
|---|---|
| **Required** | `uid`, `text` |
| **Optional** | `edge_id` (omitted for `interpret_command` reserved choices); `available` (default `true`); `unavailable_reason`; `blockers[]`; `accepts`; `ui_hints`; `activation_payload` |
| **Container rule** | Always emitted within the active `scene` group. Order is presented order; positional hotkey numbering follows order. |
| **States** | **available** → active. **locked** (`available=false`) → disabled but present; show `unavailable_reason`; `blockers[]` is author-facing detail. **freeform** (`accepts.kind ∈ {text, quantity, pieces, place, compose, raw_command}`) → inline input; commit sends typed payload. **loading** → disable group during dispatch. **error** → re-enable; mark failed attempt. |
| **A11y** | Group is `role="group" aria-label="choices"`. **The position of a choice in the open-choice list is its default hotkey** (`1`–`9`, then `a`–`z`). `ui_hints.hotkey` overrides the default for specific choices (e.g., `>` for `interpret_command`). Hotkeys are suppressed when a text input has focus; Esc returns to choice-selection mode. ↑/↓ cycles; Enter commits; Esc cancels freeform. Focus returns to primary choice of new turn after dispatch. Hit target ≥ 44×44 on touch. Locked choices remain focusable for screen reader stability. |
| **Fallback** | Unknown `accepts.kind` → plain button posting empty payload, with warning. Unknown `ui_hints.widget` → default widget for `accepts.kind`. |

**Port sketches.** Web: button list; freeform → `<input>` + submit. CLI: `1) Pay the forty silver.` … `> ` prompt; `(locked: reason)` suffix for unavailable. tkinter: `Button` stack; `Entry` for freeform; `state="disabled"` for locked. Ren'Py: `menu:` block; `if`-gated for locked; `renpy.input` for freeform. Godot: `VBoxContainer` of `Button`; `disabled=true` for locked; `LineEdit` for freeform.

### 2.7 `control` — Silent fragment mutation

```python
ControlFragmentType = Literal["update", "delete"]

class ControlFragment(BaseFragment, extra="allow"):
    fragment_type: ControlFragmentType = "update"
    reference_type: str | Enum = Field("content", alias="ref_type")
    reference_id: Identifier = Field(..., alias="ref_id")
    payload: UnstructuredData | None = None    # required for update
```

Note the wire aliases: `ref_type` and `ref_id` are the JSON field names;
`reference_type` and `reference_id` are the Python attributes. Clients
see the aliased forms.

| | |
|---|---|
| **Required** | `uid`, `fragment_type ∈ {update, delete}`, `ref_type`, `ref_id` |
| **Optional** | `payload` (required for `update`) |
| **Container rule** | Not rendered. Mutates the local fragment registry by UID; triggers re-render of target. |
| **States** | **applied** (normal). **unresolved** (target UID missing) → log to author surface; do not crash; do not surface to player. |
| **A11y** | Invisible. Re-render the target node in place — do not move focus. |
| **Fallback** | None user-visible. |

**All ports** — local registry swap by UID; no reflow.

### 2.8 `user_event` — Toast / silent stash

```python
class UserEventFragment(BaseFragment, extra="allow"):
    fragment_type: Literal["user_event"] = "user_event"
    event_type: str | None = None
    # `extra="allow"` permits `content` and per-event-type fields
```

| | |
|---|---|
| **Required** | `uid`, `event_type` |
| **Optional** | `content` (any), per-event-type fields (open via `extra="allow"`) |
| **Container rule** | Floats above the current shell. Never inserts into scene flow. |
| **States** | **empty** → skip. **unknown event_type** → stash on user record, no UI. |
| **A11y** | `role="status" aria-live="polite"`; Esc dismisses. Auto-dismiss 3s; story MAY extend. |
| **Fallback** | Drop quietly; log to author surface. |

**Port sketches.** Web: bottom toast. CLI: `* <event_type>: <content>` single line. tkinter: transient `Toplevel`. Ren'Py: `notify()`. Godot: `Popup` with autohide.

### 2.9 `interpretation` — Backend command-resolution feedback (Tier P1)

This fragment is Tier P1 — its full type definition lives in §6.4. It is
listed here for proximity to the other fragment widgets. Clients SHOULD
render it in scroll order alongside `content` fragments. It does not
advance the cursor.

---

## 3 · ProjectedState section values — Tier S

### 3.1 The `value_type` discriminated union

```python
SectionValue = Annotated[
    ScalarValue | KvListValue | ItemListValue | TableValue | BadgeListValue,
    Field(discriminator="value_type"),
]
```

Five canonical value types. Each has a stable shape, port-independent
semantics, and a sensible CLI rendering. **No additional `value_type`s
are proposed.** Subtypes that look like new value types are populated
`kv_list`s (see §2.5.1).

### 3.2 Shapes and renderings

| `value_type` | Shape | Web sketch | CLI sketch | tkinter sketch |
|---|---|---|---|---|
| `scalar` | `value: PrimitiveValue` | tile / badge | `title: value` | large `Label` |
| `kv_list` | `items: list[KvRow]` (§2.5) | rail rows; chips | aligned columns | `Frame` of pairs |
| `item_list` | `items: list[{label, detail?, tags?}]` | roster | `- label (detail) [tags]` | listbox + detail |
| `table` | `columns: list[str]`, `rows: list[list[PrimitiveValue]]` | `<table>` | aligned columns | `ttk.Treeview` |
| `badges` | `items: list[str]` | chips | `[tag1][tag2]` | small labels |

`kv_list` is the workhorse: it absorbs ledger-like data, capacity bars,
deltas, and styled rows via the field-population mechanics in §2.5.1.
`table` covers tabular data where row-major presentation matters
(armor-by-location, leaderboard); a row width validator on the engine
side ensures `len(row) == len(columns)`.

### 3.3 Section hints

```python
class ProjectedSection(BaseModel):
    section_id: str
    title: str
    kind: str | None = None              # semantic tag, e.g. "wallet", "score"
    value: SectionValue
    hints: PresentationHints | None = None
```

`kind` is a free string used by ports to choose between visual
treatments (`wallet` → coin icon, `score` → leaderboard skin, etc.). It
does not discriminate the value union. The v1.5 conventional `kind`
values (`world_time`, `location`, `inventory`, etc.) are documented in
§1.6.

`hints` is the existing `PresentationHints` model (style_name,
style_tags, style_dict, icon). Same surface as on every other fragment
that carries hints.

---

## 4 · Bundle customization — Tier S

A story bundle MAY override the following. Everything else is stable
vocabulary and MUST NOT be redefined.

### 4.1 What is stable (not author-swappable)

- The set of canonical `fragment_type`s and their required fields.
- The canonical `group_type`s listed in §2.4.
- The set of canonical `value_type`s in §3.1.
- The accessibility contract throughout §2.
- The four conformance contracts in §5 (CLI Floor + Information / Time /
  Input Parity).
- Fallback behavior: never silently drop fragments.

The §1.5 cursor-channel routing model and §1.6 info-channel rules are
Tier P1 in v1.5 — committed target contract, not yet fully engine-shipped.
When they graduate to Tier S (engine + CLI reference port implemented),
they join the list above.

### 4.2 What a bundle MAY override

```python
bundle = {
    "id":      "crossroads_cyberpunk",
    "name":    "Crossroads // Neon Cut",
    "version": "0.1.0",

    # CSS / theme tokens; flat key→value
    "tokens": {
        "--paper":        "#0a0510",
        "--ink":          "#e9f3ff",
        "--accent":       "#ff2e93",
        "--font-serif":   "'Space Grotesk', sans-serif",
        "--font-mono":    "'JetBrains Mono', monospace",
        "--motion-scale": 0.6,
    },

    # Shell selection; advisory — client falls back to default if absent
    "shell": "dossier",                      # "scroll" | "dossier" | "stage_log"

    # Per-widget variant overrides — variants share the same props contract
    "widgets": {
        "choice": "TerminalChoice",
        "media":  "HolographicMedia",
    },

    # Custom fragment types the story invents — must include text fallback
    "handlers": {
        "dice_roll": "renderDiceRoll",
    },
}
```

**Rules.**

1. Variants receive the **same props contract** as the default widget.
   They may not change required/optional field names.
2. A custom fragment handler MUST provide a text fallback (per §9 parity
   table) so other ports still work.
3. `shell` is advisory; a port that lacks the named shell falls back to
   its default.
4. Tokens are flat key→value; nothing nested. Variables prefixed with
   `--` are CSS; `motion-*` are honored by all ports including non-web.

### 4.3 Profiles — port conformance subsetting (Tier P2)

Bundles MAY declare which **profiles** they exercise:

```python
bundle["profiles"] = ["card", "location", "actor"]
```

A port that implements a strict subset of profiles is still a
conforming StoryTangl client for any bundle whose `profiles` are a
subset of the port's supported profiles. The minimum conforming
card-game client implements `card`, `hand`, `field`, `pile`,
`score_pile`, `discard`, `accepts.kind ∈ {pick, pieces}`, plus the §3
value types it uses. This is the path by which (e.g.) a hana-smuta
tkinter board ships without implementing the full §7 vocabulary.

Profiles are non-normative: a port that does not know a profile falls
back to generic widget rendering. See §7.5 for the profile registry.

---

## 5 · Conformance contracts

Four parity rules govern all ports. CLI Floor (§0.2) handles capability
parity; the three rules below handle information, time, and input
parity. Together they form the four-legged stool: every richer port may
exceed the CLI port, but never trap the player below CLI-floor
accessibility on any axis.

### 5.1 Decision Legibility Contract

> **When a fragment's state is referenced by an open `choice`'s
> `accepts` constraints, `blockers[]`, or `unavailable_reason`, the
> client MUST render enough of that fragment's state for a player to
> evaluate the choice without out-of-band knowledge.**

> `visibility="hidden"` fragments are never referenced by open choices
> in any cursor's channel. `visibility="owner_only"` fragments are
> referenced only in their owner's channel. `visibility=[...]`
> (audience list) fragments are referenced only in channels whose
> owner appears in the list.

This rule strengthens §2's generic rendering rule. Existing widgets
(prose, media, choice) do not gate legal choices on rendered state, so
"render however you like" suffices. Interactive surfaces (§7) do, and
must therefore meet a stricter floor: **if the player can choose it,
the player can see it.**

**Operational tests.**

- An open `choice.accepts.constraints.target_zone_ref = Z` means zone
  `Z` MUST be rendered with all visible-to-this-cursor member pieces
  visible.
- A `blockers[]` entry with `refs` citing `piece_id = P` means piece
  `P` MUST be rendered in this cursor's channel.
- An `unavailable_reason` mentioning a state property MUST resolve from
  rendered state alone (no out-of-band knowledge required).

This rule is **conformance-checkable**: a test sweeps every open turn
for referenced UIDs and verifies each is on screen. The test lives in
`engine/contrib/conformance/legibility.py` (Tier P1) and runs against
every fixture as part of CI.

### 5.2 Time Parity Rule

> **Player time spent on any fragment is bounded by the player's
> choice, never by the author's pacing.**

*Visual ritual* (typewriter prose, animations, transitions,
structured-outcome reveal) MUST be skippable with a single user action
to a state observably equivalent to the CLI port's rendering of the
same envelope. Authors choose default pacing; players choose actual
pacing.

*Time-bound media* (audio, video) has its own playback contract. The
player MUST always be able to advance past it with a single user
action; the player MAY independently choose to let media continue
playing in the background. The player is never trapped waiting for
media to finish.

A port that adds presentation time over CLI-floor latency without
honoring this rule is non-conforming. Bundles MAY tune skip affordances
via advisory `RitualHints` (§7.3 — `skip_label`, `auto_skip_after_seen`,
`allow_replay`) but cannot suppress skip itself. **Author intent for
dramatic pacing belongs in prose structure** (fragment boundaries that
require advancement), **not in time-elapse**.

**Operational tests.**

- Time-to-canonical-outcome on the web port (with skip invoked) MUST
  equal CLI-port time-to-canonical-outcome for the same envelope.
- For a `media` fragment with `media_role ∈ {bgm, video, sfx}`, an
  "advance" affordance MUST be reachable while the media is still
  playing.
- For any `RollFragment`, the player MUST reach the next turn's choices
  within one user action regardless of `ritual_hints.duration_ms`.

### 5.3 Input Parity Rule

> **Every interaction the contract supports MUST be reachable via the
> CLI port's input modes (numbered selection, raw text entry).**

Richer port-specific input modalities — drag-and-drop, gestures, voice,
hotkey accelerators, gamepad — are presentation enhancements that MAY
be added on top, but MUST NOT be the only way to perform any
interaction.

A port that requires drag-and-drop with no click-pick fallback, or
hotkey-only paths with no visible-button fallback, or info-pill-only
paths with no slash-command or `?` menu fallback, is non-conforming.

**Worked examples.**

- A `place` accepts choice rendered as drag-drop on the web port (per
  `ui_hints.drag`, §6.2.1) MUST also offer the two-step click-pick path
  (pick piece, pick target zone). The CLI port renders only the click-
  pick path.
- A `raw_command` accepts choice with a typeahead grammar overlay MUST
  also accept plain text submission with no overlay. The CLI port
  renders only plain text.
- A choice list's positional hotkey numbering (§2.6) is the keyboard
  realization of the same choice list visible as buttons. Ports MAY add
  hotkeys; ports MUST keep the visible buttons reachable by tap/click.
- An info-affordance bar (§1.6) is one way to expose info channels.
  Ports without room for it (CLI, narrow viewports, accessibility mode)
  MUST expose the same info channels through some CLI-floor mode —
  typically slash commands derived from `info_affordances[].shortcuts`,
  or a single `?` menu.

---

## 6 · Tier P1 — typed contract surfaces

Everything below types fragment interiors without changing the outer
fragment envelope shape. `Accepts` and `UIHints` are implemented in the
engine; `Blocker`, `InterpretationFragment`, and several metadata subkeys
remain the next dictionary-shaped sub-surfaces to promote.

### 6.1 Typed `Accepts`

The engine's `ChoiceFragment.accepts` is a Pydantic discriminated union in
`tangl/journal/intent.py`:

```python
# tangl/journal/intent.py — Tier P1
from typing import Annotated, Literal, TypeAlias
from pydantic import BaseModel, ConfigDict, Field

class CostPreview(BaseModel):
    """Advisory cost display. Never gates a commit; backend re-validates."""
    ledger_key: str           # which projected section to debit
    delta: int | float
    unit: str | None = None

class PieceConstraints(BaseModel):
    """Constraints on a kind='pieces' or kind='place' selection."""
    same_property: list[str] | None = None
    different_property: list[str] | None = None
    target_zone_ref: str | None = None    # uid of group with group_type=zone
    source_zone_ref: str | None = None    # uid of group supplying movable pieces
    target_kind: list[str] | None = None  # filter by piece.kind, e.g. ["weapon"]
    predicate_ref: str | None = None      # opaque, story-registered (§7.4)

class LengthValidator(BaseModel):
    kind: Literal["length"] = "length"
    min: int | None = None
    max: int | None = None

class RegexValidator(BaseModel):
    kind: Literal["regex"] = "regex"
    pattern: str
    flags: str | None = None
    message: str | None = None

class EnumValidator(BaseModel):
    kind: Literal["enum"] = "enum"
    values: list[str]
    case_sensitive: bool = False

class BackendValidator(BaseModel):
    kind: Literal["backend"] = "backend"
    """Opaque marker. Only the backend can evaluate this validator."""

Validator: TypeAlias = Annotated[
    LengthValidator | RegexValidator | EnumValidator | BackendValidator,
    Field(discriminator="kind"),
]

class PickAccepts(BaseModel):
    kind: Literal["pick"] = "pick"
    cost_previews: list[CostPreview] = Field(default_factory=list)

class TextAccepts(BaseModel):
    kind: Literal["text"] = "text"
    required: bool = True
    placeholder: str | None = None
    validators: list[Validator] = Field(default_factory=list)

class QuantityAccepts(BaseModel):
    kind: Literal["quantity"] = "quantity"
    required: bool = True
    min: int | None = None
    max: int | None = None
    step: int = 1
    unit: str | None = None
    ledger_ref: str | None = None     # show "you have N" from this section
    cost_previews: list[CostPreview] = Field(default_factory=list)

class PiecesAccepts(BaseModel):
    """Select N pieces from a constrained source.
    Renamed from 'tokens' (kind name) in v1.2 — the prior name collided
    with the deprecated Token fragment type. A v1.2 draft proposed
    `select` but was reverted in v1.2.1: payload is specifically piece_ids,
    so the kind name should track that. `select` stays reserved for any
    future generic selection accepts. Wire payload field is piece_ids."""
    kind: Literal["pieces"] = "pieces"
    min: int = 1
    max: int = 1
    constraints: PieceConstraints | None = None

class PlaceAccepts(BaseModel):
    """Move a piece from a source zone into a target zone, slot, or edge."""
    kind: Literal["place"] = "place"
    source_zone_ref: str | None = None       # where the piece comes from
    target_zone_ref: str | None = None       # specific target zone/slot
    edge_ref: str | None = None              # for network/route building (§7.2)
    predicate_ref: str | None = None         # for one-of-N matching targets
    source_constraints: PieceConstraints | None = None
    required: bool = True

class ComposePart(BaseModel):
    role: str                            # stable string the backend keys on
    accepts: "NonComposeAccepts"

class ComposeAccepts(BaseModel):
    kind: Literal["compose"] = "compose"
    parts: list[ComposePart]

class RawCommandAccepts(BaseModel):
    kind: Literal["raw_command"] = "raw_command"

NonComposeAccepts: TypeAlias = Annotated[
    PickAccepts | TextAccepts | QuantityAccepts | PiecesAccepts
    | PlaceAccepts | RawCommandAccepts,
    Field(discriminator="kind"),
]

Accepts: TypeAlias = Annotated[
    PickAccepts | TextAccepts | QuantityAccepts | PiecesAccepts
    | PlaceAccepts | ComposeAccepts | RawCommandAccepts,
    Field(discriminator="kind"),
]
ComposePart.model_rebuild()
```

#### 6.1.1 Commit payload shapes

The wire payload is shape-keyed by the choice's `accepts.kind`, **not**
by an explicit discriminator on the payload itself. The backend has the
open-choice list and resolves the expected shape via `edge_id`. This
keeps payloads short and matches existing webapp behavior.

| `accepts.kind` | Wire payload | Notes |
|---|---|---|
| `pick` | `{}` (empty object) | The `edge_id` is the answer. |
| `text` | `{ "text": str }` | |
| `quantity` | `{ "quantity": int }` | |
| `pieces` | `{ "piece_ids": [str, ...] }` | `min ≤ len ≤ max`. (Renamed from `tokens` in v1.2; the `select` rename was reverted in v1.2.1.) |
| `place` | `{ "piece_id": str, "source_zone_ref": str \| null, "target_zone_ref": str \| null, "edge_ref": str \| null }` | Move a single piece from an optional source into a single target. Exactly one of `target_zone_ref` or `edge_ref` is present. |
| `compose` | `{ "parts": { role: subpayload, ... } }` | Each subpayload follows its part's `accepts.kind`. |
| `raw_command` | `{ "text": str }` | Reserved for `interpret_command`-shaped choices. |

Concrete `compose` example — "give 2 coins to guard":

```json
{
  "edge_id": "e-give",
  "payload": {
    "parts": {
      "amount": { "quantity": 2 },
      "target": { "piece_ids": ["pc-guard"] }
    }
  }
}
```

Concrete `place` example — "mount the flamethrower on the front":

```json
{
  "edge_id": "e-mount",
  "payload": {
    "piece_id": "pc-flamethrower",
    "source_zone_ref": "z-vehicle-loose",
    "target_zone_ref": "z-front-mount"
  }
}
```

Concrete `place` (edge variant) — "lay track on the Toledo-Chicago connection":

```json
{
  "edge_id": "e-lay-track",
  "payload": {
    "piece_id": "pc-train-blue",
    "source_zone_ref": "z-train-yard",
    "edge_ref": "edge-toledo-chicago"
  }
}
```

#### 6.1.2 Validator authority

- Non-`backend` validators (length, regex, enum) are advisory. The
  client SHOULD evaluate them inline before allowing commit.
- The backend re-evaluates ALL validators on commit and is
  authoritative.
- A backend-side validation failure surfaces as an `interpretation`
  fragment with `result="validation_failed"` (§6.4). Step does not
  advance.

### 6.2 Typed `UIHints`

```python
class UIHints(BaseModel, extra="allow"):
    hotkey: str | None = None             # "1"-"9", "a"-"z", or symbolic
    icon: str | None = None
    emphasis: Literal["primary", "subtle", "warning", "danger"] | None = None
    widget: str | None = None             # variant override id from bundle.widgets
    cost_previews: list[CostPreview] = Field(default_factory=list)
```

`UIHints` is deliberately open (`extra="allow"`) — it's a hint surface,
not a contract surface. Authors may add hints freely; ports ignore
unknowns. The named fields are documented hints with defined semantics.

#### 6.2.1 Genre-specific UIHints sub-shapes (Tier P3)

Genre layers MAY define additional typed sub-shapes on `UIHints` for
their domain. These live in `bundles/<genre>/EXTENSIONS.md`, not in the
main spec. Examples:

- `ui_hints.drag` — drag-and-drop affordance for `place`-accepting
  choices. Floor rule per §5.3 (Input Parity): every drag interaction
  MUST have a click-pick fallback.
- `ui_hints.stat_check` — pre-roll difficulty preview for
  `RollFragment`-triggering choices.
- `ui_hints.cost_breakdown` — itemized cost display.

A port that does not know a genre-specific hint ignores it. The
behavior without the hint MUST still be reachable.

### 6.3 Typed `Blocker`

```python
class Blocker(BaseModel, extra="allow"):
    code: str                             # author-stable, e.g. "needs_key"
    message: str                          # player-facing, may be templated
    refs: list[str] = Field(default_factory=list)  # uids referenced by message
```

Each blocker entry combines an author-stable identifier (for predicates
and testing), a player-facing message (which MAY reference rendered
state per §5.1), and a list of UIDs the message references. The
Decision Legibility Contract requires every UID in `refs` to be
rendered.

### 6.4 `InterpretationFragment`

```python
InterpretResult = Literal[
    "ambiguous",
    "unknown_verb",
    "unknown_noun",
    "blocked",
    "impossible",
    "validation_failed",
]

class InterpretationFragment(BaseFragment):
    fragment_type: Literal["interpretation"] = "interpretation"
    result: InterpretResult
    text: str                             # the player's raw input
    message: str                          # human-readable reason
    candidates: list[UUID] | None = None  # edge_ids when result="ambiguous"
    blocked_reason: str | None = None     # for result="blocked"
    hint: str | None = None               # optional one-line nudge
```

| | |
|---|---|
| **Required** | `uid`, `result`, `text`, `message` |
| **Optional** | `candidates[]` (required when `result="ambiguous"`); `blocked_reason` (used when `result="blocked"`); `hint` |
| **Container rule** | Flows into the active scene. Accumulates as transcript entries. |
| **State machine** | **Does NOT advance the cursor.** `step` is unchanged from the prior envelope; choices remain open. |
| **A11y** | `role="status" aria-live="polite"`. |
| **Fallback** | A port that doesn't model `interpretation` MAY render `message` as a `content` fragment. |

**Why a dedicated fragment.** Replay/audit parity wants the failure to
be structured. Ports that render the parser-failure transcript (IF-
style) benefit from a stable shape. The cost is one fragment type that
other ports can fall back to prose for.

### 6.5 Reserved `interpret_command` edge

When a story bundle authorizes a command bar for the current turn, the
runtime MUST inject an additional `ChoiceFragment` into the open-choice
list:

```json
{
  "uid": "f-interpret-command",
  "fragment_type": "choice",
  "edge_id": "interpret_command",
  "text": "Try a command.",
  "available": true,
  "accepts": { "kind": "raw_command" },
  "ui_hints": { "hotkey": ">" }
}
```

The client's command bar wraps this choice. Submission posts a
`raw_command` payload (`{ text: "..." }`). The backend either:

- Resolves the text to a real edge, applies it, and returns a normal
  envelope (cursor advances), OR
- Returns an `InterpretationFragment` describing the failure mode
  (cursor unchanged, choices intact).

A port that does not implement a command bar simply ignores the
`interpret_command` choice (which renders as a button labeled "Try a
command" with a text input — fine fallback).

### 6.6 `metadata.grammar`

Per the architecture commitment in `apps/web/notes/ARCHITECTURE.md`,
the grammar hint lives at `RuntimeEnvelope.metadata.grammar`. This is a
typed sub-key validated on serialization, **not** a top-level field on
`RuntimeEnvelope`.

```python
class GrammarVerb(BaseModel):
    verb: str
    aliases: list[str] = Field(default_factory=list)
    frames: list[str] | None = None       # "take {noun}", "take {noun} from {noun}"

class GrammarNoun(BaseModel):
    noun: str
    aliases: list[str] = Field(default_factory=list)
    piece_ids: list[str] = Field(default_factory=list)

class GrammarHint(BaseModel):
    verbs: list[GrammarVerb] = Field(default_factory=list)
    nouns: list[GrammarNoun] = Field(default_factory=list)
    placeholder: str | None = None
    examples: list[str] = Field(default_factory=list)
    resolve_to: str | None = None         # default: "interpret_command"
```

**Synthesis.** The grammar hint is a **denormalized projection of the
visible action surface** for the current turn. It MUST NOT contain any
verb, noun, or alias that does not already correspond to a visible
`choice` or `piece` in this cursor's channel. It is a UX affordance,
never a security boundary.

The Story layer is the natural synthesizer (it knows what is
narratively visible). The Service layer is responsible for serializing
it into `metadata.grammar` on egress.

**Absence.** When `metadata.grammar` is absent, the command bar simply
submits raw text. No preview, no highlighting. Identical to a CLI
port.

### 6.7 HTTP API

```python
# tangl/service/http/story.py — Tier P1 target
class ChoiceRequest(BaseModel):
    edge_id: UUID                        # was: choice_id (deprecated alias)
    payload: dict[str, Any] | None = None  # validated against Accepts at runtime

@router.post("/story/do", response_model=RuntimeEnvelope)
def do_story_action(req: ChoiceRequest, ...) -> RuntimeEnvelope: ...

@router.get("/story/update", response_model=RuntimeEnvelope)
def get_story_update(...) -> RuntimeEnvelope: ...

@router.get("/story/info", response_model=ProjectedState)
def get_story_info(
    kind: str | None = None,
    query: str | None = None,   # JSON-encoded InfoAffordance.query descriptor
    ...,
) -> ProjectedState: ...
```

Four changes from the current `openapi.json`:

1. **`choice_id` → `edge_id`.** Deprecation: accept both names for one
   minor version, emit a header warning when `choice_id` is used. Then
   strict.
2. **Typed responses on `/story/do` and `/story/update`** —
   `response_model=RuntimeEnvelope` lets the OpenAPI doc express the
   full contract, which lets `apps/web` regenerate `api.d.ts` cleanly.
3. **Payload validation by edge.** The backend looks up the choice by
   `edge_id`, retrieves its declared `Accepts.kind`, and validates the
   posted payload against the matching `*Payload` shape (§6.1.1).
   Failures are surfaced as `InterpretationFragment` with
   `result="validation_failed"`.
4. **`/story/info` accepts an opaque query descriptor.** The
   `InfoAffordance.query` payload (§1.6) is JSON-encoded and passed as
   the `query` parameter; `kind` filters the response to a single info
   channel. Both parameters are optional. The backend interprets the
   descriptor however it wants; clients pass it back without inspecting
   contents. **The contract surface is the `InfoAffordance.query` shape
   in §1.6, not the URL routing here** — the transport may evolve (POST
   body, separate endpoint per kind, etc.) without breaking L1
   vocabulary clients, as long as the query descriptor is honored. The
   v1.2 draft proposal of `GET /story/info/{kind}` was rejected in
   v1.2.1 review because the URL-path approach baked `kind` into the
   transport and didn't accommodate richer query payloads.

---

## 7 · Tier P2 — interactive surface vocabulary (proposed, larger)

This section uses the settled §0.5 ontology rename (`token` → `piece`) and
still depends on the predicate registration protocol (§7.4).
Implementations MAY consume this as a roadmap; it is partial contract.

### 7.1 `PieceFragment` — Identified surface element with state and lifecycle

```python
class PieceFragment(BaseFragment):
    fragment_type: Literal["piece"] = "piece"
    piece_id: str
    kind: str                             # free string: "card", "tile", "die", "weapon", ...
    properties: dict[str, Any] = Field(default_factory=dict)
    visibility: VisibilityLevel | list[ParticipantId] = "public"   # see §1.5
    display_state: str | None = None      # "face_up", "face_down", "selected", ...
    zone_ref: str | None = None
    presentation_hints: PresentationHints | None = Field(None, alias="hints")

    # Multi-cursor / ownership
    owner: ParticipantId | None = None    # cursor whose channel "owns" this piece

    # Lifecycle and economics
    realized: bool = True                                  # False = offer (not yet minted)
    cost: list[CostPreview] = Field(default_factory=list)  # for offers; multi-axis ok
    available: bool = True                                 # render disabled when False
    unavailable_reason: str | None = None                  # accompanies available=False

    # Geometry (interpretation depends on parent zone's layout_hints)
    position: dict[str, Any] | None = None
    # for layout_hints.grid → {row, col}
    # for layout_hints.graph hex → {q, r}
    # for free-form spatial → {x, y}
    # absent → piece occupies the zone without a positional binding
```

A piece is an addressable, state-bearing element of a game surface
(card, tile, die, counter, weapon, generator, location, actor).

**Lifecycle.** A piece is either **realized** (`realized=True`, has a
backend-issued UID, exists in world state) or an **offer**
(`realized=False`, has a bundle-stable id, will be minted on commit).
Both share `piece_id` and `PieceFragment` shape — there is no separate
`token_offer` fragment type. Catalogs are zones whose members are
unrealized pieces. Shop transactions, salvage piles, quest rewards,
and crafting outputs all use this lifecycle.

**Ownership and visibility.** `owner` identifies the cursor whose
channel the piece is primarily associated with — typically the
player holding the card, occupying the slot, or controlling the
worker. `visibility="owner_only"` is interpreted against `owner`.
`visibility=[...]` lists the cursors that may see the piece. See §1.5.

**Position.** `PieceFragment.position` carries the piece's spatial
binding inside its parent zone, when the parent zone's `layout_hints`
provides a geometry. For a grid zone, `position` is `{row, col}`. For
a hex zone, `{q, r}` (axial coords). For a free-form spatial zone
(e.g., a free-placement map), `{x, y}`. The CLI port renders piece
position as `[piece at (2, 3)]` regardless of geometry; richer ports
use the parent zone's layout to place the piece graphically. If
`position` is absent, the piece occupies the zone without a positional
binding (a card in a hand, a coin in a wallet).

**Movement.** Zone-to-zone moves are `update` control fragments
mutating `zone_ref`. Position changes within a zone are `update`
fragments mutating `position`. Display-state changes are `update`
fragments mutating `display_state`. Same UID throughout — no reflow.
Realization (offer → realized piece) is also an `update` control
fragment mutating `realized`.

**Availability.** `available=False` renders the piece as disabled with
`unavailable_reason`. Use cases: a card grayed because it's not
playable this turn; a shop item temporarily out of stock; a slot-
occupant pending some condition.

**`hints.label_text` is required** as a text fallback for CLI rendering.

### 7.2 `zone` — Group container with semantic constraints and geometry

Adds `zone` to the canonical `group_type` list in §2.4. Zones carry
two distinct kinds of metadata:

```python
class Edge(BaseModel):
    """An adjacency relation between two zones, addressable as a placement target."""
    uid: str                              # stable id for place choices' edge_ref
    a: str                                # zone uid
    b: str                                # zone uid
    label: str | None = None              # player-facing
    properties: dict[str, Any] = Field(default_factory=dict)

class ZoneLayoutHints(BaseModel):
    """Visual layout — port-specific; does not affect what's allowed."""
    orientation: Literal["row", "grid", "fan", "stack"] | None = None
    reveal: Literal["all", "top", "count"] | None = None
    counter: bool = False                 # render as bare number (Nim, wallet)
    # geometry — exactly one of:
    graph: GraphLayout | None = None      # {nodes, edges} — for point-to-point or networks
    grid: GridLayout | None = None        # {rows, cols} — civ-style
    floorplan: dict | None = None         # {rooms, doors} — building
    hex: HexLayout | None = None          # {orientation: "pointy"|"flat", radius}

class GraphLayout(BaseModel):
    nodes: list[str]                      # zone uids
    edges: list[Edge]                     # addressable adjacencies (see G3)

class GridLayout(BaseModel):
    rows: int
    cols: int

class HexLayout(BaseModel):
    orientation: Literal["pointy", "flat"]
    radius: int | None = None

class ZoneCapacity(BaseModel):
    kind: Literal["count", "weight", "power", "composite"]
    max: int | float | None = None
    unit: str | None = None
    sum_property: str | None = None       # for kind="weight"|"power": sum this piece property
    ledger_key: str | None = None         # advisory mirror in projected ledger

class ZoneConstraints(BaseModel):
    """Semantic constraints — informs what's allowed, affects all ports."""
    accepts_kind: list[str] = Field(default_factory=list)       # piece.kind whitelist
    accepts_tags: list[str] = Field(default_factory=list)       # piece.properties.tags ∩
    capacity: list[ZoneCapacity] = Field(default_factory=list)  # multiple = composite
    predicate_ref: str | None = None                            # backend-evaluated catch-all
```

`GroupFragment` (when `group_type=zone`) has both fields available:

- **`layout_hints`** — *visual* layout (orientation, fan, grid, hex,
  graph, floorplan). A renderer that ignores layout hints still
  renders the zone correctly.
- **`constraints`** — *semantic* membership rules. A renderer MAY use
  these for live preview (slot tile turns red on capacity overflow),
  but the backend always re-evaluates and is authoritative.

**The split matters because they have different cross-port behavior.**
A port that ignores `layout_hints` still renders correctly (just less
prettily). A port that ignores `constraints` may show stale capacity
bars or mispredicted blockers, but commits will still be correctly
evaluated by the backend.

**Edges are first-class.** `GraphLayout.edges` carry UIDs and may be
addressable as placement targets via `PlaceAccepts.edge_ref`
(§6.1.1). This lets a bundle author model network/route-building
games — Ticket to Ride trains on routes, Power Grid wires between
cities — where pieces are placed *on connections*, not in zones.
Bundles that prefer it MAY model edges as `zone_role="connection"`
sub-zones with capacity 1 instead; both patterns are conforming.

**Capacity is projected, not computed client-side.** The backend
projects current capacity into a `kv_list` row using `KvRow.value` /
`KvRow.max` (e.g., `weight: 4/12`). The client paints the bar from
the projected state. Drag-preview UIs read the projection plus the
dragged piece's `properties.<sum_property>` to compute a live
overlay. There is no `capacity_contributions` mapping on the wire —
the projection is the contract, not the formula.

**Empty zones referenced by an open choice.** A zone with
`member_ids: []` that is the target of an open choice's
`accepts.constraints.target_zone_ref` or
`PlaceAccepts.target_zone_ref` MUST still render as a placeholder
with its `hints.label_text` and constraint summary, per §5.1
Decision Legibility. CLI port renders `[ front_mount: empty (weapon,
cap 1) ]`.

### 7.3 `RollFragment` — Structured-outcome ritual

Generalizes "backend-resolved structured outcome rendered as a
ritual." Subsumes dice rolls, card draws, random-table results, coin
flips, combat resolutions, and procedural reveals.

```python
class RitualHints(BaseModel, extra="allow"):
    """Advisory polish for skip/replay UX. Cannot suppress skip itself."""
    skip_label: str | None = None        # "Skip the roll" — defaults to a generic
    auto_skip_after_seen: bool = False   # client may auto-skip on replay
    allow_replay: bool = True            # may the player re-watch from the transcript
    duration_ms: int | None = None       # advisory; informs progress UI

class RollFragment(BaseFragment):
    fragment_type: Literal["roll"] = "roll"
    label: str                            # "Driving check", "Draw fate"
    kind: Literal["dice", "card", "table", "flip", "custom"] = "dice"
    inputs: dict[str, Any] = Field(default_factory=dict)   # discriminated by kind
    outcome: str                          # "success" | "fail" | "crit" | bundle-defined
    narrative: str | None = None          # prose; required for CLI fallback
    against: dict[str, str] | None = None # {piece_id, property} when applicable
    ritual_hints: RitualHints | None = None
```

| | |
|---|---|
| **Required** | `uid`, `label`, `outcome`. `narrative` is required when no other content fragment in the same envelope explains the result. |
| **Optional** | `inputs` (kind-specific), `against`, `ritual_hints` |
| **Container rule** | Flows into the active scene. Order is presented order; pre-roll choice precedes the roll. |
| **States** | **resolved** (the outcome is canonical the moment the fragment lands). The visual *ritual* is a presentation enhancement bound by §5.2 Time Parity. |
| **A11y** | The outcome word is announced verbatim. Any visual ritual respects `prefers-reduced-motion` and the §5.2 skip rule. |
| **Fallback** | A port that does not specially-render `roll` MUST render `label`, `inputs` summary, `outcome` word, and `narrative` as a `content` fragment. |

**`inputs` shape by kind.**

| `kind` | Typical `inputs` |
|---|---|
| `dice` | `{ "dice": "2d6", "rolled": [4, 5], "target": 12, "modifier": 0, "total": 9 }` |
| `card` | `{ "drawn": ["king_of_cups"] }` |
| `table` | `{ "table_id": "minor_loot", "row": 17, "label": "rusted dagger" }` |
| `flip` | `{ "result": "heads" }` |
| `custom` | bundle-defined |

**The fork lives on the backend.** A roll's success/fail outcome
selects which edges appear in the *next* envelope's open-choice list.
The client never decides which branch fires — the backend rolls,
narrates, and routes to the corresponding edge. This is what makes
`RollFragment.outcome` canonical and unambiguously skippable: the
player has nothing to decide about the roll itself.

**Per §0.6 narrative authoring stance:** a roll outcome need not be
the answer to a referentially-transparent question. The backend may
generate the outcome at the moment of the roll, may have planned it
in advance, or may decide it in service of narrative pacing. The
contract is that the *rendered outcome is canonical*; nothing
upstream commits the backend to a stable underlying model.

### 7.4 `predicate_ref` registration protocol

Open question pending an MVP author. The shape proposed:

- `predicate_ref` is a **stable string id**.
- A bundle declares `predicates: { id: callable }`.
- A port without that bundle's predicates renders any blocker citing
  `predicate_ref` as opaque (`requires: <predicate_ref>`).
- The backend always evaluates predicates; the client never does.

Per §0.6, predicates need not be referentially transparent — they are
backend callables, not world-model queries. The same `predicate_ref`
may return different answers on different turns; the contract is that
the backend has decided, not that any client can reproduce the
decision.

Without this protocol resolved, BGG-mechanism coverage for variable
powers, area control, pattern building, and adjacency-based tile
placement stays theoretical. §7.4 is the single highest-leverage open
item in v1.5.

### 7.5 Profile registry

Profiles are non-normative descriptors of how a specific `piece.kind`
is used. Each profile specifies canonical `properties` keys,
recommended `zone_role`s and `layout_hints`, the `accepts.kind` its
moves use, and a worked CLI fallback.

Currently sketched: `card`, `tile`, `counter`, `die`, `packet`,
`generator`, `location`, `actor`. Full definitions deferred until Tier
P2 typing lands.

---

## 8 · Tier P3 — genre extensions (deferred)

Genre layers add domain-specific authoring affordances on top of Tier
P2. Each genre lives in its own extensions document.

- **Carwars-gamebook** — `bundles/carwars/EXTENSIONS.md`. Slot-zone
  conventions, `ui_hints.stat_check`, `ui_hints.drag` for vehicle
  outfitting, RNG combat fixtures, the "Garage turn" worked example.
- **Credentials / inspection** — `bundles/credentials/EXTENSIONS.md`.
  Severity-coded findings, mediation move catalog, packet zones,
  disposition severity, backend-authored discrepancies.
- **Training (succession-game)** — `bundles/training/EXTENSIONS.md`.
  Mood as growth modulator, scheduled checks, inventory unlocks,
  weekly study commits. Grounded in `worlds/coronate_the_regent`.
- **Elefant Hunt / graph-traversal board game** —
  `bundles/elefant_hunt/EXTENSIONS.md`. Graph sandbox, backend-private
  token pool, composite hunt resolution, journal-as-story.
- **Hana-smuta board** — `bundles/hana_smuta/EXTENSIONS.md` (sketched).
  Card profile + `hand` / `field` / `pile` / `score_pile` zones, plus
  matching `accepts(pieces, same_property)`.

Genre extensions MAY introduce typed sub-shapes on the open dicts of
existing fragments and hints (e.g., `ui_hints.stat_check`,
`ui_hints.drag`). They MUST NOT introduce new top-level fragment types
or modify Tier S/P1/P2 contract surfaces. Anything that needs a new
top-level type is a candidate for promotion to Tier P2 or P3, and goes
through the CLI Floor Rule.

---

## 9 · Port parity reference (Tier S + Tier P1)

| Widget | Web (Vue) | CLI | tkinter | Ren'Py / Godot |
|---|---|---|---|---|
| content | `<p>` / `<article>` | wrapped stdout | `Text` segment | `RichTextLabel` / narrator |
| attributed | avatar + bubble | `who [how]> text` | `Frame` (img + label) | character say / portrait |
| media (cover_im / narrative_im) | `<img>` / `<video>` | `[img: url]` | `Label(image=…)` | `scene bg` / `TextureRect` |
| media (avatar_im) | round `<img>` | (elided) | small `Label(image=…)` | side image / portrait slot |
| media (audio/video) | `<audio>` / `<video>` | `[♪ url]` / `[▶ url]` | out-of-band | `play music` / `VideoStreamPlayer` |
| group(scene) | section block | blank-line separator | `Frame` group | `Node2D` / scene |
| group(dialog) | indented region | indented block | `Frame` indented | contiguous say block |
| group(overlay) | modal sheet | `---` banner page | `Toplevel` modal | modal screen |
| group(status_sidecar) | right rail | status line | side `Frame` | stats screen |
| kv (fragment) | inline chips | `[status] k=v k=v` | label pairs | `HBoxContainer` |
| choice (pick, available) | button | `1) …` | `Button` | `menu:` / `Button` |
| choice (locked) | disabled + reason | `(locked) reason` | disabled + reason | `if` gated |
| choice (text/quantity/pieces) | inline form | `> ` prompt | `Entry` / `Spinbox` | `renpy.input` / `LineEdit` |
| choice (place) | two-step click-pick (drag-drop optional, §5.3) | numbered two-step pick | listbox + button | scene click target |
| choice (compose) | grouped form | sequenced prompts | nested `Frames` | menu of menus |
| choice (raw_command) | command bar | `> ` prompt (default) | `Entry` | `renpy.input` |
| control (update/delete) | re-render target | re-print with marker | re-render cell | re-run statement |
| user_event | bottom toast | `* type: content` | `Toplevel` | `notify()` / Popup |
| interpretation | transcript line | inline transcript | `Label` row | log line / chip |
| projected scalar | tile | `title: value` | large `Label` | stat widget |
| projected kv_list | rail rows | aligned columns | `Frame` + grid | `VBoxContainer` |
| projected item_list | roster | `- label (detail)` | `Listbox` + detail | `ItemList` |
| projected table | `<table>` | aligned columns | `ttk.Treeview` | grid / `Tree` |
| projected badges | chips | `[tag1][tag2]` | small labels | chips |
| info_affordances bar | pill bar | slash commands / `?` menu | menu bar | menu screen |

**Tier P2 widgets (piece, zone, roll)** are not in this table until
their CLI renderings ship in `cli_reference_port.py`.

---

## 10 · Conformance

### 10.1 Fixture suite

```
engine/contrib/conformance/
  fixtures/
    command_hints.json            # raw_command + grammar + interpretation
    compose_payload.json          # compose accepts with quantity + pieces parts
    control_delete.json           # delete control mutation
    crossroads_inn.json           # canonical narrative turn
    dialog_with_avatar.json       # attributed group + avatar_im binding
    pending_media_update.json     # rit format with later update swap
    projected_state_all_values.json
    quantity_payload.json         # quantity accepts
    sandbox_payload.json          # text/quantity/pieces accepts variants
  proposals/
    carwars_garage_turn.json      # proposal fixture for slot/catalog/place flow
    piece_realization.json        # proposal fixture for realized/unrealized pieces
    place_accepts.json            # proposal fixture for place accepts
    record_kvrow.json             # proposal fixture for record-shaped KvRow
    roll_fragment.json            # proposal fixture for RollFragment
  cli_reference_port.py           # Python CLI port (Tier S floor)
  reference_port.py               # UI-neutral reference view model
  tk_reference_port.py            # Tk planning / inspection reference
```

**Proposal fixtures vs. gating fixtures.** Fixtures tagged "PROPOSAL
FIXTURE" exercise contract surfaces that are committed in this spec
but not yet engine-shipped (and not yet enforced in the CLI reference
port). They serve as forward-compatibility evidence — the wire shapes
are valid against the spec — but conformance tests skip them until
the corresponding engine-rollout status is "implemented." See
`WIDGET_CONTRACT_RECONCILIATION.md` for current rollout status.

Fixtures are JSON. Each port runs its own conformance test that loads
the fixtures and asserts observable output:

- **Web port**: feed envelopes through the renderer, assert DOM matches
  expected.
- **CLI port**: feed envelopes through `cli_reference_port.py`, assert
  stdout matches expected.
- **Future ports**: same fixtures, port-appropriate assertions.

### 10.2 Conformance checks (Tier P1)

`legibility.py` walks each fixture and verifies §5.1:

- Every UID referenced by an open choice's
  `accepts.constraints.target_zone_ref`,
  `PlaceAccepts.target_zone_ref`, or `PlaceAccepts.edge_ref` is
  present in rendered output.
- Every UID in any `blocker.refs` is present in rendered output.
- No fragment with `visibility="hidden"` appears in any channel.
- A fragment with `visibility="owner_only"` appears only in its
  owner's channel.
- A fragment with `visibility=[participant_ids]` appears only in
  channels whose owner is in the list.

`parity.py` verifies §5.2 and §5.3 against port harnesses:

- Time-to-canonical-outcome on the web port (with skip invoked) ≤
  CLI-port time-to-canonical-outcome + tolerance.
- Every `media` fragment's "advance past" affordance is reachable
  during playback.
- Every interaction the CLI port reaches via numbered selection is
  reachable on the web port via tap/click of a visible button.
- Every drag-and-drop interaction on the web port has a click-pick
  fallback observable in the same fixture.
- Every `metadata.info_affordances` entry is reachable through some
  CLI-floor mode (`info_affordances[].shortcuts` keystrokes or a
  documented slash/menu command).

Failure prints the offending fixture, choice/fragment UID, and rule
violation.

### 10.3 CLI floor as gate

Per §0.2: `cli_reference_port.py` MUST produce defined output for
every state of every Tier S widget. Tier P1 proposals MUST add CLI
rendering before graduating to Tier S. PRs that change Tier S
vocabulary without updating `cli_reference_port.py` fail CI.

### 10.4 Journal-as-story transcript test

Per §0.8: each genre fixture suite SHOULD include at least one
**transcript test** — a script that runs a complete play session
through `cli_reference_port.py`, captures the rendered stdout, and
asserts the resulting transcript is:

1. Non-trivial (at least one fragment per location, encounter, or
   choice-resolution event).
2. Contains the key narrative events (locations visited, captures /
   losses / commits, terminal outcome).
3. Readable as prose by a human (smoke-tested manually; not a hard
   assertion).

The test is diagnostic, not gating: a transcript that reads poorly
is a *bundle-authoring* finding (thin prose, missed control-fragment
narrations, etc.), not a contract violation. The point is to keep
the journal-as-story claim concretely measurable rather than
aspirational.

`engine/contrib/conformance/transcripts/` collects exemplar
transcripts per genre:

```text
engine/contrib/conformance/transcripts/
  carwars_garage_to_combat.txt
  credentials_day1_morning.txt
  training_coronate_full_session.txt
  elefant_hunt_one_expedition.txt
```

These serve as both regression baselines and authoring references.

---

## Appendix A — Glossary

| Term | Definition |
|---|---|
| Envelope | One `RuntimeEnvelope` instance — the per-turn payload from `/story/do` or `/story/update`. |
| Fragment | An entry in `RuntimeEnvelope.fragments`. Has stable `uid`. |
| Section | An entry in `ProjectedState.sections`. Refreshed every state-changing turn. |
| Cursor | One participant's traversal through a story. Each cursor has its own journal channel; envelopes are per-cursor. |
| Channel | The envelope stream for one cursor. Multi-cursor sessions have multiple channels coordinated by bundle logic. |
| Participant / Owner | The account or identity behind a cursor. Used for `owner_only` visibility and `visibility=[participant_ids]` audience routing. |
| Info channel | An advisory side-projection of world state queryable via the info endpoint (§6.7) with an opaque `query` descriptor (§1.6) and advertised in `metadata.info_affordances`. |
| Piece (Tier P2) | Identified, state-bearing surface element (card, tile, die, etc.). UI concept; distinct from `tangl.core.token.Token`. May be realized (has backend UID) or unrealized (an offer). |
| Offer (Tier P2) | A `PieceFragment` with `realized=False`. Becomes a real piece on commit. |
| Zone (Tier P2) | A `group_type="zone"` group containing pieces. May carry `constraints` (semantic), `layout_hints` (visual), and `layout_hints.graph.edges` (addressable adjacencies). |
| Edge (Tier P2) | An adjacency relation between zones, addressable as a placement target via `PlaceAccepts.edge_ref`. |
| Slot (Tier P2) | Recommended visual-treatment tag for a zone with `constraints.capacity` set. Not a contract entry. |
| Catalog (Tier P2) | Recommended visual-treatment tag for a zone whose members are unrealized pieces. Not a contract entry. |
| Connection (Tier P2) | Recommended visual-treatment tag for a zone or edge that models a route between locations. Not a contract entry. |
| Profile (Tier P2) | A non-normative descriptor of how a `piece.kind` is used. Drives port-conformance subsetting. |
| Predicate (Tier P2) | An author-registered, backend-evaluated boolean function referenced by `predicate_ref`. Per §0.6, need not be referentially transparent. |
| Ritual (Tier P2) | A presentation enhancement that elapses time to dramatize a backend-canonical outcome. Subject to §5.2 Time Parity. |
| Tier S/P1/P2/P3 | This document's stratification of stable vs. proposed vocabulary. |

## Appendix B — Open questions (working list)

1. **`payload_type` wrapper** in webapp `ChoiceInputView`. Kill,
   formalize, or fold into a specific `Accepts` variant? Default-kill
   unless an author case appears.
2. **`render_profile` query parameter** on `/story/do` (currently
   defaults to `"raw"`). What other profiles exist? Document or
   remove.
3. **Sunset clock for legacy `JournalStoryUpdate[]`** in
   `apps/web/src/components/story/fragmentUtils.ts`. Are any backends
   still emitting that shape? If not, the adapters can go.
4. **Predicate registration protocol** (§7.4). Highest-leverage open
   item. Awaiting an MVP author.
5. **Conformance fixture format** — JSON confirmed for cross-language
   portability.
6. **Group fragment `dialog` vs DialogFragment** — current engine has
   both. Spec says ports MAY treat them identically. If there's a use
   case for DialogFragment carrying additional fields, it should be
   promoted. Else, plan retirement of the legacy shape.
7. **`PieceFragment.available` / `unavailable_reason` for realized
   pieces.** These fields make sense for offers (catalog rows). They
   also plausibly apply to realized pieces (a card grayed because not
   playable this turn). v1.5 keeps them on base `PieceFragment` for
   both cases.
8. **`RitualHints` scope.** Currently on `RollFragment` only. If
   authors want skip-tuning on `MediaFragment` transitions or other
   timed presentations, lift `RitualHints` to a shared mixin.
9. **Cross-channel turn coordination** (§1.5). The contract says
   bundles own this; the spec does not propose a uniform primitive
   for "wait for all cursors to commit" or "rotate active cursor."
   Worth a sketch document at some point but explicitly out of scope
   for v1.x.
10. **Info-channel compound queries.** v1.5 keeps the v1.3 sub-
    addressing question via `InfoAffordance.query: dict[str, Any] |
    None` — bundles encode whatever compound parameters they need in
    the descriptor (e.g., `query={"type":"map","region":"hall"}`).
    Whether the engine team standardizes a sub-set of well-known query
    keys (`region`, `filter`, `format`) is a future question.

## Appendix C — Cross-references to genre extensions

| Bundle | Document | Highlights |
|---|---|---|
| carwars (gamebook) | `bundles/carwars/EXTENSIONS.md` | Slot-zone conventions, `ui_hints.stat_check`, `ui_hints.drag`, Garage turn worked example, RNG combat patterns |
| credentials (inspection) | `bundles/credentials/EXTENSIONS.md` | Severity-coded findings as `KvRow.emphasis`, mediation move catalog, packet zones, disposition severity via `ui_hints.emphasis`, backend-authored discrepancies per §0.6 |
| training (succession-game) | `bundles/training/EXTENSIONS.md` | Mood as growth modulator (per-tag `SituationalEffect`s rendered as projected scalar + delta previews), `RollFragment` skill checks against player stats, weekly study commits, inventory unlocks via `realized` lifecycle |
| elefant_hunt (board game / sandbox) | `bundles/elefant_hunt/EXTENSIONS.md` | Graph-traversal sandbox; backend-private `TokenPool` validating §0.3; composite hunt resolution via `RollFragment(kind="custom")`; journal-as-story validation per §0.8 |
| hana_smuta (sketch) | `bundles/hana_smuta/EXTENSIONS.md` (TBD) | Card profile, `hand`/`field`/`pile`/`score_pile` zones, `same_property` constraints |

---

*End of v1.5.*
