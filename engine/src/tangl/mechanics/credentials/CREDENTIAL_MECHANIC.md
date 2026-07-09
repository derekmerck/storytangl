# Credential Mechanic — Design Note

**Status:** PLANNED (design precedes code; this doc stakes the intended shape);
game-layer packet-manager adapter landed 2026-06-25 as a compatibility bridge,
not the full global mechanic extraction.
**Scope:** the *global* credential mechanic — `Credential → Document → Media`,
with carrier/bearer binding — that the credentials checkpoint **game**
(`tangl.mechanics.games.credentials_game`) becomes one consumer of.
**Relation to other docs:**
- `tangl.mechanics.games.CREDENTIALS_LOOP_DESIGN.md` — the *game* layer (roster
  shift, restriction map, disposition derivation, mediation). This note is its
  global-mechanic counterpart; the game points *up* to here.
- `CREDENTIAL_ASSEMBLY_RETROFIT.md` — the migration plan for turning the current
  game-layer packet-manager bridge into the shared assembly/component-manager
  pattern.
- `tangl.media.MEDIA_DESIGN.md` — the spec→adapt→create→provision pipeline this
  builds on.
- `tangl.mechanics.presence` (`look/look.py`) — the bearer-portrait projection
  this *adopts* (see below).
- Supersedes the scratch `media/.../credforge.py` (`CredentialMediaSpec` /
  `CredentialForge`), which predates the mature media pipeline.

---

## 1 · Why this is global, not game-specific

The credentials *game* is one skin. The primitives underneath it are a reusable
pattern that recurs well outside a checkpoint: the player's own papers in
inventory, an NPC flashing a badge, an access-gated door, a comp tier, a hall
pass. Those primitives currently live inside the games package
(`credentials_enums.py`); promoting them to `tangl.mechanics.credentials` (a
sibling of `presence`, `demographics`, `progression`) was always the intended
shape.

The pattern is a **projection chain**:

```text
Credential   (abstract attestation: issuer, indication, validity)
  → Document  (carrier form: id_card / permit / ticket)
     → Media  (visible card: frame + seal + text + bearer portrait)
```

with **carrier binding** threaded through every layer.

---

## 2 · The three layers

### Credential
An attestation: issuer / indication (purpose or contraband) / validity status.
This is today's `CredentialToken` (`VALID` / `MISSING_SEAL` / `EXPIRED` /
`FORGED` / `WRONG_HOLDER`).

### Document — the carrier form
A credential rendered as a concrete document type. Two carrier modes:

- **Self-carrying** — an *id card* identifies its own holder; the bearer *is* the
  carrier.
- **Carrier-bound by reference** — a *permit* references an id; the binding is the
  `holder_matches` axis, and a broken binding is `WRONG_HOLDER`. ("Carrier-bound
  id" = the permit-references-id relationship.)

### Media — the visible card
A `CredentialCardSpec(MediaSpec)` composes the card: frame + seal(issuer,
validity) + text(name, indication, dates) + **bearer portrait**. Built on the
existing `MediaSpec` two-phase `adapt → create` contract, resolved through
`MediaSpecProvisioner`, attached as a `MediaFragment` on the document's
`PieceFragment` (which Bridge.1 already emits). Content-addressed → dedupe +
caching + reproducibility (adapted-spec hash) for free.

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
id_photo  =  bearer.adapt_look_media_spec(media_role="id_photo")
```

**Division of ownership:** credentials owns the *card* (frame, seal, layout,
text); presence owns the *portrait*. The credential mechanic never generates a
face — it asks the bearer's presence for one.

This makes discrepancy rendering fall out for free:

- **valid** → bind the *true bearer's* look.
- **`WRONG_HOLDER`** → bind a *different* entity's look (or a mismatched
  demographic), so the photo doesn't match the declared identity — a thing the
  player can *spot*.

This is the visual arm of the **build-correct-then-degrade** factory the game
already has: the same `degrade` step that sets a token's status drives which look
the card binds. The credential mechanic reads token status; it does not maintain
a parallel error flag.

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
MediaSpecProvisioner → MediaRIT → MediaFragment`. The journal-integration path for
a *single produced RIT already exists* (a handler emits `MediaFragment(content=
rit)`; the service dereferences it), and a composite is just a RIT, so it rides
the same path. The genuine gap is only the *composition framework* (registries +
strategies). If credentials hand-rolls its own composition **and** its own journal
emission outside this, we duplicate exactly the plumbing paperdolls also need.

> **Dependency, flagged:** the registry + strategy refactor is a **media-subsystem
> design decision**, not a credentials one. Credentials should *consume* it, not
> drive a big media refactor on its own schedule. Phase D therefore depends on at
> least a minimal composition-strategy surface existing; worth its own media-layer
> design note / issue rather than being smuggled in through this mechanic.

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
degradation, and a game-layer mediation outcome (a presence-aware extension of
B.2). Deferred; noted here because it is the reason the presence projection must
separate identity from presentation.

---

## 4 · Default projections + the override model ("template for the template")

`tangl.mechanics.credentials` ships **default projections** so a bare credential
renders a working card with no world-specific authoring:

- a default card frame (SVG primitives),
- a small seal set (valid / wrong / missing variants, SVG),
- a default text/date layout,
- a placeholder portrait silhouette (when no bearer look is available).

A world or game **overrides by data, not code**: region names, seal designs,
permit/indication catalog, card styling are provided as configuration, and the
default projection machinery consumes them as guidance. The credentials demo game
supplies its regions, seals, and permit types; the machinery "just does its
thing." This is the *template for the template* — engine defaults prove the
projection and are the copy-and-reskin starting point (Lethesford University →
any institution).

---

## 5 · Media policy: three tiers, raster stays out of the engine repo

Same `MediaDep`, three provisioning tiers:

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
wrong seal, a wrong-holder card draws a mismatched portrait, an expired card
shows a past date. These are *visible to a careful look* — but the *finding*
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
`Look` data and the token status, and presence already projects that truth to
*both* channels —

- **prose** via `Look.describe()` / `trait_tokens()`,
- **media** via `adapt_look_media_spec()`.

MEDIA_DESIGN frames these as symmetric output dimensions of one adapted intent.
So a wrong-holder card is, for a text client, a **prose look-diff**: the id reads
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

## 7 · Staged plan (media spec is the forcing function)

### Assembly compatibility step already landed

The shared credentials package now owns the credential domain vocabulary and an
assembly-backed packet path. The live game package still exposes its
value-object `CredentialPacketManager` adapter, but `CredentialCase` can now also
carry `tangl.mechanics.credentials.CredentialPacketManager`, an owner-bound
manager over graph credential components. Both paths answer the same discovery
surface used by disposition derivation, so the current roster/game/demo data
keeps working while graph-backed packet identity can be adopted incrementally.

This is still not the full credential mechanic described above: document/media
projection has not landed, presence-snapshot holder binding is not implemented,
contraband remains value-shaped, and `credential_gate` remains the reference
consumer rather than a retrofit target. It does establish the retirement path for
the current game-local implementation: future packets should either embed value
credentials deliberately or store graph-token credentials by id through the same
owner-bound manager pattern used by outfits, vehicles, and connector groups.

0. **(Media-layer prerequisite, separate track.)** A minimal **RIT registry +
   composition-strategy** surface, replacing the legacy `svg_forge`/`raster_forge`
   shape (§3a). Owned by media, not credentials; Phase D consumes it.
1. **`CredentialCardSpec`** as a `MediaSpec`, built *on the media framework*
   (`MediaSpec` → `MediaSpecProvisioner` → `MediaRIT` → `MediaFragment`) and the
   composition surface from (0) — **not** a hand-rolled composition or journal
   path. It reads a credential's status + carrier binding to render discrepancies,
   and calls presence's `adapt_look_media_spec(media_role="id_photo")` for the
   bearer portrait. The genuine *second consumer* of the credential primitives and
   the *simplest consumer* of the composition framework.
2. **Extract primitives** (`Credential`, `Document`, carrier binding) into
   `tangl.mechanics.credentials` — partially landed for the current enum/value
   vocabulary and assembly packet proof. Carrier binding still waits on the
   presence-snapshot surface.
3. **Re-point the game** at the promoted primitives; the game adds its overrides
   (regions, seals, permits).
4. **Default assets** land alongside (1) so the projection is provable from day
   one.

Steps 1–4 keep the merged game working; nothing is a big-bang refactor. Step 0 is
the one genuine dependency, and it is a media-subsystem concern in its own right.

---

## 8 · Open questions

- **Portrait pool keying.** Demographic descriptor → portrait identity mapping for
  the world pre-render pool (so `WRONG_HOLDER` can deterministically bind a
  *different* pool entry, and so a base portrait can be re-used as the img2img
  reference for the side-by-side live figure). Likely a `demographics`-driven key.
- **Where bearer identity lives for procedural candidates.** A sampled candidate
  has no `HasLook` entity yet; the factory may need to materialize a minimal
  presence (a `Look`) per candidate so the card can bind a portrait — and so the
  base-identity-vs-mutable-presentation split (§3b) has somewhere to live.
- **RIT registry + composition-strategy surface (media-layer, §3a step 0).** The
  one genuine dependency. Unifies the legacy `svg_forge` catalog-assembler and the
  `raster_forge`/file-forge stub into registries of mini-RITs + interchangeable
  composition strategies producing a composite RIT. Recipe/spec format (layer list
  + transforms + strategy + content-addressing) is the open piece. Paperdoll-
  driven; credentials is the degenerate validating consumer, not the driver.
  Deserves its own media-subsystem design note / issue.
- **Journal integration of composed media.** The single-RIT path exists
  (`MediaFragment(content=rit)` → service deref). Confirm a composite RIT rides
  the same path unchanged (it should — a composite is just a RIT), so neither
  credentials nor paperdolls invent a second journal channel.
