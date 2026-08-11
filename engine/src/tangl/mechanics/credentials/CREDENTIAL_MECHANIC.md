# Credential Mechanic — Design Note

```{storytangl-topic}
:topics: credentials
:facets: overview, design
:relation: defines
:related: assembly, games, transaction, prose, media, presence
```

**Status:** LANDED as the shared credential assembly, projection, and game-facing
mechanic. One owner-bound packet manager carries graph-owned bearer/document
components through defect derivation, mediation, recursive text, typed document
pieces, presentation-safe card projection, media provisioning, and JOURNAL
association. Hall Monitor proves durable document custody and authorized reissue,
world-authored consequence return, recurring bearers, and a disclosure-safe
request-ID response window. Missing native components remain graph-owned in an
unpresented slot and enter visible evaluation only after an explicit response.
The sections below describe the current contract and its deferred work, not a
remaining implementation sequence. Advanced appearance comparison, authored
media alternatives, broader response/bluffing policy, and malfeasance remain
separate follow-ups.
**Scope:** the shared credential mechanic — `Credential → Document → Media`,
with carrier/bearer binding — that the credentials checkpoint **game**
(`tangl.mechanics.games.credentials_game`) becomes one consumer of.
**Relation to other docs:**
- `tangl.mechanics.games.CREDENTIALS_LOOP_DESIGN.md` — the game consumer (roster
  shift, restriction map, disposition derivation, mediation). This note defines
  the shared mechanic that consumer adopts.
- `CREDENTIAL_ASSEMBLY_RETROFIT.md` — implementation history for the completed
  assembly/component-manager migration.
- `tangl.media.MEDIA_DESIGN.md` — the spec→adapt→create→provision pipeline this
  builds on.
- `tangl.mechanics.presence` (`look/look.py`) — the bearer-portrait projection
  this *adopts* (see below).
- Supersedes the scratch `media/.../credforge.py` (`CredentialMediaSpec` /
  `CredentialForge`), which predates the mature media pipeline.

---

## 1 · Why this is shared, not game-specific

The credentials *game* is one skin. The primitives underneath it are a reusable
pattern that recurs well outside a checkpoint: the player's own papers in
inventory, an NPC flashing a badge, an access-gated door, a comp tier, a hall
pass. The shared vocabulary now lives in `tangl.mechanics.credentials`, a sibling
of `presence`, `demographics`, and `progression`.

The pattern is a **projection chain**:

```text
Credential   (abstract attestation: issuer, indication, validity)
  → Document  (carrier form: id_card / permit / ticket)
     → Media  (visible card: frame + seal + text + bearer portrait)
```

with **carrier binding** threaded through every layer.

---

## 2 · Three semantic representations

### Credential
An attestation: issuer / indication (purpose or contraband) / validity status.
This is today's component status (`VALID` / `MISSING_SEAL` / `EXPIRED` /
`FORGED`). `CredentialStatus.WRONG_HOLDER` remains accepted only as a compatibility
input and compiles to subject references during materialization.

### Document — the carrier form
A credential rendered as a concrete document type. Two carrier modes:

- **Self-carrying** — an *id card* names a subject; it is valid for the presenter
  when `id.subject_id == packet.bearer_id`.
- **Carrier-bound by reference** — an *id-bound permit* names the same subject as
  the id when `permit.subject_id == id.subject_id`.

### Media — the visible card
`CredentialCardProjection` exposes only presentation-safe card fields. It
requests a renderer-neutral `PortraitSpec` for eligible presence-bound cards and
a `PrintableTextSpec`; once all requested children resolve, a one-level
`CompositionSpec` requests the card RIT. There is no placeholder or later
replacement: a missing or pending child yields no parent CREATE offer, so the
ordinary text piece remains the presentation floor. When the children are
resolved, their content hashes determine the composite identity and the emitted
`MediaFragment` is associated with the document's `PieceFragment` through a new
`GroupFragment`. Media identity and availability never become validity authority.

---

## 3 · Bearer binding adopts the presence projection (the load-bearing idea)

The bearer's photo is **not a credential concept**. It is the *presence system's
portrait of whoever the credential names as bearer*. Presence already exposes
exactly this seam:

- `HasSimpleLook.adapt_look_media_spec(media_role=...) -> LookMediaPayload`
  (`presence/look/look.py`) — any `HasLook` entity projects its appearance into a
  media payload.
- `Look.media_traits()` / `trait_tokens()` and the demographic enums
  (`HairColor`, `SkinTone`, ...) are the shared vernacular.

So:

```text
id_photo = packet.resolve_subject(id.subject_id).adapt_look_media_spec(
    media_role="id_photo"
)
```

**Division of ownership:** credentials owns the *card* (frame, seal, layout,
text); presence owns the *portrait*. The credential mechanic never generates a
face — it asks the bearer's presence for one.

This makes discrepancy rendering fall out for free:

- **valid** → the id subject is the presenting bearer.
- **subject mismatch** → the id (or permit) names a distinct subject entity, even
  if the two subjects currently have identical looks.

This is the visual arm of the **build-correct-then-degrade** factory: degradation
changes a component's subject binding. The evaluator compares bindings; presence
only projects those independently resolved subjects for prose and media.

---

## 3a · Everything reduces to compiling a pile of RITs

The whole media side collapses to one operation: **compose a recipe of RITs
(background, frame, seal/overlay, text layer, optional portrait) into one
composite RIT (or resolve to an existing one that already fills the need).**

- **Non-presence-bound credentials** (permit, ticket — no portrait) compose
  *strictly from SVG content templates + backgrounds + seals/overlays*. Each
  layer is an SVG-rendered or static RIT, composited into one card.
- **Presence-bound credentials** (id card) differ in exactly *one* extra step:
  first **acquire a suitable presence projection** for the document — an
  id-portrait-style close-up. Once that portrait RIT exists, the case **reduces
  to the non-presence case**: it is just one more RIT in the pile.

So credentials' media is a *degenerate composition* — a few fixed layers, no
inventory. That is why it can be the **simple first consumer** that proves the
composition pipeline before the full paperdoll system needs it.

### The real shape: RIT registries + composition strategies

Neither existing forge is the right tool, and both are legacy:

- `svg_forge` is built for **inventorying and assembling parts out of a catalog
  SVG** (`SvgSourceManager` → named `SvgGroup`s), not for compositing a handful of
  independent SVG/RIT wrappers.
- `raster_forge` is a stub whose intended job — the **avatar paperdoll
  assembler** (layer body + outfit + ornaments from the `presence` wearable/outfit
  stack) — is poorly named; it is really a **file/resource forge**, not a raster
  one.

The unifying target is to refactor both into **RIT registries + composition
strategies**:

- **Each layer/part is its own mini-RIT** — a catalog SVG's groups, a seal, a
  rendered text block, a background, a portrait are all RITs, indexed in a
  registry. (This generalizes `MediaResourceRegistry` + `SvgSourceManager` into
  one notion: everything is a RIT.)
- **A composition strategy** combines selected RITs into a new composite RIT —
  SVG-assembly, raster-paste, etc. are interchangeable strategies behind one
  interface. (This generalizes `SvgGroup` assembly and the PIL paste into one.)
- **The composite is itself a RIT** — content-addressed, reused on identical
  recipe, and it rides the existing `MediaFragment` journal path unchanged.

A `MediaSpec` is then exactly the user's "functional description of RIT
manipulation and composition": *select mini-RITs from registries + apply a
strategy → composite RIT, or resolve to an existing one.*

**Credentials is the degenerate consumer** of this — a few fixed layers, one
strategy, no inventory management. The avatar paperdoll system is the rich
consumer (large wearable inventories, many layers). They share the registry +
strategy framework; credentials is the simplest thing that proves it.

**The one hard rule:** route through the media framework — `MediaSpec →
MediaSpecProvisioner → MediaRIT → MediaFragment`. The landed one-level
`CompositionSpec` proves that a composite is just another RIT and rides the same
journal path. The remaining gap is broader catalog-driven composition strategies,
not credential-card provisioning. If credentials hand-rolls a richer composition
or journal channel, it duplicates plumbing that paperdolls and other media
consumers also need.

> **Boundary:** broader registry + strategy work is a media-subsystem decision,
> not a credentials extension. Credentials consumes the minimal shared compositor
> and should not force a general media DAG or catalog abstraction into this package.

### Acquiring the portrait RIT (three modes)

The id-portrait can be specified:

1. **Directly** — a given portrait RIT.
2. **By properties → selection** — demographic/look properties select from a
   range of pre-created assets (the world portrait pool).
3. **By properties → dynamic generation** — `comfy_forge` / `stable_forge`
   generate from the look descriptor.

A richer variant of (3) drives the **side-by-side presentation**: pre-render
everyone's base portraits once, then send a base portrait *as an img2img/
controlnet reference* to re-generate the candidate's appearance **today** —
slightly different hairstyle, expression, and current clothing — for the live
figure standing at the counter. The card carries the *official* portrait; the
candidate standing there is a today-variation of the *same base presence*. That
makes the compare-the-photo-to-the-face interaction literal.

---

## 3b · Advanced: presence-degradation mediation (deferred)

Once the card photo and the live candidate are both presence projections, a
mismatch is a **presence diff**, and severity depends on whether the mismatched
trait is *mutable*:

- **Mutable mismatch** (hair color/style, expression, clothing) — the card shows
  blonde hair, the candidate is now brunette; they claim they recently dyed it.
  Probably **OK** if nothing else is wrong — clearable by claim, because hair is
  legitimately changeable.
- **Immutable mismatch** (facial bone structure / identity) — the card's face
  does not match the candidate's *and* the hair differs; the dyed-hair claim is a
  cover for a **false id** → deny / arrest.

So the holder-match check graduates: a same-base-identity / mutable-trait
difference is mitigatable; a different-base-identity difference is a crime, no
matter what claim accompanies it. This needs presence to distinguish **base
identity** (immutable) from **mutable presentation** — advanced presence
degradation, and a game-consumer mediation outcome (a presence-aware extension of
B.2). Deferred; noted here because it is the reason the presence projection must
separate identity from presentation.

---

## 4 · Forward-looking default styling and override policy

The landed proof supplies neutral text and one-level composition for eligible
presence-bound cards, including their portrait child, not a complete styled
credential catalog. A future default styling package may let a bare credential
render a conventional card with:

- a default card frame (SVG primitives),
- a small seal set (valid / wrong / missing variants, SVG),
- a default text/date layout,
- a placeholder portrait silhouette (when no bearer look is available).

A world or game should **override by data, not code**: region names, seal designs,
permit/indication catalog, and card styling would be provided as configuration.
Credential worlds already supply semantic regions, issuers, and document types;
future styling should consume those bounded world catalogs rather than inventing
a second credential truth model. This is the *template for the template* — a
working neutral projection becomes the copy-and-reskin starting point.

---

## 5 · Forward-looking media tiers

The shared request/provisioning path can eventually support three content tiers:

1. **Engine SVG defaults** — deterministic, repo-safe, `FAST_SYNC` via
   `svg_forge` (frame/seal/text as SVG; portrait an `<image>` ref). The test and
   conformance path.
2. **World pre-rendered portrait pool** — a world's compile / first-run / setup
   step generates ~N portraits matching a demographic distribution into the
   **world media directory** (distributed with the world, content-addressed,
   deduped). Raster here is fine — it is *not* in the engine repo.
3. **Runtime gen-AI portrait** — optional `comfy_forge` / `stable_forge`
   generation into **story-scope** inventory (ASYNC; soft-dependency, so the
   card frame renders immediately and the portrait fills in).

**Raster / LFS guidance.** "No raster in the engine repo" is test/demo hygiene
(stray PNGs get LFS'd and confuse non-LFS install patterns), not dogma. It is
waivable per-case with an explicit, documented LFS exception or a fallback. When
a skin has *a lot* of vector media, the CarWars precedent applies: commit SVG
under LFS and reverse the policy deliberately. The rule is really "no
*unmanaged* raster."

---

## 6 · Disclosure discipline carries over

The card renders the candidate's **presentation**: a forged seal draws a subtly
wrong seal, a subject-mismatched card names a different presence entity, and an
expired card shows a past date. These are *visible to a careful look* — but the *finding*
("this seal is forged") is revealed only by inspecting. The image is the visual
analog of `presented_documents` (visible) vs. `hidden_facts` (revealed on
inspection). The card must **not** flag "FORGED" in red; the player must notice.
Same discipline already enforced on the move menu and info channels.

---

## 6a · Media is enrichment — prose carries the floor

Media is a **soft dependency** (MEDIA_DESIGN): the journal text is the primary
artifact, and the widget vocab's CLI-floor rule requires every interaction be
reachable by a text client. So a "visual" discrepancy cannot live *only* in
pixels. The resolution is that **the discrepancy lives in the structured truth,
not in any one rendering channel**: a portrait mismatch is a difference in the
`Look` data and the subject references, and presence already projects that truth to
*both* channels —

- **prose** via `Look.describe()` / `trait_tokens()`,
- **media** via `adapt_look_media_spec()`.

MEDIA_DESIGN frames these as symmetric output dimensions of one adapted intent.
So a subject-mismatched card is, for a text client, a **prose look-diff**: the id reads
"a fair-skinned woman, blonde, neutral"; the traveler at the counter reads "a
fair-skinned woman, dark hair." The player compares two *descriptions* exactly as
a rich client compares two *faces*. The discrepancy is reachable at the CLI
floor; the image merely makes the comparison nicer.

**The honest caveat (a real, non-blocking weak spot).** Images allow a
discrepancy to be *present but missable* — you can simply fail to look closely at
a faintly-wrong seal. Prose struggles to be both faithful and missable: "the
seal's color is slightly off" already half-states the finding, where an image
just shows the seal and lets you not notice. So a class of **subtle visual
discrepancies** (fine seal tells, micro-expression, print-quality cues) renders
weakly on non-visual clients — it tends to either leak or become unspottable.
Mitigations, none of which block the media work:

- author the prose to give the **raw observation, not the judgment** (describe
  the seal's full visible detail neutrally; let the player decide), preserving
  missability;
- let a skin **select failure modes by client profile** — lean on coarse,
  text-faithful discrepancies (missing seal, wrong region name, expired date,
  whole-identity mismatch) for CLI-floor play, and reserve the subtle-visual
  modes as enrichment that rich clients reward.

In short: most credential discrepancies are structured and project cleanly to
prose; a minority are genuinely visual-first and are simply *better* with media —
worth naming, not worth gating the media work on.

---

## 7 · Landed composition and current boundary

The shared credentials package owns the domain vocabulary and canonical
assembly-backed packet path. `CredentialCase` carries one owner-bound
`CredentialPacketManager`; offer arrival materializes it from the selected
catalog before the encounter becomes active. Defect derivation, mediation,
recursive text, document pieces, and card projection all read that same
graph-owned component state.

Eligible ID cards request a Presence-owned portrait and generic printable text,
then provision one resolved `CompositionSpec` parent during frontier PLANNING.
The text `PieceFragment` remains unconditional. A `MediaFragment` appears only
when the complete card resolves, and a `GroupFragment(group_type="piece_media")`
associates the two without overloading provenance. Complete authored document
replacements suppress generated card content before projection.

Hall Monitor exercises the path as a disclosure-safe visual witness: the live
candidate and recorded document subject project independently, while neither
the portrait nor card exposes the evaluator's subject-mismatch finding. The
same world also proves a component moving through desk custody, being restored
to native validity and rebound to a bearer, and later entering the ordinary
evaluator without a parallel date or waiver algorithm.

Credentials must continue to consume the shared `MediaSpec →
MediaSpecProvisioner → MediaRIT → MediaFragment` path. It does not own a packet
sheet, recursive media DAG, credential forge, or parallel JOURNAL channel.

---

## 8 · Open questions

- **Portrait pool keying.** Procedural candidates carry stable `HasSimpleLook`
  subjects. The remaining question is how a world maps those subject ids to
  reusable portrait-pool entries.
- **Broader RIT catalog + composition-strategy surface (media-layer, §3a step
  0).** The minimal one-level ``CompositionSpec`` compositor landed in PR #326.
  What remains open is generalizing the legacy `svg_forge` catalog-assembler and
  the `raster_forge`/file-forge stub into registries of mini-RITs plus
  interchangeable composition strategies. Recipe/spec format (layer list +
  transforms + strategy + content-addressing) remains a media concern;
  paperdolls, not credentials, are the likely forcing consumer.
