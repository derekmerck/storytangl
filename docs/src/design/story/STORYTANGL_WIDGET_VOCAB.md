# StoryTangl Widget Vocabulary

**Version:** v1.0 (draft) · supersedes v0.3 + interactive-surfaces v0.4 + command-resolution v0.1
**Status of this document:** adopted unified vocabulary target. Repo-current
conformance status is tracked in
`docs/src/design/story/WIDGET_CONTRACT_RECONCILIATION.md`; do not treat every
Tier S label below as CI-enforced until that table marks the surface current.
**Audience:** anyone implementing a StoryTangl client (Vue, CLI, tkinter, Godot, Ren'Py, bespoke), or extending the engine's emitted contract
**Source of truth:**
- `tangl.journal.fragments` (fragment types, presentation hints)
- `tangl.service.response` (`RuntimeEnvelope`, `ProjectedState`, section value union)
- `tangl.journal.intent` (proposed; typed `Accepts`/`UIHints`/`Blocker` — see §5)

This document defines the framework-independent rendering contract for the
engine's `RuntimeEnvelope.fragments` and `ProjectedState.sections`. Visual
treatments are author-swappable via bundle customization (§4); the vocabulary
itself is not.

> The Vue components in `apps/web/src/components/story/` are **one** reference
> rendering. A CLI port, a tkinter port, and a Godot port are equally valid —
> they each realize the same widget contract in their own medium.

Repository note: this document intentionally uses the settled vocabulary target
(`piece`, record-shaped `KvRow`, `interpretation.result/text`) even where the
current engine/webapp still carry migration names (`token`, tuple-style kv rows,
or fallback-only interpretation rendering). See the reconciliation document
before generating conformance fixtures or filing implementation drift.

---

## 0 · Conventions and principles

### 0.1 Tier tags

Every section in this document carries one of four tier tags. These are not
aspirations; they are operational. A reader should always know what's in the
engine right now, what's a near-term proposal, and what's a longer-horizon
direction.

| Tag | Meaning |
|---|---|
| **Tier S** (Stable) | Implemented in engine v3.7+ as documented; clients MAY rely on it. |
| **Tier P1** (Proposed, next engine epoch) | Concrete proposal with typed Pydantic models below. Additive. Backwards-compatible coercion path planned. |
| **Tier P2** (Proposed, larger) | Architectural direction with sketch-level types. Pending settlement of §6 ontology. |
| **Tier P3** (Genre extensions) | Domain-specific layers (carwars, hana-smuta, etc.). Defer until P1+P2 stabilize. |

Each section's tier is given in its header. Subsections inherit unless overridden.

### 0.2 The CLI Floor Rule

> A new widget, accepts kind, hint, fragment type, or `value_type` does not
> enter Tier S until a worked CLI rendering exists in
> `engine/contrib/conformance/cli_reference_port.py` and produces output for
> every state described in its spec entry.

This is the single rule that prevents the contract from drifting toward
web-shaped affordances. Drag-drop, animation, hover preview — those are
*reference renderings on top of* a contract that a CLI could fully execute.
A widget whose semantics requires more than a CLI can do is not in the
vocabulary; it is a renderer flourish.

The Python `cli_reference_port.py` is the gating artifact. If a Tier P1/P2
proposal lands without a CLI rendering, it stays Tier P; it does not graduate.

### 0.3 Backend authority

> The backend is authoritative for all state changes. The client MAY preview,
> validate, and decorate, but the client never decides anything that affects
> state without backend confirmation.

This rule has implications throughout the document. Grammar hints are
advisory; client-side validators are advisory; capacity ledgers compute on
the backend; predicates evaluate on the backend. The client's job is to
render and route events.

### 0.4 Records over tuples

All ordered key/value structures in this document are arrays of records, not
arrays of tuples. This applies to `KvRow` (§2.5), `compose.parts` payloads
(§5.1), and any future ordered-pair surface. Records are extensible, narrow
cleanly in TypeScript and Pydantic, and survive schema evolution. Tuples are
not used at any wire boundary.

### 0.5 Naming changes from prior drafts

Five renames were ratified in moving from v0.x to v1.0. They are noted here
once and applied throughout. Implementations migrating from v0.x should follow
the repo-current schedule in `WIDGET_CONTRACT_RECONCILIATION.md`.

| v0.x | v1.0 | Reason |
|---|---|---|
| `token` (UI piece) | `piece` | Collides with `tangl.core.token.Token` (singleton wrapper). |
| `ledger` (UI section type) | *removed* | Subsumed by annotated `kv_list` rows (§2.5). The engine's `tangl.vm.runtime.ledger.Ledger` keeps the name. |
| `choice_id` (HTTP body) | `edge_id` | Reconciles with `ChoiceFragment.edge_id`. |
| `interpretation.outcome` / `command_text` | `interpretation.result` / `text` | Spec-final names; webapp drift is recent enough to fix cheaply. |
| `token_ids` (commit payload) | `piece_ids` | Follows `piece` rename. |

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

Each runtime turn produces one envelope. Fields:

- **`cursor_id`** — current cursor position. Stable across `interpretation`
  fragments (which do not advance the cursor); changes when state advances.
- **`step`** — monotonic counter incremented per state-changing turn.
  Unchanged by `interpretation` fragments.
- **`fragments`** — ordered stream; see §2 for fragment types.
- **`last_redirect` / `redirect_trace`** — runtime introspection for the
  ledger's most recent and historical redirects. Author/debug surface only;
  reader clients ignore.
- **`metadata`** — open dict for cross-cutting hints. The `metadata.grammar`
  sub-key is reserved (§5.5).

### 1.2 Fragment registry and UID stability

Every fragment carries a stable `uid`. Clients maintain a registry keyed by
`uid` across envelopes within a session. The registry is the source of truth
for the rendered scene; envelopes are diffs into it.

Two registry-mutating fragment types exist (§2.7):

- **`update`** control fragments mutate the registry entry at `ref_id` by
  merging `payload` into the existing fragment. The same UID is re-rendered
  in place; **no layout shift**.
- **`delete`** control fragments remove the registry entry at `ref_id`.

**Clients MUST NOT drop fragments they do not understand.** They MUST render
a textual fallback (see §3 parity table) so UIDs remain resolvable by future
control fragments.

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
re-projected every state-changing turn (i.e. when `step` advances). Shells
MAY animate deltas. The `kind` field is a free string for semantic tagging
(`wallet`, `score`, `inventory`, etc.); ports MAY use it to choose between
visual treatments.

### 1.4 Flow vs rail

A useful organizing distinction for shell designers:

- **Flow content** comes from `RuntimeEnvelope.fragments`. It is
  scene-bound, accumulates as a transcript, and is the locus of player
  interaction.
- **Rail content** comes from `ProjectedState.sections`. It is durable
  across turns, refreshes in place, and represents the world's persistent
  state visible to the player (purse, stats, inventory).

Some widgets exist in both worlds — `kv` (§2.5) is the canonical example,
appearing as a scene-bound *fragment* and as a durable *section value*. The
shape is identical (§2.5); only the routing differs.

---

## 2 · Fragment widgets — Tier S

Every fragment widget section has the same structure: a Pydantic shape, a
behavior table (required/optional/states/a11y/fallback), and concrete port
sketches.

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
| **A11y** | Plain text selectable; if `hints.style_tags` contains `establishing` or `chapter`, treat as `<h*>` landmark. Honor `prefers-reduced-motion`. |
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

Note the `alias="type"` on `fragment_type` — the wire shape may use either
`fragment_type: "attributed"` or `type: "attributed"`. Clients MUST accept
both. (This is a legacy-compat surface; future fragment types should not
introduce aliases.)

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
| **A11y** | Images need `content` labeled via `hints` or sibling text. Audio/video must expose native controls or keyboard toggle. `prefers-reduced-motion` disables `media_transition`. |
| **Fallback** | Unknown `media_role` → render inline. `content_format="rit"` unresolved → pending placeholder. |

**Port sketches.** Web: `<img>` / `<video>` / `<audio>` / placeholder; role maps to CSS class. CLI: `[img: <url>]` / `[♪ <url>]` single-line tokens. tkinter: `Label(image=…)` or placeholder `Frame`; audio/video out-of-band. Ren'Py: `scene <bg>` / `show <sprite>` / `play music` / `play sound`. Godot: `TextureRect` / `VideoStreamPlayer` / `AudioStreamPlayer`.

### 2.4 `group` — Container

```python
class GroupFragment(BaseFragment, extra="allow"):
    fragment_type: Literal["group"] = "group"
    group_type: str | Enum | None = None
    member_ids: list[UUID] = Field(default_factory=list)
```

Note: `DialogFragment(GroupFragment)` exists as a distinct fragment type
(`fragment_type: "dialog"`) with the same structural role. Clients MAY
treat `DialogFragment` and `GroupFragment(group_type="dialog")` identically.

| | |
|---|---|
| **Required** | `uid`, `member_ids[]` |
| **Optional** | `group_type` |
| **Canonical `group_type`** | `scene` (turn boundary); `dialog` (consecutive `attributed` lines); `turn` (implicit cursor advancement); `overlay` (modal over active scene; one level of nesting); `status_sidecar` (in-stream kv/item_list rail). Tier P2 adds `zone` (§6.2). |
| **Container rule** | `scene` defines turn boundaries. `dialog` groups consecutive `attributed`. `turn` is implicit cursor advancement. `overlay` is modal over current scene. `status_sidecar` is an in-stream rail. |
| **States** | **loading** → render members as they arrive, in order. **partial** → ok; finalize on next `update`. **empty** → hide entire group. |
| **A11y** | `overlay` traps focus and exposes `role="dialog" aria-modal="true"`. `dialog` is the `aria-live` host. |
| **Fallback** | Unknown `group_type` → render members flat, no wrapper. |

`group_type` is currently typed as `str | Enum | None` — it accepts any
value. The canonical list above is recommended; ports MUST handle unknown
types via the fallback rule.

### 2.5 `kv` — Key/value rows (unified shape)

The `kv` surface appears in two places — as a scene-bound fragment, and as a
projected section's `value_type`. **Both use the same `KvRow` shape.** This
unification supersedes the older `OrderedTupleDict` form for `KvFragment` and
the simpler `{key, value}` form for `ProjectedKVItem`.

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

- **Semantic fields** (`max`, `delta`, `unit`, `hint`, `emphasis`) inform
  rendering across *all* ports. CLI honors them by choice of glyph/format;
  web by choice of widget; Godot by choice of scene variant.
- **Presentational hints** (`presentation_hints`, the engine's existing
  `PresentationHints` model) are port-specific styling (`style_dict`,
  `style_tags`, `style_name`, `icon`). Ports that don't recognize them
  ignore them — this is correct.

#### 2.5.1 Type narrowing via field population

The flat optional-field shape supports type narrowing without proliferating
`value_type`s. A port that wants to render specific subshapes does so by
narrowing on populated fields:

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

The wire schema is unchanged — exactly one shape, with optional fields. The
narrowing happens at read time in the consumer's type system. This is also
why the project does not add `value_type: "ledger"` or
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
    blockers: list["Blocker"] | None = None         # Tier P1 type, see §5.3
    accepts: "Accepts | None" = None                # Tier P1 type, see §5.1
    ui_hints: "UIHints | None" = None               # Tier P1 type, see §5.2
    activation_payload: Any = Field(None, alias="payload")
```

The current engine emits `accepts`, `ui_hints`, and `blockers` as
`dict[str, Any]`. Tier P1 (§5) introduces typed shapes; the migration shim
on `ChoiceFragment` accepts both forms during deprecation.

| | |
|---|---|
| **Required** | `uid`, `text` |
| **Optional** | `edge_id` (omitted for `interpret_command` reserved choices); `available` (default `true`); `unavailable_reason`; `blockers[]`; `accepts`; `ui_hints`; `activation_payload` |
| **Container rule** | Always emitted within the active `scene` group. Order is presented order; `ui_hints.hotkey` is advisory. |
| **States** | **available** → active. **locked** (`available=false`) → disabled but present; show `unavailable_reason`; `blockers[]` is author-facing detail. **freeform** (`accepts.kind ∈ {text, quantity, tokens, compose, raw_command}`) → inline input; commit sends typed payload. **loading** → disable group during dispatch. **error** → re-enable; mark failed attempt. |
| **A11y** | Group is `role="group" aria-label="choices"`. Hotkeys from `ui_hints.hotkey`; ↑/↓ cycles; Enter commits; Esc cancels freeform. Focus returns to primary choice of new turn after dispatch. Hit target ≥ 44×44 on touch. Locked choices remain focusable for screen reader stability. |
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
`reference_type` and `reference_id` are the Python attributes. Clients see
the aliased forms.

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

This fragment is Tier P1 — its full type definition lives in §5.4. It is
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
semantics, and a sensible CLI rendering. **No additional `value_type`s are
proposed.** Subtypes that look like new value types are populated `kv_list`s
(see §2.5.1).

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
(armor-by-location, leaderboard); a row width validator on the engine side
ensures `len(row) == len(columns)`.

### 3.3 Section hints

```python
class ProjectedSection(BaseModel):
    section_id: str
    title: str
    kind: str | None = None              # semantic tag, e.g. "wallet", "score"
    value: SectionValue
    hints: PresentationHints | None = None
```

`kind` is a free string used by ports to choose between visual treatments
(`wallet` → coin icon, `score` → leaderboard skin, etc.). It does not
discriminate the value union.

`hints` is the existing `PresentationHints` model (style_name, style_tags,
style_dict, icon). Same surface as on every other fragment that carries hints.

---

## 4 · Bundle customization — Tier S

A story bundle MAY override the following. Everything else is stable
vocabulary and MUST NOT be redefined.

### 4.1 What is stable (not author-swappable)

- The set of canonical `fragment_type`s and their required fields.
- The canonical `group_type`s listed in §2.4.
- The set of canonical `value_type`s in §3.1.
- The accessibility contract throughout §2.
- Fallback behavior: never silently drop fragments.
- The CLI floor rule (§0.2).

### 4.2 What a bundle MAY override

```python
bundle = {
    "id":      "crossroads_cyberpunk",      # unique
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
        "dice_roll": "renderDiceRoll",      # function reference
    },
}
```

**Rules.**

1. Variants receive the **same props contract** as the default widget. They
   may not change required/optional field names.
2. A custom fragment handler MUST provide a text fallback (per §6 parity
   table) so other ports still work.
3. `shell` is advisory; a port that lacks the named shell falls back to its
   default.
4. Tokens are flat key→value; nothing nested. Variables prefixed with `--`
   are CSS; `motion-*` are honored by all ports including non-web.

### 4.3 Profiles — port conformance subsetting (Tier P2)

Bundles MAY declare which **profiles** they exercise:

```python
bundle["profiles"] = ["card", "location", "actor"]
```

A port that implements a strict subset of profiles is still a conforming
StoryTangl client for any bundle whose `profiles` are a subset of the
port's supported profiles. The minimum conforming card-game client
implements `card`, `hand`, `field`, `pile`, `score_pile`, `discard`,
`accepts.kind ∈ {pick, tokens}`, plus the §3 value types it uses. This is
the path by which (e.g.) a hana-smuta tkinter board ships without
implementing the full §6 vocabulary.

Profiles are non-normative: a port that does not know a profile falls back
to generic widget rendering. See §6.5 for the profile registry.

---

## 5 · Decision Legibility Contract — Tier S (proposed conformance hook)

> **When a fragment's state is referenced by an open `choice`'s `accepts`
> constraints, `blockers[]`, or `unavailable_reason`, the client MUST render
> enough of that fragment's state for a player to evaluate the choice
> without out-of-band knowledge.**

> `visibility="hidden"` fragments are never referenced by open choices in
> the referencing player's session. `visibility="owner_only"` fragments are
> referenced only in their owner's session.

This rule strengthens §2's generic rendering rule. Existing widgets (prose,
media, choice) do not gate legal choices on rendered state, so "render
however you like" suffices. Interactive surfaces (§6) do, and must
therefore meet a stricter floor: **if the player can choose it, the player
can see it.**

**Operational tests.**

- An open `choice.accepts.constraints.target_zone_ref = Z` means zone `Z`
  MUST be rendered with all non-hidden member pieces visible.
- A `blockers[]` entry with `refs` citing `piece_id = P` means piece `P`
  MUST be rendered.
- An `unavailable_reason` mentioning a state property MUST resolve from
  rendered state alone (no out-of-band knowledge required).

This rule is **conformance-checkable**: a test sweeps every open turn for
referenced UIDs and verifies each is on screen. The test lives in
`engine/contrib/conformance/legibility.py` (Tier P1) and runs against every
fixture as part of CI.

---

## 6 · Tier P1 — typed contract proposals (next engine epoch)

Everything below is **additive** and **backwards-compatible** via coercion
shims. No fragment shapes change; only their interior dicts gain types.

### 6.1 Typed `Accepts`

The engine's `ChoiceFragment.accepts` is currently `dict[str, Any]`.
This proposal lands a Pydantic discriminated union in
`tangl/journal/intent.py`:

```python
# tangl/journal/intent.py — proposed Tier P1
from typing import Annotated, Literal, TypeAlias
from pydantic import BaseModel, ConfigDict, Field

class CostPreview(BaseModel):
    """Advisory cost display. Never gates a commit; backend re-validates."""
    ledger_key: str           # which projected section to debit
    delta: int
    unit: str | None = None

class TokenConstraints(BaseModel):
    """Constraints on a kind='tokens' selection."""
    same_property: list[str] | None = None
    different_property: list[str] | None = None
    target_zone_ref: str | None = None    # uid of group with group_type=zone
    predicate_ref: str | None = None      # opaque, story-registered (Tier P2)

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
    cost_preview: CostPreview | None = None

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
    cost_preview: CostPreview | None = None

class TokensAccepts(BaseModel):
    kind: Literal["tokens"] = "tokens"   # selects pieces; not the engine "Token"
    min: int = 1
    max: int = 1
    constraints: TokenConstraints | None = None

class ComposePart(BaseModel):
    role: str                            # stable string the backend keys on
    accepts: "NonComposeAccepts"

class ComposeAccepts(BaseModel):
    kind: Literal["compose"] = "compose"
    parts: list[ComposePart]

class RawCommandAccepts(BaseModel):
    kind: Literal["raw_command"] = "raw_command"

NonComposeAccepts: TypeAlias = Annotated[
    PickAccepts | TextAccepts | QuantityAccepts | TokensAccepts | RawCommandAccepts,
    Field(discriminator="kind"),
]

Accepts: TypeAlias = Annotated[
    PickAccepts | TextAccepts | QuantityAccepts | TokensAccepts
    | ComposeAccepts | RawCommandAccepts,
    Field(discriminator="kind"),
]
ComposePart.model_rebuild()
```

#### 6.1.1 Commit payload shapes

The wire payload is shape-keyed by the choice's `accepts.kind`, **not** by an
explicit discriminator on the payload itself. The backend has the open-choice
list and resolves the expected shape via `edge_id`. This keeps payloads short
and matches existing webapp behavior.

| `accepts.kind` | Wire payload | Notes |
|---|---|---|
| `pick` | `{}` (empty object) | The `edge_id` is the answer. |
| `text` | `{ "text": str }` | |
| `quantity` | `{ "quantity": int }` | |
| `tokens` | `{ "piece_ids": [str, ...] }` | `min ≤ len ≤ max` |
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

#### 6.1.2 Validator authority

- Non-`backend` validators (length, regex, enum) are advisory. The client
  SHOULD evaluate them inline before allowing commit.
- The backend re-evaluates ALL validators on commit and is authoritative.
- A backend-side validation failure surfaces as an `interpretation` fragment
  with `result="validation_failed"` (§6.4). Step does not advance.

### 6.2 Typed `UIHints`

```python
class UIHints(BaseModel, extra="allow"):
    hotkey: str | None = None             # "1"-"9", "a"-"z"
    icon: str | None = None
    emphasis: Literal["primary", "subtle", "warning", "danger"] | None = None
    widget: str | None = None             # variant override id from bundle.widgets
    cost_preview: CostPreview | None = None
```

`UIHints` is deliberately open (`extra="allow"`) — it's a hint surface, not
a contract surface. Authors may add hints freely; ports ignore unknowns.
The named fields are documented hints with defined semantics.

### 6.3 Typed `Blocker`

```python
class Blocker(BaseModel, extra="allow"):
    code: str                             # author-stable, e.g. "needs_key"
    message: str                          # player-facing, may be templated
    refs: list[str] = Field(default_factory=list)  # uids referenced by message
```

Each blocker entry combines an author-stable identifier (for predicates and
testing), a player-facing message (which MAY reference rendered state per
§5), and a list of UIDs the message references. The Decision Legibility
Contract (§5) requires every UID in `refs` to be rendered.

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

**Why a dedicated fragment.** Replay/audit parity wants the failure to be
structured. Ports that render the parser-failure transcript (IF-style)
benefit from a stable shape. The cost is one fragment type that other ports
can fall back to prose for.

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

The client's command bar wraps this choice. Submission posts a `raw_command`
payload (`{ text: "..." }`). The backend either:

- Resolves the text to a real edge, applies it, and returns a normal
  envelope (cursor advances), OR
- Returns an `InterpretationFragment` describing the failure mode (cursor
  unchanged, choices intact).

A port that does not implement a command bar simply ignores the
`interpret_command` choice (which renders as a button labeled "Try a
command" with a text input — fine fallback).

### 6.6 `metadata.grammar`

Per the architecture commitment in `apps/web/notes/ARCHITECTURE.md`, the
grammar hint lives at `RuntimeEnvelope.metadata.grammar`. This is a typed
sub-key validated on serialization, **not** a top-level field on
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
verb, noun, or alias that does not already correspond to a visible `choice`
or `piece`. It is a UX affordance, never a security boundary.

The Story layer is the natural synthesizer (it knows what is narratively
visible). The Service layer is responsible for serializing it into
`metadata.grammar` on egress.

**Absence.** When `metadata.grammar` is absent, the command bar simply
submits raw text. No preview, no highlighting. Identical to a CLI port.

### 6.7 HTTP API

```python
# tangl/service/http/story.py — proposed Tier P1
class ChoiceRequest(BaseModel):
    edge_id: UUID                        # was: choice_id (deprecated alias)
    payload: dict[str, Any] | None = None  # validated against Accepts at runtime

@router.post("/story/do", response_model=RuntimeEnvelope)
def do_story_action(req: ChoiceRequest, ...) -> RuntimeEnvelope: ...

@router.get("/story/update", response_model=RuntimeEnvelope)
def get_story_update(...) -> RuntimeEnvelope: ...

@router.get("/story/info", response_model=ProjectedState)
def get_story_info(...) -> ProjectedState: ...
```

Three changes from the current `openapi.json`:

1. **`choice_id` → `edge_id`.** Deprecation: accept both names for one
   minor version, emit a header warning when `choice_id` is used. Then
   strict.
2. **Typed responses on `/story/do` and `/story/update`** —
   `response_model=RuntimeEnvelope` lets the OpenAPI doc express the full
   contract, which lets `apps/web` regenerate `api.d.ts` cleanly (§7.5).
3. **Payload validation by edge.** The backend looks up the choice by
   `edge_id`, retrieves its declared `Accepts.kind`, and validates the
   posted payload against the matching `*Payload` shape (§6.1.1). Failures
   are surfaced as `InterpretationFragment` with `result="validation_failed"`.

---

## 7 · Tier P2 — interactive surface vocabulary (proposed, larger)

This section depends on settling the §6 ontology rename (`token` → `piece`)
and the predicate registration protocol (§7.4). It is sketch-level until
those land. Implementations MAY consume this as a roadmap; it is not yet
contract.

### 7.1 `PieceFragment` — Identified surface element with state

```python
class PieceFragment(BaseFragment):
    fragment_type: Literal["piece"] = "piece"
    piece_id: str
    kind: str                             # free string: "card", "tile", "die", ...
    properties: dict[str, Any] = Field(default_factory=dict)
    visibility: Literal["public", "owner_only", "hidden"] = "public"
    display_state: str | None = None      # "face_up", "face_down", "selected", ...
    zone_ref: str | None = None
    presentation_hints: PresentationHints | None = Field(None, alias="hints")
```

A piece is an addressable, state-bearing element of a game surface (card,
tile, die, counter, generator, location, actor). Zone-to-zone moves are
`update` control fragments mutating `zone_ref`. Display-state changes are
`update` control fragments mutating `display_state`. Same UID throughout —
no reflow.

`hints.label_text` is **required** as a text fallback for CLI rendering.

### 7.2 `zone` — New `group_type`

Adds `zone` to the canonical `group_type` list in §2.4.

```python
class ZoneLayoutHints(BaseModel):
    orientation: Literal["row", "grid", "fan", "stack"] | None = None
    reveal: Literal["all", "top", "count"] | None = None
    counter: bool = False                 # render as bare number (Nim, wallet)
    # geometry — exactly one of:
    graph: dict | None = None             # {nodes, adjacency} — overworld
    grid: dict | None = None              # {rows, cols} — civ-style
    floorplan: dict | None = None         # {rooms, doors} — building
```

A zone's member pieces (those with `zone_ref` matching the zone's `uid`)
render inside it. Empty zones MUST still render a placeholder if
referenceable by an open choice (§5).

### 7.3 `RoundReportFragment` — Structured move-outcome

```python
class RoundReportFragment(BaseFragment):
    fragment_type: Literal["round_report"] = "round_report"
    result: Literal["WIN", "LOSE", "DRAW", "CONTINUE"]
    player_move: Any
    opponent_move: Any | None = None      # null for solitaire
    score_delta: dict[str, int] = Field(default_factory=dict)
    notes: dict = Field(default_factory=dict)  # game-specific
    prose_fallback: str                   # required for CLI port
```

Replay/audit parity wants this stable. Ports without round-report
rendering fall back to emitting `prose_fallback` as a `content` fragment.

### 7.4 `predicate_ref` registration protocol

Open question pending an MVP author. The shape proposed:

- `predicate_ref` is a **stable string id**.
- A bundle declares `predicates: { id: callable }`.
- A port without that bundle's predicates renders any blocker citing
  `predicate_ref` as opaque (`requires: <predicate_ref>`).
- The backend always evaluates predicates; the client never does.

Without this, BGG-mechanism coverage for variable powers, area control, and
pattern building stays theoretical.

### 7.5 Profile registry

Profiles are non-normative descriptors of how a specific `piece.kind` is
used. Each profile specifies canonical `properties` keys, recommended
`zone_role`s and `layout_hints`, the `accepts.kind` its moves use, and a
worked CLI fallback.

Currently sketched: `card`, `tile`, `counter`, `die`, `packet`,
`generator`, `location`, `actor`. Full definitions deferred until Tier P2
typing lands.

---

## 8 · Tier P3 — genre extensions (deferred)

Genre layers add domain-specific widgets on top of Tier P2:

- **Carwars-gamebook** (in design): `slot` zone_role, `place` accepts.kind,
  `piece_offer`, `dice_roll` content fragment, `ui_hints.stat_check`.
- **Hana-smuta board** (sketched in v0.x): card profile + `hand` / `field` /
  `pile` / `score_pile` zones, plus matching `accepts(tokens, same_property)`.

These remain in design conversations. They do not enter Tier P2 until
their underlying primitives have stabilized and a CLI rendering exists.

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
| choice (text/quantity/tokens) | inline form | `> ` prompt | `Entry` / `Spinbox` | `renpy.input` / `LineEdit` |
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

**Tier P2 widgets (piece, zone, round_report)** are not in this table until
their CLI renderings ship in `cli_reference_port.py`.

---

## 10 · Conformance

### 10.1 Fixture suite

```
engine/contrib/conformance/
  fixtures/
    crossroads_inn.json           # canonical narrative turn
    projected_state_all_values.json # all current ProjectedState value types
    sandbox_payload.json          # text/quantity/tokens accepts variants
    quantity_payload.json         # quantity accepts with min/max/unit
    command_hints.json            # raw_command + grammar + interpretation
    dialog_with_avatar.json       # attributed group + avatar_im binding
    pending_media_update.json     # rit format with later update swap
    control_delete.json           # delete control fragment
  cli_reference_port.py           # Python CLI port (Tier S floor)
  legibility.py                   # §5 contract checker
  test_conformance.py             # pytest harness
```

Fixtures are JSON. Each port runs its own conformance test that loads the
fixtures and asserts observable output:

- **Web port**: feed envelopes through the renderer, assert DOM matches
  expected.
- **CLI port**: feed envelopes through `cli_reference_port.py`, assert
  stdout matches expected.
- **Future ports**: same fixtures, port-appropriate assertions.

### 10.2 Legibility check (Tier P1)

`legibility.py` walks each fixture and verifies:

- Every UID referenced by an open choice's `accepts.constraints.target_zone_ref`
  is present in the rendered output.
- Every UID in any `blocker.refs` is present in the rendered output.
- No fragment with `visibility="hidden"` appears in a non-owner session.

Failure prints the offending fixture, choice UID, and missing reference UID.

### 10.3 CLI floor as gate

Per §0.2: `cli_reference_port.py` MUST produce defined output for every
state of every Tier S widget. Tier P1 proposals MUST add CLI rendering
before graduating to Tier S. PRs that change Tier S vocabulary without
updating `cli_reference_port.py` fail CI.

---

## Appendix A — Glossary

| Term | Definition |
|---|---|
| Envelope | One `RuntimeEnvelope` instance — the per-turn payload from `/story/do` or `/story/update`. |
| Fragment | An entry in `RuntimeEnvelope.fragments`. Has stable `uid`. |
| Section | An entry in `ProjectedState.sections`. Refreshed every state-changing turn. |
| Piece (Tier P2) | Identified, state-bearing surface element (card, tile, die, etc.). UI concept; distinct from `tangl.core.token.Token`. |
| Zone (Tier P2) | A `group_type="zone"` group containing pieces. |
| Profile (Tier P2) | A non-normative descriptor of how a `piece.kind` is used. Drives port-conformance subsetting. |
| Predicate (Tier P2) | An author-registered, backend-evaluated boolean function referenced by `predicate_ref`. |
| Tier S/P1/P2/P3 | This document's stratification of stable vs. proposed vocabulary. |

## Appendix B — Open questions (working list)

1. **`payload_type` wrapper** in webapp `ChoiceInputView`. Kill, formalize,
   or fold into a specific `Accepts` variant? Default-kill unless an author
   case appears.
2. **`render_profile` query parameter** on `/story/do` (currently
   defaults to `"raw"`). What other profiles exist? Document or remove.
3. **Sunset clock for legacy `JournalStoryUpdate[]`** in
   `apps/web/src/components/story/fragmentUtils.ts`. Are any backends
   still emitting that shape? If not, the adapters can go.
4. **Predicate registration protocol** (§7.4). Awaiting an MVP author.
5. **Conformance fixture format** — JSON wins for cross-language portability;
   confirmed unless YAML's commentability becomes load-bearing.
6. **Group fragment `dialog` vs DialogFragment** — current engine has both.
   Spec says ports MAY treat them identically. If there's a use case for
   DialogFragment carrying additional fields, it should be promoted. Else,
   plan retirement of the legacy shape.

---

*End of v1.0.*
