# Repertoire Loop Design

```{storytangl-topic}
:topics: games
:facets: design
:relation: documents
:related: assembly, transaction, credentials, progression, widget, media
```

**Status:** DESIGN — nothing landed. Proposes one new kernel
(`CallResponseGame`), one shell pattern (repertoire acquisition), and the narrow
interface between them.
**Scope:** a *follow-the-leader* interaction type in `tangl.mechanics.games`,
the token-acquisition shell it plugs into, and the world veneer that gives both
their texture
**Prior art:** *Monkey Island* insult swordfighting; Simon-says; catechism and
countersign challenges; "one red paperclip" trade-up arbitrage; in-package,
`PickingGame` (keyed answers) and `SiegeRpsGame` (initiative alternation)
**Governing context:** `COMPOSITE_GAME_LOOPS_DESIGN.md` (shell + spikes),
`CREDENTIALS_LOOP_DESIGN.md` (stacked composition, world-tunable texture),
`MECHANICS_FAMILIES.md` (resolution grammars, pressure systems)

---

## Why This Note Exists

Insult swordfighting looks like a bespoke minigame. It is not. Pulled apart, it
is three independent things that the repository already has strong opinions
about, plus one small kernel it genuinely lacks.

The mistake worth avoiding is building "repartee" as a unit. That produces a
mechanic that can only ever be repartee. The cut below produces a kernel that
also covers Simon-says, work-song call-and-response, catechism, interrogation,
password/countersign challenges, spell-counter duels — and the credentials
check, which is already a keyed prompt-to-correct-response exchange.

---

## The Cut

Four separable concerns, three of them layers and one of them an orthogonal
axis:

```text
L3  world veneer        catalog content, text, tone, stakes      (authoring)
L2  acquisition shell   how repertoire is earned and traded      (mechanics)
L1  call-response       how one exchange resolves                (kernel)
────────────────────────────────────────────────────────────────
P   presentation        CLI floor -> richer media                (orthogonal)
```

L1 and L2 are **orthogonal and must be modeled separately**. A call-response
contest is perfectly playable against a fixed repertoire with no economy at all.
An acquisition economy is perfectly playable with any spike, not just this one.
They meet through a narrow, named interface (below), and only a *world* smushes
them together — exactly as credentials nests picking checks, packet consistency,
and disposition choice from several levels into one coherent encounter.

Presentation is not a layer in this stack. It is an axis every layer is
projected onto, and the CLI floor is where correctness is decided. Richer media
is additive.

---

## L1 · The call-response kernel (follow-the-leader)

### Shape

One participant issues a **prompt**. The other must play the **response** keyed
to that prompt, drawn from what they currently have available. Initiative may
alternate. The contest ends on a score threshold or exhaustion.

This is a *resolution grammar* in the `MECHANICS_FAMILIES.md` sense: small,
legible, and interesting because of the pressure the surrounding system supplies,
not because the grammar itself is deep.

### It is a recombination of two live kernels

Both halves already exist in the package, in different games.

**The keyed-answer table comes from `PickingGame`.** Its structured
`PickingMove(kind, target)` and `hidden_facts: dict[str, str]` keyed by target
are already the prompt-to-answer shape. What it lacks is an exchange: it is
configured `scoring_strategy="single_round"` with `opponent_strategy=None` —
inspect, reveal, commit. A validation loop.

**The alternation comes from `SiegeRpsGame`**, which `GAME_MECHANICS_DESIGN.md`
already names as the family's *asymmetric challenge-response* archetype. It
carries `player_has_initiative` as ordinary game state, sets it in `on_setup`,
flips it in `resolve_round`, records `initiative_before`/`initiative_after` in
round notes, and switches presentation on it — `get_move_label` returns "Attack
with" or "Answer with" depending on who leads. That is exactly the lead/response
structure this kernel needs, and it establishes the convention: **initiative
lives on the `Game` subclass, not on `RoundRecord`.**

`CallResponseGame` is therefore siege's initiative model over picking's keyed
table, with the response set supplied from outside. It belongs beside both in
the kernel list, not inside either.

### The key/text split — the load-bearing decision

The matching relation must be keyed on an **abstract response key**, never on
prompt text:

```text
PromptCard   { prompt_id, response_key, text }
ResponseCard { response_key, text }
```

A response is correct when its `response_key` matches the prompt's. Text is
catalog content hanging off both.

This one decision is what makes the Sword Master twist expressible: the player
learned responses from pirates, and the twist is that a new opponent issues
*unfamiliar prompt text* that resolves to *already-known response keys*. If the
match were keyed on text, that twist would require a parallel table. It also
means a world can retexture every line without touching the kernel — the same
property credentials has.

**Consequence:** this makes #336 (named, scope-overridable text expressions) a
hard dependency for L3, not a nicety. Today move text comes from
`get_move_label()` returning `f"Play {move_value}"` — a label function, not an
addressable text resource.

---

## L2 · The acquisition shell (red-paperclip arbitrage)

### Shape

Tokens are earned, held, and **traded up**. The distinguishing property is that
acquisition is not a victory reward: you gain a phrase badge when you *lose*,
because losing is how you were shown the correct response. You then spend that
badge elsewhere to obtain a different one.

`COMPOSITE_GAME_LOOPS_DESIGN.md` already describes this as *shell + spikes* and
names this instance in "Collectible / Training Shells": an outer loop of
discovery, collection, sorting, and roster construction; a focused contest that
tests the current build; outcomes that feed back into what can be collected next.
Its own gap list asks for exactly this — "at the shell level, some notion of
collection/training or expeditionary progression when the outer loop is not
purely economic."

### Repertoire is an assembly, and it works today

Known responses are a `SlottedContainer` over catalog components, the same
instrument behind outfits, credential packets, and vehicle loadouts.

One caveat that turns out not to bind: `SlottedContainer.slots` is a `ClassVar`
and `can_assign` rejects undeclared slot names, so the slot *schema* cannot grow
at runtime. But a repertoire does not want many slots. It wants **one** —
`known_responses`, large `max_count`, `selection_criteria={"is_instance":
ResponseCard}` — and mastering a technique is assigning another component into
it. No engine change.

A carry limit (bring only N into a duel) is either a second container with a
small `max_count` or the existing `BudgetTracker`/`can_afford` capacity
instrument. The stored-pool-versus-in-play split is already precedented by
`WardrobeManager` (`WARDROBE_SLOT = "stored"`) and `VehicleLoadout`.

Known asymmetry, noted so nobody builds on it: `component_facets` unions
declared slots with instance assignment keys, so undeclared slots are visible to
the read path while the write path rejects them. Use the one-slot model.

### Trade-up is a transaction

`tangl.mechanics.transaction` already has Spec / Offer / Commitment / Accept /
Receipt with `AssetHolder` and `CountableHolder` protocols, and
`TRANSACTION_OFFER_DESIGN.md` enumerates **Held Token** and **Catalog
Provision** as source modes. Arbitrage is: held token (the badge you won by
losing) → offer → commitment → receipt (a new badge minted from a catalog).

This step needs an author, not an engine.

---

## The interface between L1 and L2

Keep it narrow and named. Two directions, both idiomatic as `Protocol`s (the
package already leans on `TransactionHandler`, `CountableHolder`,
`StoryInfoProjector`):

**In — what may I play?** The kernel does not know about repertoires. It asks a
move source for the currently playable responses. A fixed-list source satisfies
it for a kernel-only test; a repertoire projection satisfies it in a world.

**Out — what did this contest yield?** The kernel does not know about
acquisition. It emits a structured record of the exchange and lets a sink decide
what that is worth.

The critical detail: **the yield is keyed to exposure, not to outcome.** Because
the point of losing is that you were shown the answer, the record must carry
*which prompts and responses were witnessed this contest*, not merely
win/lose/draw. An outcome-keyed interface cannot express red-paperclip
acquisition at all. This is the one place where getting the interface wrong
forces a rewrite.

Both directions are named in `COMPOSITE_GAME_LOOPS_DESIGN.md`'s shell-support
list — "snapshotting or staking tokens into sub-contests" and "applying
structured reward payloads on return."

---

## L3 · World veneer

Repartee is one skin: a catalog of insults and comebacks, a tone, a set of
opponents, and stakes. Like credentials, the entire texture is world-tunable —
catalogs, scoring config, which opponents teach what, whether losing costs
anything beyond time.

Other skins over the identical L1+L2 stack:

- Simon-says / memory drill (prompt is a sequence; no economy)
- catechism or interrogation (prompt is a question; stakes are social)
- countersign challenge (prompt is a password half; failure is exposure)
- spell-counter duel (response keys are elements)

The rule from credentials holds: mechanics stay world-agnostic, and world
adoption is bounded by authority.

---

## P · Presentation axis

Credentials is the model to copy here: demonstrably complete in the CLI, and
*intended* to carry a richer media representation, without the CLI ever being a
degraded fallback.

For this loop the CLI floor is genuinely sufficient — a prompt line, a numbered
list of playable responses, a score line. That is a complete, honest game. Every
richer projection is additive under the four parity rules (CLI Floor, Decision
Legibility, Time Parity, Input Parity).

What a richer port would add, and its current state:

| Surface | State |
|---|---|
| `AttributedFragment(who, how, media)` for the exchange lines | shipped |
| `PieceFragment` for held/playable cards | shipped engine-side; `PieceFragmentView.vue` renders as a list |
| `zone` grouping for pool vs in-play | shipped; `ZoneFragmentView.vue` present |
| `PieceFragment.position` + `ZoneLayoutHints` geometry | specified §7.1/7.2, **not consumed** by the Vue views |
| `StagingHints.media_timing` for looping sprites | shipped in the engine, **never read** by `MediaFragmentView.vue` |
| Portrait/background generation | forges exist (comfy, stable, svg, tts, dicebear, composition) |
| Bundled art | none — zero raster assets in `worlds/` |

Whether the richer representation works yet is an open empirical question, and
that is fine. It is deliberately not on the critical path: L1+L2 must be
complete and playable at the CLI floor before any of it is attempted.

---

## Engine seams this will hit

Only one, and it is small.

**Move provisioning has no context.** `get_provisioned_moves(game)` and
`get_available_moves(game)` take only the game object. Under this model the
playable responses come from an assembly that lives on the actor, not on the
game. Either mirror the repertoire onto the `Game` at setup, or widen the hook
to accept `ctx` — there is precedent, since `provision_presentation(game, *,
ctx)` already has it. Widening is preferred: this is the second consumer that
justifies it.

Initiative is **not** a seam. `SiegeRpsGame` already establishes the convention
(state on the `Game` subclass, transitions in `resolve_round`, transitions
recorded via `build_round_notes`, presentation via `get_move_label`). Follow it
rather than adding a role field to `RoundRecord`.

Nothing here requires a new phase, a new fragment type, or a new graph
primitive.

---

## Build order

1. **`CallResponseGame` kernel**, world-agnostic, against a fixed move source.
   No repertoire, no economy, no repartee vocabulary anywhere in it. Playable at
   the CLI floor.
2. **Repertoire as a one-slot assembly** plus the exposure-keyed yield
   interface. Kernel and shell still separately testable.
3. **Acquisition shell**: award-on-exposure as an authored POSTREQS exit effect;
   trade-up as a `TransactionOffer` against a held token. This is where the four
   shell supports from `COMPOSITE_GAME_LOOPS_DESIGN.md` get built.
4. **Repartee world**: catalog, text, tone, opponents. Pure authoring if #336
   has landed.
5. **Richer presentation**, only then, and only as an additive projection.

---

## Open questions

1. **Does the yield record belong to the game or the ledger?** Exposure is
   arguably a journal fact ("you heard this line") rather than game state. If it
   is journal-derived, acquisition could read from the journal rather than from
   a bespoke record — cheaper, and closer to how achievements already work.
2. **Is initiative a kernel concern or a scoring-config concern?** Strict
   alternation, winner-leads, and always-opponent-leads are all reasonable, and
   they may belong in the world-tunable config rather than the kernel.
3. **How does a partial match score?** Credentials generalized this into a
   penalty matrix with per-rule-set config. A near-miss response is a natural
   fit; whether to reuse that scorer or keep this binary is undecided.
4. **Sequence prompts.** Simon-says prompts are ordered sequences, not single
   keys. Whether that is the same kernel with a list-valued key or a sibling is
   an open question — worth deciding before the kernel is written, not after.

---

## Non-goals

- A general dialogue or conversation system. This is a contest kernel that
  happens to read as dialogue.
- Multi-cursor / two-human play. That is #346, and it is a runtime expansion.
- Hidden information. `visibility` does not exist on fragments today, and this
  loop does not need it.
- Solving presentation. The CLI floor is the deliverable.
