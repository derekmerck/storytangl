# Credentials Bundle — Widget Vocabulary Extensions

**Bundle id:** `credentials`
**Vocab spec base:** `STORYTANGL_WIDGET_VOCAB.md` v1.5
**Status:** draft v0.2 · aligned to v1.5 core vocabulary
**Genre:** narrative inspection / verification, *Papers Please*-inspired
**Audience:** authors writing credentials-style bundles; port implementers covering the credentials profile suite

This document is a **Tier P3 genre extension** (per main spec §8). It
introduces no new top-level vocabulary; it codifies conventions on top
of v1.5 for inspection / verification gameplay.

The credentials-specific enrichments are mostly naming and emphasis
conventions. A generic client that ignores packet styling, finding
severity, and disposition color still conforms when it renders the
underlying zones, pieces, key/value findings, blockers, and choices.

---

## 0 · Genre summary

Credentials bundles model **verification under uncertainty**: a player
inspects packets of documents against a published rule-set, applies
mediation moves to gather information, and disposes of each candidate
(allow / deny / arrest / escalate) under time and accuracy pressure.

**Three orthogonal patterns** the credentials genre exercises:

| Pattern | Main spec mechanism | Genre layer adds |
|---|---|---|
| Document packet inspection | `zone` group with `accepts.kind="pieces"` choice | `zone_role="packet"`, `ui_hints.emphasis` per finding severity |
| Severity-coded findings | `KvFragment` + `KvRow.emphasis` + `extra="allow"` for finding metadata | conventional `code` / `target` / `state` fields on findings |
| Mediation / disposition tree | `ChoiceFragment` with `accepts.kind="pick"` and `Blocker[]` for gated options | conventional `ui_hints.emphasis` severity (primary/warning/danger) for allow/deny/arrest |

**On authorship vs. rendering.** The credentials *engine architecture*
(`CREDENTIALS_LOOP_DESIGN.md`) describes how the bundle authors
candidates, restriction maps, indications, and outcome hierarchies.
This document describes how the *client* renders the engine's emitted
fragments. Keep the two separated: the engine-side `Indication`,
`RestrictionLevel`, `Outcome`, and `Move` enums are bundle authoring
vocabulary; this doc is rendering contract.

---

## 1 · Domain vocabulary mapped to v1.5

| Credentials concept | v1.5 surface |
|---|---|
| Candidate | `PieceFragment(kind="candidate")` with `properties: {name, declared_purpose, declared_origin, photo_url}` |
| Credential packet | `GroupFragment(group_type="zone", zone_role="packet")` containing the candidate's documents |
| Document (permit, id_card, ticket, asylum_form, etc.) | `PieceFragment(kind=<document_type>)` with `properties: {seal, holder, issue_date, expiry, photo_url, ...}` |
| Restriction map / current rules | `ProjectedState` section with `kind="restrictions"`, `value_type="kv_list"`, one annotated row per indication |
| Inspection move | `ChoiceFragment(accepts.kind="pieces", min=1, max=1, constraints.target_zone_ref=<packet_uid>)` |
| Finding | `KvRow` inside a scene-bound `KvFragment` or a projected section, with `emphasis` for severity and `extra="allow"` fields `{code, target, state}` |
| Mediation move | `ChoiceFragment(accepts.kind="pick")` for verify-id / search-bag; `accepts.kind="pieces"` for request-specific-doc |
| Bribe offer | `ChoiceFragment(accepts.kind="compose")` with parts `[{decision: pick}, {amount: quantity}]`, or `accepts.kind="pick"` over discrete accept/refuse |
| Disposition | `ChoiceFragment(accepts.kind="pick")` with `ui_hints.emphasis` keyed to severity (primary/warning/danger) |
| Shift summary | `ProjectedState` section with `value_type="table"`, columns `Candidate / Decision / Correct / Notes` |
| Score / accuracy meter | `ProjectedState` `scalar` or annotated `kv_list` row with `hint="bar"` |

---

## 2 · Packet zone conventions

The credential packet is a zone holding the candidate's documents.
Recommended layout:

```js
{
  uid: "z-packet",
  fragment_type: "group",
  group_type: "zone",
  member_ids: ["pc-permit", "pc-id-card", "pc-ticket"],
  layout_hints: { orientation: "row", reveal: "all" },
  hints: { label_text: "Credentials packet", style_tags: ["packet"] }
}
```

**Document pieces** live inside the packet zone:

```js
{
  uid: "pc-permit",
  fragment_type: "piece",
  piece_id: "permit-9472",
  kind: "permit",
  zone_ref: "z-packet",
  properties: {
    seal: "Imperial",
    holder: "Anya Volkov",
    issue_date: "2026-04-12",
    expiry: "2027-04-12",
    purpose: "merchant",
    photo_url: "..."
  },
  hints: { label_text: "Permit (Imperial)" }
}
```

The CLI port renders the packet as:

```text
[Credentials packet]
  - Permit (Imperial)  holder=Anya Volkov  expires 2027-04-12  purpose=merchant
  - ID card            holder=Anya Volkov  issued 2025-11-03   photo=present
  - Travel ticket      origin=Kalden       destination=here    issued 2026-05-19
```

---

## 3 · Findings as annotated KvRows

A finding is a row in a `KvFragment` (scene-bound) or a `ProjectedSection`
(if persistent for the shift). It uses `KvRow.emphasis` for severity and
`extra="allow"` for the bundle-specific fields.

```js
// scene-bound finding fragment after the player inspects the permit
{
  uid: "f-finding-permit-expiry",
  fragment_type: "kv",
  content: [
    {
      key: "permit_seal",
      value: "Imperial",
      emphasis: "ok",
      code: "seal_valid",
      target: "pc-permit",
      state: "verified"
    },
    {
      key: "permit_purpose",
      value: "merchant",
      emphasis: "warn",
      code: "purpose_mismatch_declared",
      target: "pc-permit",
      state: "flag"
    },
    {
      key: "permit_expiry",
      value: "2027-04-12",
      emphasis: "ok",
      code: "permit_current",
      target: "pc-permit",
      state: "verified"
    }
  ],
  hints: { style_tags: ["findings", "inline"] }
}
```

**Severity convention:**

| `emphasis` | Meaning | CLI rendering |
|---|---|---|
| `ok` | Verified clean | `✓` prefix |
| `subtle` | Informational; not actionable | no prefix |
| `warn` | Mitigatable infraction; mediation move available | `!` prefix |
| `danger` | Crime; arrest justified | `!!` prefix |

The `code` field is author-stable for downstream predicate evaluation
and test fixtures. `target` is the UID of the piece the finding
relates to. `state` is one of `verified`, `flag`, `unverified`,
`disputed`.

---

## 4 · Mediation moves

Mediation moves are choices the player invokes between initial
inspection and final disposition. They typically reveal additional
findings or unlock new options.

```js
[
  {
    uid: "f-choice-verify-id",
    fragment_type: "choice",
    edge_id: "e-verify-id",
    text: "Verify the ID card against the registry.",
    accepts: { kind: "pick" },
    ui_hints: { hotkey: "1", emphasis: "subtle", cost_previews: [{ ledger_key: "time", delta: -1 }] }
  },
  {
    uid: "f-choice-request-permit",
    fragment_type: "choice",
    edge_id: "e-request-permit",
    text: "Request the missing permit.",
    accepts: {
      kind: "pieces",
      min: 1, max: 1,
      constraints: { target_kind: ["permit"] }
    },
    available: false,
    unavailable_reason: "No permit shown.",
    blockers: [
      { code: "no_permit_in_packet", message: "Candidate has not provided a permit.", refs: ["z-packet"] }
    ],
    ui_hints: { hotkey: "2" }
  },
  {
    uid: "f-choice-search",
    fragment_type: "choice",
    edge_id: "e-search",
    text: "Search the candidate's belongings.",
    accepts: { kind: "pick" },
    ui_hints: { hotkey: "3", emphasis: "warning", cost_previews: [{ ledger_key: "time", delta: -2 }] }
  }
]
```

**Mediation move catalog (conventional, non-normative):**

| Move kind | accepts | Typical effect |
|---|---|---|
| `verify_<source>` | `pick` | Backend rolls validity against a registry; emits new findings |
| `request_<document>` | `pieces` over a hypothetical document kind | Candidate produces the doc (new piece appears in packet) or refuses (Blocker on disposition) |
| `search_<target>` | `pick` | Backend reveals previously-hidden contents or contraband |
| `cross_check_<a>_<b>` | `pick` | Backend evaluates consistency between two pieces; new finding |
| `interrogate` | `text` (raw question) | Bundle-authored response from candidate; may seed Phase C bribery / threats |

Bundles MAY introduce additional mediation kinds; the rendering is
the same shape (a `ChoiceFragment` with appropriate `accepts.kind`).

### `ui_hints.validity_check` optional preview

Most credentials checks should remain opaque until the backend returns a
finding. When a bundle wants to advertise that a mediation move consumes
time or checks a published rule, it MAY add a genre-specific hint:

```python
class ValidityCheckHint(BaseModel):
    label: str                            # "Registry lookup"
    target_ref: str | None = None         # document or candidate UID
    published_rule: str | None = None     # player-visible rule label
    risk_text: str | None = None          # "Costs 1 time"
```

This follows the same pattern as carwars/training `stat_check`: the hint
is advisory and legibility-focused. The backend still performs the lookup
and emits authoritative `KvRow` findings.

---

## 5 · Disposition severity

Disposition is the terminal commit per candidate. Conventional severity
mapping:

```js
[
  { uid: "f-disp-allow", fragment_type: "choice", edge_id: "e-allow",
    text: "Allow passage.", accepts: { kind: "pick" },
    ui_hints: { hotkey: "a", emphasis: "primary" } },
  { uid: "f-disp-deny", fragment_type: "choice", edge_id: "e-deny",
    text: "Deny passage.", accepts: { kind: "pick" },
    ui_hints: { hotkey: "d", emphasis: "warning" } },
  { uid: "f-disp-arrest", fragment_type: "choice", edge_id: "e-arrest",
    text: "Arrest.", accepts: { kind: "pick" },
    available: false,
    unavailable_reason: "Insufficient evidence for arrest.",
    blockers: [{ code: "no_arrestable_findings",
                 message: "No finding with emphasis=danger present.",
                 refs: [] }],
    ui_hints: { hotkey: "x", emphasis: "danger" } }
]
```

The CLI port renders disposition as:

```
a) Allow passage.
d) Deny passage.
x) Arrest.  (locked: Insufficient evidence for arrest.)
```

---

## 6 · Restriction map projection

The current shift's restriction map renders as a `ProjectedState`
section the player can consult at any time:

```js
{
  section_id: "restrictions",
  title: "Shift directives",
  kind: "restrictions",
  value: {
    value_type: "kv_list",
    items: [
      { key: "Imperial citizens", value: "allowed", emphasis: "ok",
        hint: "tag" },
      { key: "Kaldenese refugees", value: "allowed with permit",
        emphasis: "warn", hint: "tag" },
      { key: "Eastern merchants", value: "denied — embargo",
        emphasis: "danger", hint: "tag" },
      { key: "Diplomatic envoys", value: "allowed — privileged",
        emphasis: "subtle", hint: "tag" }
    ]
  },
  hints: { style_tags: ["sidebar"] }
}
```

Per §5.1 Decision Legibility, every restriction that could gate a
disposition's blocker MUST appear in this projection. The
`unavailable_reason` on disposition choices references it
(`"Eastern origin under embargo — see Shift directives"`).

---

## 7 · Shift summary

End-of-shift summary is a `ProjectedState` table:

```js
{
  section_id: "shift_summary",
  title: "Shift summary",
  kind: "shift_summary",
  value: {
    value_type: "table",
    columns: ["Candidate", "Decision", "Correct", "Findings"],
    rows: [
      ["Anya Volkov", "Allowed", "✓", "purpose mismatch flagged"],
      ["Bek Tarsus", "Denied", "✓", "permit expired"],
      ["Kavel Ren", "Allowed", "✗", "missed embargo origin"]
    ]
  }
}
```

---

## 8 · Worked example — one candidate, three turns

### Turn 1 — candidate arrives

```js
fragments: [
  { uid: "f-prose-1", fragment_type: "content",
    content: "A merchant in worn furs approaches the booth. He sets down a
              folded packet and waits, breath misting in the cold." },

  // Candidate piece
  { uid: "pc-candidate-bek", fragment_type: "piece",
    piece_id: "bek-tarsus", kind: "candidate",
    properties: {
      name: "Bek Tarsus",
      declared_purpose: "merchant",
      declared_origin: "Kalden",
      photo_url: "..."
    },
    hints: { label_text: "Bek Tarsus (declared merchant)" } },

  // Packet zone
  { uid: "z-packet", fragment_type: "group", group_type: "zone",
    member_ids: ["pc-permit", "pc-id-card", "pc-ticket"],
    layout_hints: { orientation: "row" },
    hints: { label_text: "Credentials packet" } },

  // Document pieces (abbreviated)
  { uid: "pc-permit", fragment_type: "piece",
    piece_id: "permit-9472", kind: "permit", zone_ref: "z-packet",
    properties: { seal: "Imperial", holder: "Bek Tarsus",
                  expiry: "2026-03-01", purpose: "merchant" },
    hints: { label_text: "Permit (Imperial)" } },
  { uid: "pc-id-card", fragment_type: "piece",
    piece_id: "id-3382", kind: "id_card", zone_ref: "z-packet",
    properties: { holder: "Bek Tarsus", origin: "Kalden" },
    hints: { label_text: "ID card" } },
  { uid: "pc-ticket", fragment_type: "piece",
    piece_id: "ticket-117", kind: "ticket", zone_ref: "z-packet",
    properties: { origin: "Kalden", destination: "Imperial Gate",
                  issued: "2026-05-19" },
    hints: { label_text: "Travel ticket" } },

  // Inspect choice
  { uid: "f-choice-inspect", fragment_type: "choice",
    edge_id: "e-inspect",
    text: "Inspect a document.",
    accepts: {
      kind: "pieces",
      min: 1, max: 1,
      constraints: { target_zone_ref: "z-packet" }
    },
    ui_hints: { hotkey: "1" } },

  // Disposition options (initially gated)
  { uid: "f-disp-allow", fragment_type: "choice", edge_id: "e-allow",
    text: "Allow passage.", accepts: { kind: "pick" },
    available: false,
    unavailable_reason: "Inspect documents first.",
    ui_hints: { hotkey: "a", emphasis: "primary" } },
  { uid: "f-disp-deny", fragment_type: "choice", edge_id: "e-deny",
    text: "Deny passage.", accepts: { kind: "pick" },
    ui_hints: { hotkey: "d", emphasis: "warning" } }
]
```

### Turn 2 — player inspects permit

After committing `e-inspect` with `payload: {piece_ids: ["pc-permit"]}`:

```js
fragments: [
  { uid: "f-prose-2", fragment_type: "content",
    content: "You unfold the permit. The Imperial seal is sound, but the
              date stamp shows expiry months past." },

  // Findings emitted by the backend
  { uid: "f-finding-permit", fragment_type: "kv",
    content: [
      { key: "permit_seal", value: "Imperial", emphasis: "ok",
        code: "seal_valid", target: "pc-permit", state: "verified" },
      { key: "permit_expiry", value: "2026-03-01", emphasis: "danger",
        code: "permit_expired", target: "pc-permit", state: "flag" }
    ] },

  // Allow now gated by the expired permit
  { uid: "f-disp-allow", fragment_type: "control",
    ref_type: "fragment", ref_id: "f-disp-allow",
    payload: {
      available: false,
      unavailable_reason: "Permit expired (see findings).",
      blockers: [{ code: "permit_expired",
                   message: "Permit expired 2026-03-01.",
                   refs: ["pc-permit"] }]
    } }
]
```

Same packet, same disposition slots — only an annotated finding fragment
and a control mutation. The CLI port re-renders:

```text
You unfold the permit. The Imperial seal is sound, but the date stamp
shows expiry months past.

  [findings]
    ✓  permit_seal = Imperial
    !! permit_expiry = 2026-03-01

1) Inspect a document.
a) Allow passage.   (locked: Permit expired (see findings).)
d) Deny passage.
```

### Turn 3 — disposition

Player commits `e-deny`. The backend returns the next candidate and
appends a row to the shift summary.

---

## 9 · Time pressure

Per main spec §0.3 and §0.6, time pressure is **backend territory**.
The bundle MAY emit periodic envelopes that decrement a visible time
counter via `update` control fragments. When time reaches zero, the
backend emits a control fragment marking all open dispositions
`available=false` with `unavailable_reason="Shift ended."`.

No client-side timer primitive. Per §0.2 CLI Floor Rule, the CLI port
renders the projected `time_remaining` row exactly as the web port
does — both update only on backend tick.

---

## 10 · Port parity addendum

| Widget | Web (Vue) | CLI | tkinter | Hypothetical Godot |
|---|---|---|---|---|
| Candidate piece | photo + declared-purpose chip | line: `<name> (declared <purpose>, from <origin>)` | `Label` + small image | NPC 3D portrait |
| Packet zone | row of document tiles | `[packet]` block of `- <doc>` lines | `Frame` of document cards | spatial array on counter |
| Finding row (`ok`) | check icon + muted text | `✓ <key> = <value>` | green text | green chip |
| Finding row (`warn`) | warning chip + amber text | `! <key> = <value>` | amber text | amber chip |
| Finding row (`danger`) | danger chip + red text + pulse | `!! <key> = <value>` | red text | red chip + sound |
| Disposition (`primary`) | green button | `a) Allow passage.` | green `Button` | green panel |
| Disposition (`warning`) | amber button | `d) Deny passage.` | amber `Button` | amber panel |
| Disposition (`danger`) | red button with confirm | `x) Arrest.` | red `Button` (confirm dialog) | red panel + confirm |
| Disposition (locked) | grayed + reason tooltip | `a) Allow.  (locked: <reason>)` | disabled + label | grayed + tooltip |
| Restriction map | sidebar `kv_list` | `[directives]` block | `Frame` of rules | corkboard |
| Shift summary | table | aligned columns | `ttk.Treeview` | scroll table |

---

## Appendix — Prior art

Lucas Pope's *Papers, Please* (2013) is the immediate inspiration for
this genre profile. Pope's design innovation is decoupling the
*procedural* (verify documents against shifting rules) from the
*moral* (every disposition is a small ethical choice). This bundle
profile honors both halves: the verification mechanics are
contract-rendered cleanly; the moral weight lives in bundle-authored
prose around dispositions.

The credentials genre also overlaps with judicial process simulators
(*Phoenix Wright*-style logical-discrepancy hunting), bureaucratic
fiction (Kafka's *The Trial*, Mieville's *Embassytown*), and
contemporary procedural games (*This War of Mine*'s ethical-triage
loops). The vocabulary lifts cleanly to all of them.

The credentials *engine architecture* is documented separately in
`CREDENTIALS_LOOP_DESIGN.md`. The engine-side `Outcome` hierarchy,
`Move` enum, `RestrictionLevel` ordering, and indication-generation
doctrine are authoring concerns; this document is rendering contract.

---

*End of credentials EXTENSIONS v0.2.*
