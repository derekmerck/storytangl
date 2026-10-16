# Salon Season: a standalone dating sim with a Terror coda

**Status:** design approved, 2026-10-15. All three checkpoints in §5 are
settled. Nothing is built yet. Grafting the world onto *Coronate the Regent* is
deliberately deferred (§8).

## 1. What this is

A small standalone world in two phases.

1. **The Season** (spring 1789, Paris). A dating sim on a short calendar:
   - Attend salons to build favor with three factions.
   - Collect gossip.
   - Dress to each host's taste.
   - Court one of three suitors at date spots around the city.
2. **The Coda** (1793–94). The revolution comes, and the player rises to sit on
   the Committee:
   - The people met during the Season come up on the docket.
   - The gossip collected becomes evidence, which can be true or forged.
   - Each case ends in a ruling: destroy your enemies, shelter your friends.
   - Every mercy toward the old order raises suspicion. Thermidor ends the coda
     either way: you survive it, or you go the way of Robespierre.

What the coda adds: **the Season's social capital is cashed in under inverted
rules.** Being esteemed by the Crown was an asset in April 1789. In 1793 it is
a liability. A rival snubbed at a salon becomes a defendant. A gossip token
becomes the evidence that condemns or clears someone.

### Lineage and IP

- **Season.** The mechanical lineage is *Ambition: A Minuet in Power* (Joy
  Manufacturing Co.): faction favor gates scheduled events, salons are where
  you grind for favor, and suitors are courted at rendezvous spots. The posture
  matches `credential_gate` → *Papers, Please*.
- **Coda.** No source. The original game ends around the Bastille.
- **No source prose, names, characters or plot are used.** Historical setting,
  public places and historical figures (who appear only in the background) are
  fair game. The ripped string dump stays out of the repository. Its proper use
  is as a compression corpus for detangl (§9).

### Where it sits in the catalog

| World | Pressure |
| --- | --- |
| `coronate_the_regent` | Stats trained against a fixed schedule |
| `credential_gate`, `hall_monitor` | Rulings on cases |
| `salon_season` (this) | Standing built against a schedule, then rulings where that standing is the evidence and the defendants are people you know |

## 2. Salvage from the old `minuet` folder

| Old artifact | Disposition |
| --- | --- |
| `factions.yaml`: 5 factions, 5-tier allegiance reward ladder | **Keep the shape** at 3 factions and 3 tiers |
| "Crown and revolution never align; the minors swing" | **Keep.** The coupling rule is the Season's core mechanic |
| `salon_activity.py`: salon = activity hub, prestige tier, arrival/departure, 2–3 slots, stay-late adds slots, stamina | **Keep** |
| `salons/arrival.yaml`: outfit approval, rested check, gift at the door | **Keep the shape.** Rewrite the prose |
| `parlour_game.py`: stat challenge followed by a **forced walk** to a predetermined leaf | **Keep** as outcome-first presentation |
| `gossip.yaml`: faction-templated "Is it X, or Y?" dilemmas; framing moves favor | **Keep the shape.** Write new dilemmas. In the coda, gossip *also* becomes evidence |
| `rendezvous.yaml`: suitor × place cross-product (outfit reaction × place reaction × outcome tier) | **Keep the shape** as reaction tables |
| `formal_wear.py`: fashion × prestige × modesty, novelty/condition decay | **Keep** fashion, prestige and novelty |
| `epilogue.yaml`: assembled fates (fled together, executed, acquitted, swore vengeance) | **Keep the shape** as the coda's epilogue assembler |
| `roles.yaml`: archetype × faction matrix for a generated cast | **Defer** (§8) |
| Jinja-dereferenced prose | **Drop.** Write ground-instance prose against a fixed cast |
| `afc.*` Python, `minuet*.yaml` dumps | **Drop.** The dumps are detangl corpus only |

## 3. Scope (v1)

### The Season

- **Calendar.** About three weeks, from late March to the Estates-General in
  May 1789. Each day has two periods:
  - *Afternoon:* rendezvous, shop, or the rumor mill.
  - *Evening:* salon.
- **Factions.** Crown and Revolution are the majors and are opposed. The
  Bourgeoisie is the minor and swings.
  - Each faction has three standing tiers: *disregarded*, *known*, *esteemed*.
  - Tiers gate salon prestige: intimate, festive, grand.
  - Esteem with the host grants **stay late**, one extra activity slot.
  - Favor with one major costs favor with the other.
- **Salons.** Generated from faction × prestige × occasion, each with a named
  host who is a recurring person (the coda needs them). Each one arrives as an
  invitation letter (§5.3).
  - *Arrival:* outfit judgment against the host faction's taste, a rest check
    against stamina, an optional gift.
  - *Hub:* 2 slots, 3 with stay late, drawn from four activities:
    - a parlour game (outcome-first)
    - a gossip dilemma (gains a gossip token)
    - a snoop (gains a gossip token)
    - a suitor beat, when eligible
  - *Departure.*
- **Gossip tokens.** Assets carrying a faction, a subject (a named person) and
  a tier. In the Season they are spent in conversation for favor, or sold.
  Tokens held at the end of the Season carry into the coda.
- **Wardrobe.** 4 garments. Each has a favored faction (gown → Crown, suit →
  Bourgeoisie, town wear → Revolution), a prestige tier, and novelty that drops
  with each wear and recovers over days. One modiste sells upgrades.
- **Suitors.** Three, one per faction, each with an arc of four beats:
  1. introduction at an intimate salon
  2. rendezvous
  3. a festive-salon complication
  4. a commitment
- **Rendezvous.** Three date spots, each with a reaction table: suitor × outfit
  → line plus favor delta, and suitor × place → line plus favor delta.
- **Mutual exclusion.** Committing to the Crown suitor closes the Revolution
  suitor's last beat, and the reverse holds too. The Bourgeoisie suitor is
  compatible with either.
- **Rivals.** One salon rival per major faction, made or soured by your
  choices. Rivals exist mostly to reappear in the coda.

### The Coda

- **Phase boundary: regime change.** A time skip to 1793. One authored
  transform is applied to the faction standings:
  - Revolution standing becomes *influence* (power on the Committee).
  - Crown standing becomes *taint* (a starting value for suspicion).
  - Bourgeoisie standing is halved.

  The transform is applied once, at an UPDATE boundary.
- **The docket.** Three Committee sessions, each with 3 accused drawn from the
  Season's people:
  - salon hosts you met
  - rivals
  - the suitors who were not chosen
  - at most one stranger per session

  Who appears is determined by Season state. A person you never met does not
  appear.
- **A case = a credentials case.**
  - The **dossier** has two sources (§5.2):
    - the prosecution's findings, which arrive with the case;
    - the gossip tokens you hold about the accused, which you may *present*.
  - The accused's papers are period-true credentials: the *carte de sûreté*
    (the ID) and the *certificat de civisme* (the permit). Their deeds and
    associations from the Season are the contraband.
  - **Rulings:**

    | Ruling | Credentials disposition |
    | --- | --- |
    | acquit | PASS |
    | exile | DENY |
    | condemn | ARREST |

  - **Disposition ≠ fate.** Exile can be a rescue, prison can shelter someone
    from the mob, and acquittal can leave someone exposed. The world decides
    each fate, not the evaluator.
- **Malfeasance.** One axis, from passive to active, pointing for or against
  the accused:

  | Move | Pole | Direction |
  | --- | --- | --- |
  | *Withhold* a token you hold | passive | for |
  | *Take a favor* from the accused's faction | passive | for |
  | *Bury* a prosecution finding | active | for |
  | *Forge* a finding | active | against |

  Active moves cost influence. Every move except withholding carries a
  getting-caught risk that feeds suspicion. This is the deferred credentials
  malfeasance layer, built as one axis (§5.2).
- **Suspicion.** Raised by taint, by acquitting the tainted, and by being
  caught at malfeasance. Lowered by condemning, and by denouncing (spending a
  gossip token in public).
- **Thermidor.** A final scheduled event:
  - suspicion above threshold → your own trial (the Robespierre ending)
  - otherwise → survive, with the fates of the people you protected or
    destroyed assembled into the epilogue

### Budget and exclusions

| Piece | Estimate |
| --- | --- |
| Season blocks | ~25–30 |
| Coda blocks | ~15 cases-and-sessions plus Thermidor and epilogue |
| Script | ~700–1,000 lines of YAML |
| Domain module | ~400–600 lines |

The domain module grows only where §4 says something is world-local.

**Out of scope for v1:** generated cast, Church and Military factions, rent and
upkeep, a Paris map plate, art, and non-CLI clients.

## 4. Engine pieces it forces

### Consumed as-is

| Need | Existing surface |
| --- | --- |
| Calendar, periods, scheduled set pieces (Estates-General, Thermidor) | `sandbox` `WorldTime` / `ScheduleEntry` / `ScheduledEvent`, used in a non-spatial frame |
| Faction-taste and outfit modifiers on salon checks | `SituationalEffect` via `get_situational_effects` (the Coronate pattern) |
| Parlour games | `StatChallenge` / `HasStatChallenge`; `kim_game` via `HasGame` for one of them |
| Rigging an outcome | `SituationalEffect.forced_outcome` and the `roll` argument on challenge resolution |
| Garments | `WardrobeManager`, `OutfitManager`, `build_wardrobe_dress_offer` |
| Gifts, purchases, spending gossip | `TransactionOffer` and its commitments |
| Rulings | the credentials evaluator, penalty matrix, per-rule-set scoring, recurring-bearer attribution (`hall_monitor`) |
| Meeting people | concept naming, anonymous before / known after |
| Tier labels | `progression.measures.Quality` |

### Forced: new or promoted

1. **Standing as a coupled measure.** Proposed in §5.1: store raw favor mass
   per faction, and read renown, alignment and standing from it. The weights
   are the coupling.
2. **Regime change.** Proposed in §5.1: more readouts over the same store. The
   phase boundary writes nothing.
3. **Dossier from collected evidence.** Proposed in §5.2. The world *authors*
   offers from story state instead of sampling them. The kernel gains seeded
   findings and a `present_evidence` move. Packet provenance does not change.
4. **The malfeasance layer.** Proposed in §5.2. The `case_mutations` overlay
   that `CREDENTIALS_LOOP_DESIGN.md` already sketched, shipped as one axis. **The
   coda is the consumer that layer has been waiting for.**
5. **Generic offers.** Proposed in §5.3: no promotion. An invitation is an open
   edge whose requirement carries the salon template, and provisioning
   materializes it on traversal. `ScenarioOffer` stays in credentials.
6. **Outcome-first presentation.** Resolve at entry, then make the walk
   conform. `forced_outcome` and `roll` cover resolution. The gap is choice
   availability keyed off a result stored on entry. Prove it world-locally
   first, then promote it if it stays small.
7. **Wearable novelty.** Revive the commented-out `Wearable.condition` field as
   a real presence feature, and add novelty alongside it.
8. **Reaction tables.** Suitor × stimulus → tiered line plus delta. This is the
   #340 situation × voice factorization on the #336 override chain, and a #339
   measurement datapoint.

Gossip dilemmas, mutual exclusion, suspicion and Thermidor need no engine
change. They are conditions, effects and one counter with a threshold.

## 5. Checkpoints before code

1. **Standing ownership, the coupling chokepoint, and whether regime change
   reuses it** (§4.1–4.2). **Approved 2026-10-15** as §5.1 revision 2.
2. **Dossier-from-holdings and the malfeasance overlay** (§4.3–4.4).
   **Approved 2026-10-15** as §5.2. The kernel parts move into
   `CREDENTIALS_LOOP_DESIGN.md` as its malfeasance phase.
3. **Generic offer promotion** (§4.5). **Approved 2026-10-15** as §5.3.

There are no hard external dependencies. #556 would make faction-sponsored
invitations nicer, but the standalone world can own its hubs.

### 5.1 Checkpoint 1: approved resolution (revision 2)

#### Owner: the player

Standing lives on the world's player object, a `Player` subclass composed with
progression mixins (the `Regent` pattern). Factions are authored Singletons
carrying taste, reward ladder, host roster and their **readout weights**. They
hold no run state. That would break `(class, label)` serialization and the
multi-lane contract (#346).

#### Store one thing, read it three ways

Three representations were on the table:

1. a dict keyed by faction Singleton, valued with a `Quality`
2. a raw currency per faction
3. a barycentric coordinate for three-way influence, plus a renown magnitude

These are one model read three ways.

**Stored: raw favor mass per faction** (option 2), held in the player's
existing `AssetWallet` (`story/concepts/asset/wallet.py`) through `HasAssets`.
`Faction` subclasses `CountableAsset`, so favor with the Crown is a fungible
asset, counted beside livres.

- Favor acts `gain` mass. Offending a faction `spend`s mass, clamped to what is
  held, because `spend` already refuses to go below zero.
- This is the only stored state. It persists as the wallet already does.
  `AssetTransactionManager` already validates transfers, for example a favor
  trade, and `HasAssets` already publishes the wallet into the namespace.

**Read: three computed readouts**, never stored.

| Readout | Definition | Used for |
| --- | --- | --- |
| **Renown** | `Σ favor`, projected to a `Quality` tier | The faction-independent ladder (the old `reputation_rewards`): "invited to all intimate salons", and so on |
| **Alignment** (option 3) | `favor / renown`, a barycentric point on the faction simplex | Presentation, such as a ternary plot. Narration: regions of the simplex carry the old allegiance names (*Monarchist*, *Third Estate*, *Radical*) |
| **Standing** (option 1) | `Quality(Σ_g w[f][g] · favor_g)`, with `w[f]` authored on faction *f* | The per-faction ladder: salon tiers, stay late. Exposed as `player.standing(faction) → Quality` |

**Coupling is the weights.** For example:

```yaml
crown:       {crown: 1.0, revolution: -0.5}
revolution:  {revolution: 1.0, crown: -0.5}
bourgeoisie: {bourgeoisie: 1.0}
```

Opposed majors cost each other, and the minor swings freely.

There is a geometric reading of this. Standing is renown times a linear kernel
on the barycentric point: `renown · (w[f] · alignment) = w[f] · favor`. So
barycentric-plus-renown and per-faction standing are exact rescalings of each
other, not two models to keep in sync.

**Why this shape.**

- **Nothing is derived twice.** Standing cannot drift from favor, because it is
  never stored.
- **No new write chokepoint.** Writers add or remove mass, and readouts are
  pure functions of it. PLANNING stays repeatable, delta order does not matter,
  and replay is trivial.
- **Reuse, not a new store.** The wallet already is the counted, nonnegative,
  type-defined mapping this needs. Its intended keying was by `AssetType`.
  Today `amounts` is keyed by asset label, which is the identity Singletons
  serialize by, so persistence needs nothing new. Moving the wallet to typed
  `AssetType` keys is a separate wallet cleanup. It is not required here.
- **No `Stat` tier machinery for the store.** Masses are counts, so they belong
  in a counted mapping. `Quality` appears only at readout. This follows
  STAT_CHALLENGE_DESIGN's split between tactical currencies and broad
  entitlements: the count is a currency, and standing is the entitlement read
  off it.

**Engine footprint.** Small, and mostly reuse.

- `Faction(CountableAsset)` carries taste, ladder and its readout weights.
- **Readouts over the wallet:**
  - Renown is `total_value` filtered to `Faction` types. `total_value` already
    computes Σ amount × type value.
  - Standing is the same sum with the faction's weight row in place of
    `value`.
- **One pathway.** Add a weighted-sum method to `AssetWallet`, and re-express
  `total_value` as that method called with each type's `value`. Then renown and
  standing share one implementation.
- Alignment is the ratio of the two.
- A threshold table supplies the `Quality` projection.

The likely home is story (the asset package), since `AssetType` is story-level.
About 30–60 lines plus tests, plus a check that the wallet still behaves as
intended (it is lightly exercised today). `HasStats` read paths are untouched.
Salon gating is ordinary availability conditions, for example
`player.standing(crown) >= known`. It is not a `StatChallenge` requirement.

This replaces revision 1's `composed_from` on `StatDef`, which would have
rerouted every stat reader for a value that is not really a stat.

**Costs.**

- Clamping at 0 means "offend the Crown" can only remove what you earned. That
  is acceptable: through the weights, it still lifts Revolution standing.
- The kernel is linear. Nonlinear couplings, such as the attitude-dependent
  sign flip in HARVEST batch 2, stay deferred.
- Suitor affection is pairwise person state and is out of this checkpoint's
  scope. Plain player stats are enough for a fixed cast in v1. Revisit with
  relationship edges when the cast is generated.

#### Regime change: more readouts, and the boundary writes nothing

The coda adds readouts over the same store, plus coda-local counters.
Coefficients are illustrative:

```yaml
influence: {revolution: 1.0, bourgeoisie: 0.5, crown: -0.5}  # minus influence_spent
taint:     {crown: 1.0}
```

Here `influence_spent` and the suspicion counters are coda-local stored
counts. Suspicion is `taint` plus acts caught minus acts cleared.

Renown is double-edged in 1793: total influence and total exposure both scale
with it. The Terror falls hardest on the prominent, and the readouts produce
that with no extra rule.

The phase boundary is only a time skip, so there is no "apply exactly once"
hazard.

### 5.2 Checkpoint 2: approved resolution

#### The Tribunal is a credentials shift

| Credentials | Tribunal |
| --- | --- |
| region (origin) | the accused's estate: noble, clergy, bourgeois, sans-culotte |
| purpose | residence in Paris |
| ID | *carte de sûreté* |
| permit | *certificat de civisme* |
| contraband | deeds and associations, each a typed indication, e.g. `royalist_correspondence`, `emigre_relative`, `hoarding` |
| `Restrictions` | the Law of Suspects. It grades each deed by estate, with CRIMINAL at the top (per se, no rescue) |
| PASS / DENY / ARREST | acquit / exile / condemn |
| per-rule-set `penalty_matrix` | the Terror regime: acquitting the guilty is costly, condemning the innocent is cheap |
| `no_evidence_penalty` | kept above zero. A condemnation must *look* grounded, which is exactly what makes forging rational |
| `bearer_id` and `prior_case_results` | the accused actor's uid, so someone re-accused in a later session carries their record (the `hall_monitor` recurring-bearer precedent) |

#### Dossier from holdings: authored offers, not new provenance

Packet provenance does **not** change. A packet is still built by
`build_valid` → `degrade` → derive from a `ScenarioOffer`. What changes is
*who writes the offer*.

- **World side: an offer builder.** It reads Season state and writes one
  `ScenarioOffer` per accused, in place of `generate_roster`'s sampler:
  - estate → `region`
  - Season deeds → `contraband`, with the `concealed` flag set for deeds that
    were never public
  - missing papers → `failure_modes`; for example, a noble denied a
    *certificat* is `MISSING_PERMIT`
  - actor uid → `bearer_id`

  This needs no kernel change. `ScenarioOffer` is already plain data, and
  `materialize` already replays it deterministically.
- **K1. Seeded findings.** `ScenarioOffer.prior_findings: dict[str, str]`
  seeds `finding_status` when its case becomes active. This is the
  prosecution's dossier. Seeded adverse findings count as surfaced evidence
  through the existing `_EVIDENCE_FINDINGS` check, so the justification logic
  is untouched. `advance_case` resets to the next offer's seed, not to `{}`.
- **K2. Presenting held evidence.** `ScenarioOffer.evidence_held:
  list[IndicationId]` lists the indications the player can prove. The world
  fills it from the gossip tokens whose subject is the accused. A new mediation
  move, `present_evidence(indication)`:
  - writes `finding_status[indication] = CONFIRMED` for a held indication the
    accused actually carries;
  - costs no time budget, since the evidence is already known.

  Withholding is simply not presenting. It is free and invisible, and it is the
  passive pole of the malfeasance axis. In v1, tokens are true by construction.
  Unwittingly false rumor is a possible later extension.
- **K4. Target for authored offers.** `materialize` asserts
  `target_disposition`. A small helper derives it, so the builder fills it
  rather than guessing. The assertion stays, as the author-side consistency
  check.

#### Malfeasance: the overlay already sketched, shipped as one axis

**K3** adopts the shape `CREDENTIALS_LOOP_DESIGN.md` recorded as deferred:

- **The overlay.** A `case_mutations` overlay on the game, the adversarial
  counterpart of `finding_status`:
  - It lives on game state, persists with it, and is reset by `advance_case`.
  - Derivation reads the packet *through* it. The materialized packet is never
    written.
- **The moves:**
  - `plant(indication)` adds a confirmed contraband finding to the record, for
    a deed the truth does not hold. This is *forge*: active, against.
  - `invalidate(finding_key)` removes an adverse finding from the record. This
    is *bury*: active, for.
  - `accept_favor` is the passive, low pole. A pass is bought. The favor is
    paid in Season faction assets through the existing transaction machinery
    (the "bribes pay in goods" thread).
  - All three are gated by a regime flag, `allow_malfeasance`, off by default.
    `credential_gate` and `hall_monitor` are unaffected.
- **Scoring: record versus truth.** This is the new semantic.
  - Uncaught, the case is scored **on the record**: expected disposition,
    penalty and justification all derive from packet ⊕ mutations. The regime
    sees only paperwork.
  - Caught, it is scored **on the truth**, plus a per-move malfeasance penalty.
  - The catch roll happens once, at decision commit. It uses a per-rule-set
    `malfeasance` config (catch probability and penalty per move) and the
    game's seeded RNG, so replay is deterministic.
  - `CredentialCaseResult` records the mutations, `caught`, and both
    derivations, so the world and the journal can tell the story either way.
- **World side, as ever: disposition ≠ consequence.**
  - Suspicion, verdict → fate, and Thermidor read `case_results` and world
    state.
  - The kernel scores compliance and offers tools. It never knows about the
    guillotine.

#### What this is not

- **Not a new packet source.** The world authoring offers covers that.
- **Not the generic offer** (checkpoint 3). `ScenarioOffer` is used here in
  its own domain.
- **Not B.3 declines.** The accused do not lie or refuse in v1. Declines can
  layer on later without touching this.

**Kernel footprint.**

- K1 and K2: two offer fields, one seeding line in `advance_case`, one
  mediation move.
- K3: the overlay, three moves, a scoring branch, and result fields.
- K4: one helper.

All four are additive, behind the regime flag where it matters. The design text
moves into `CREDENTIALS_LOOP_DESIGN.md` as its malfeasance phase, so it is not
duplicated here.

### 5.3 Checkpoint 3: approved resolution

**Do not promote `ScenarioOffer`.** The generic "promised encounter,
materialized on arrival" already exists twice:

- **`EntityTemplate`** (core). An authored prototype, materialized on demand
  with overrides: `materialize(**updates)`, or
  `materialize_one(selector, update)`.
- **Provisioning** (vm). A requirement may carry an inline `fallback_templ`.
  The provisioner offers a create from it when the edge's destination is
  unresolved (`vm/provision/provisioner.py`).

An open edge whose requirement carries a template materializes on traversal.
That is the affordance model's primitive. A promoted generic offer would be a
third version of it, which AGENTS.md lists as a stop sign.

**A salon invitation is an open edge.**

- **When the invitation arrives** (an UPDATE-boundary effect, such as the
  morning post), its parameters are sampled once: faction, prestige, occasion,
  host. The player gains an **invitation letter**, a discrete asset token whose
  locals hold those parameters.
  - The letter is diegetic: the old `salons.yaml` invitation text renders from
    it.
  - It is inventory-visible, and it persists with the player.
- **The evening hub** offers one choice per held letter. Each choice's
  successor requirement carries the salon template, with the letter's
  parameters applied as `fallback_templ`.
- **On traversal**, provisioning materializes the salon. Nothing is created
  for invitations that are declined or expire.
- Sampling happens at UPDATE, so PLANNING stays repeatable.
- When #556 lands, the letter becomes the concept that donates its choice to
  any receiving hub, which is #556's sponsor shape. No change to the letter is
  needed.

**`ScenarioOffer` stays credentials' domain record.** It is not a template of
an entity. It is the parameter record for a domain builder (`build_valid` →
`degrade` → verified derive). The coda's docket uses it in its own domain
(§5.2), so there was only ever one new consumer: the invitation. And the
invitation does not need it.

**Not foreclosed.** If a second domain builder appears, compare it with
`ScenarioOffer`. The natural convergence is a credentials-case template, with
the offer as its update payload. Revisit then, not now.

**Kernel footprint: none.** World side, it is an invitation-letter asset type,
a salon template, and the hub's per-letter choice builder.

## 6. Validation targets

**Season**

1. **Coupling seam.** One unit of Crown favor moves `standing(revolution)` by
   its weight, and `standing(bourgeoisie)` not at all.
   - Sabotage check: zero the weight and confirm the test fails.
   - Only `favor` is persisted. Renown, alignment and standing are absent from
     the unstructured form.
   - `renown · (w · alignment) == w · favor` holds on random favor vectors.
2. **Ladder.** Below tier, a salon renders as an unavailable choice with a
   reason. Crossing into *esteemed* adds exactly one activity slot.
3. **Outcome-first.** For a fixed seed, the parlour outcome is identical across
   every choice path. On a losing path, the winning choice is never offered.
4. **Outfit and novelty.** The same salon with different garments gives
   different modifiers. Novelty drops after a wear and recovers on schedule.
5. **Mutual exclusion.** Committing to either major suitor closes the other's
   final beat, with a reason.
6. **Invitations.**
   - A letter's parameters are sampled once, at UPDATE. Re-planning the
     evening hub yields identical choices.
   - The salon is materialized only on traversal. A declined or expired letter
     leaves no salon node.
   - A held letter survives a fresh-process round-trip.

**Coda**

7. **Carry-over.** The docket contains only people met in the Season. The
   *only* inputs from the Season are standings, holdings, met-flags and
   commitments (asserted by constructing the coda from a synthetic Season
   state).
8. **Regime-change seam.** Crossing the boundary writes nothing: `favor` is
   equal before and after the time skip. A coda act that adds Revolution favor
   raises `influence` by its weight.
9. **Dossier provenance.** Every adverse finding in a coda case traces to one
   of three sources:
   - an offer's `prior_findings`
   - `present_evidence` on an indication in `evidence_held`
   - a `plant` mutation

   The materialized packet is byte-identical before and after any mutation.
   `advance_case` clears `case_mutations`.
10. **Disposition ≠ fate.** A pinned case where an exile ruling yields a
   survival fate, and a condemn ruling (prison) shelters someone.
11. **Malfeasance.**
    - An uncaught forged condemnation of a clean accused scores as justified.
    - The same case with the catch roll forced scores on the truth, plus the
      malfeasance penalty, and the world raises suspicion.
    - Sabotage check: make the overlay write the packet instead, and confirm
      target 9 fails.
    - The catch roll is deterministic under replay.
    - With `allow_malfeasance` off, the `credential_gate` and `hall_monitor`
      goldens are unchanged.
12. **Thermidor.** Endings partition on the suspicion threshold, and both sides
    are reachable.

**Whole world**

13. Reachability across both phases: every ending is reachable, and no ending
    requires mutually exclusive commitments.
14. CLI witness committed. A mid-Season save and a mid-coda save each survive a
    JSON service round-trip in a fresh process. Replay is deterministic.
    - Restored favor amounts resolve to the live `Faction` instances after the
      factions are re-registered in the fresh process, and readouts match
      their pre-save values.
15. Compression datapoint: authored reaction-table units against the
    cross-product they cover (#339).

## 7. Phases

1. **Season spine.** Calendar, factions, standing coupling, one intimate salon
   with arrival and departure, wardrobe, invitation letters. Targets 1, 2, 4, 6.
2. **Salon activities and gossip.** Parlour game, dilemma, snoop, gossip
   assets. Target 3.
3. **Suitors.** Three arcs, rendezvous reaction tables, mutual exclusion, an
   ending stub at the Estates-General. Targets 5, 15. *At this point the
   Season is a complete small dating sim and could ship alone.*
4. **Coda.** Regime change, docket, dossier, rulings, malfeasance, suspicion,
   Thermidor, epilogue. Targets 7–12.
5. **Witness and docs.** Targets 13–14, README, catalog entry in
   `worlds/README.md`.

## 8. Later: grafting onto *Coronate the Regent*

Once the Season works on its own, grafting it onto Coronate becomes a clean
test of world extension. The mechanics are already proven, so only the
extension machinery is new:

- `WorldManifest` gains `extends:`.
- The loader composes base and extension.
- Extensions are additive only.
- The composed world gets its own identity, so base saves don't silently load
  into it.
- Insertion into Coronate's hand-wired week hubs needs #556 (concept-donated
  contributions at ordinary-scene receivers).

The Season's factions would reskin into Coronate's court, and the coda would
become an optional post-coronation phase. The generated cast (archetype ×
faction × gender, via `RoleGrant` and open role references, with gender swap as
a fabula-leak fuzzer) belongs here or in a larger standalone derived game, not
in v1.

## 9. The corpus

The *Ambition* string dump (~488 flattened scenes, with rendezvous as a
near-pure cross-product) is the ready-made rung-2 test for discovering a cast
in formulaic text. Keep it local. It is not content.
