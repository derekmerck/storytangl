# Credentials Loop Design

**Status:** v1 LANDED (candidate-roster shift, 2026-05-21); Phase A LANDED
(A.1 rules-derived dispositions, A.2 candidate factory, A.3 day-spec sampling +
lazy offer roster, 2026-05-22); Phase B.1 LANDED (core mediation moves,
2026-05-23); Phase B.2 LANDED (contraband mediation, 2026-06-04); penalty-matrix
scorer + soft time budget + per-rule-set scoring config (configurable
`penalty_matrix`, `no_evidence_penalty` toggle) LANDED 2026-06-05; B.2.1 CRIMINAL
contraband tier (per-se crime, no rescue, per-rule-set) LANDED 2026-06-05; Phase C
whitelist/blacklist override (data flags clamping `expected_disposition`; overt vs
shadow = the tax toggle) LANDED 2026-06-06; B.3 (declines axis) + the malfeasance
layer (bribe/plant/invalidate) designed below as overlays; Phase 7 packet
authority cutover LANDED 2026-07-20 (one owner-bound assembly manager per case);
Phase 8 structured defects LANDED 2026-07-21 (one mediated evaluator, then a
disposition fold)
**Scope:** the credentials / checkpoint interaction as a stacked picking-game
composition inside `tangl.mechanics.games`  
**Background sources:** `docs/src/notes/CREDENTIALS_INTERACTION.md`,
`scratch/mechanics/credentials/README.md`,
`scratch/mechanics/credentials/notes.md`, and the older scratch credentials
package  
**Prior art:** Lucas Pope's *Papers, Please* and similar checkpoint-inspection
games

---

## Why This Note Exists

The credentials mechanic has been one of the longest-running design threads in
the repository. It already has a substantial background note in
`docs/src/notes/CREDENTIALS_INTERACTION.md`, but it is important enough to
deserve a short, live-facing mechanics note too.

The main reason is that credentials is not just "another picking game." It is a
**stacked composite loop** built from several smaller patterns:

- local spot-the-difference checks on individual documents
- packet-level consistency checks across the whole presented case
- a final disposition choice with narrative consequences
- circumstance and prior memory that can skew any of the above

That is exactly why it made sense to defer it until simpler kernels were
proven.

---

## Papers, Please Decomposition

What made *Papers, Please* compelling was not only the fiction. It was the way
it layered a few simple interaction patterns:

- compare visible evidence against current rules
- inspect for discrepancies or confirmations
- manage time, suspicion, and partial information
- make a final bureaucratic disposition
- carry narrative and economic consequences outward into a larger loop

That combination gives the player the feeling of performing a procedural task
while actually navigating a tightly authored dramatic machine.

StoryTangl's credentials mechanic should preserve that layered structure rather
than flattening it into a single yes/no check.

---

## Core Structure

The credentials interaction should be thought of as three explicit layers.

### 1. Document Loop

Each credential has its own local inspection game:

- what should this document look like?
- what visible fields or seals are present?
- what details are missing, forged, inconsistent, or suspicious?

This is the most direct descendant of a picking or Kim's Game style loop:

- inspect a feature
- reveal either a distractor, confirmation, or discrepancy
- record the finding

### 2. Packet Loop

The full credential packet then has its own consistency game:

- do the documents agree with each other?
- do they match the declared purpose, origin, and identity?
- do they satisfy the current checkpoint rules?
- are there missing supporting documents for the declared situation?

This is not identical to any one document check. It is a second-order
comparison between the candidate's full presentation and the current policy.

### 3. Disposition Loop

After inspection, the player chooses a terminal disposition such as:

- allow / pass
- deny
- arrest
- defer, extort, request search, or other world-specific outcomes later on

This is where narrative consequences enter most directly. The disposition is not
just scoring. It can affect later plot state, reputation, rewards, risk, and
future encounter structure.

---

## Context Layer

Any of those three layers can be informed by circumstance or prior memory.

Examples:

- "I have seen this candidate before."
- the candidate is on a whitelist or blacklist
- the candidate offers a bribe
- the current checkpoint rules changed this morning
- the player is under pressure from quotas, supervisors, smugglers, or scarcity

This is a crucial design property. Credentials is not only a static discrepancy
spotter. It is an inspection loop whose available moves, findings, and correct
dispositions can be bent by world context.

That context should be modeled as explicit game state and policy input, not as
hidden exception logic.

---

## Domain Vocabulary Worth Preserving

The older scratch work and consolidated docs note already established strong
domain nouns. Those are still the right building blocks:

- **restriction map** or current checkpoint rules
- **candidate truth**
- **candidate presentation**
- **credential packet**
- **document finding**
- **packet finding**
- **disposition**
- **whitelist / blacklist**
- **bribe / threat / pressure**

These are more stable than any one old implementation scaffold.

---

## Why This Is A Composite Loop

Credentials sits at the overlap of multiple family notes:

- it is a **picking game** because the player inspects and reveals findings
- it is a **composite loop** because document checks, packet checks, and
  disposition are stacked
- it is often a **narrative pressure game** because circumstance and prior
  knowledge bias the available choices and outcomes

That makes it a good test case for whether the mechanics taxonomy is actually
compositional rather than merely descriptive.

---

## Recommended First Live Implementation

Even though the conceptual structure is layered, the first live implementation
should probably *not* be a literal nested `HasGame` inside `HasGame` inside
`HasGame`.

The simpler and safer v1 is:

- one outer `CredentialsGame`
- staged internal phases such as `inspect_document`, `inspect_packet`, and
  `decide`
- findings recorded at both local and packet scope
- context injected as explicit state that affects move generation and evaluation

In other words, the first implementation can treat the inner loops as
**virtual subgames** inside one outer game state machine.

That keeps the runtime surface manageable while still preserving the conceptual
stack.

---

## Later Directions

Once the simplified outer-game version is proven, richer versions can add:

- request missing credential
- request search
- verify identity
- challenge a claimed exemption
- accept or reject a bribe
- memory-driven special handling for recurring candidates
- packet generation driven by distributions, regions, and authored policy tables

At that stage we can revisit whether any inner layer deserves extraction into a
reusable generic kernel.

---

## Relationship To Existing Reference Games

The current live references already point in this direction:

- `KimGame` proves cue-driven inspection and reveal
- `CredentialsGame` proves a compact inspect-and-dispose loop
- the picking-game conventions in the handlers prove that findings can surface
  through move labels, notes, journal fragments, and namespace

What remains is the stacked form: local mismatch, packet mismatch, then
disposition under context.

---

## Implementation Guidance

If the credentials family is expanded next, the live design should aim for:

1. document findings and packet findings as separate recorded categories
2. explicit context inputs for prior memory, whitelist/blacklist, bribery, and
   changing rules
3. a disposition layer that routes narrative consequences outward
4. a first implementation that stages subloops inside one outer game
5. only later, if justified, true nested subgames or reusable picking kernels

That should preserve the best lessons from the old *Papers, Please*
deconstruction without forcing the first implementation to solve everything at
once.

---

## v1 Landed (2026-05-21): the candidate-roster shift

The first live expansion is implemented in `credentials_game.py` and demoed by
`worlds/credential_gate`. A single `CredentialsGame` hosts a **roster** of
`CredentialCase`s walked by one re-entrant `HasGame` block: each disposition keeps
the game `READY` and re-provisions moves for the next candidate, so there are no
nested game blocks and no per-candidate story edges. The game reports terminal
only once the final candidate is decided, at which point the existing
`game_won` / `game_lost` POSTREQS exits route to a shift summary.

What shipped:

- **`CredentialCase`** -- the single source of truth for per-candidate authored
  data (documents, hidden facts, packet facts, `correct_disposition`), with
  reserved seams for Phase A (`region`/`purpose`/`contraband`) and Phase C
  (`whitelist`/`blacklist`/`bribe_offer`).
- **`CredentialCaseResult`** -- an auditable record per disposition (chosen vs.
  expected, correct, findings).
- **`shift_complete` + `evaluate()`** own shift terminality; `advance_case()`
  resets only per-case working state; `pass_threshold` defaults to strict
  all-correct.
- **`expected_disposition(case)`** -- the single correctness chokepoint, today
  returning the authored answer (bent by whitelist/blacklist context).

Dispositions are authored per case, and the interaction is inspect -> packet ->
disposition only. Everything below layers onto this spine.

---

## Implementation Seams (how later phases stay overlays)

Five properties keep Phases A/B/C as extensions rather than entangled rewrites:

1. **`CredentialCase` is pure data.** Every phase adds *fields*; the loop never
   special-cases them.
2. **`expected_disposition(case)` is the single correctness chokepoint.** Nothing
   else decides right vs. wrong.
3. **Move dispatch is by `move.kind`** in the picking kernel. New interactions are
   new kinds, not new control flow.
4. **Shift state is additive** (`case_results` today; `reputation`/`finding_status`
   later), reset on setup, exported via `to_namespace`.
5. **Consequences route through namespace + authored POSTREQS edges** in YAML, not
   hardcoded branches.

### Packet authority cutover (2026-07-20)

`CredentialPacketManager` is the sole runtime credential authority.
`CredentialCase` retains only candidate and narrative/projection state plus its
required manager; it has no parallel region, purpose, id, document, or
possession fields. `derive_disposition` reads the concrete manager directly.

`ScenarioOffer` is the authored arrival contract. At setup/UPDATE materialization
creates one manager with the host owner and selected catalog, then applies failure
modes to its components and possessions. A small private sampler feasibility
check stays data-only; the materialized manager is asserted against the offer's
target disposition. Gate and Hall Monitor both use ordinary offers, with only
narrative overrides for their authored wording.

---

## The rule and failure-mode model

The mechanic runs on a few axes. Stating them precisely here so Phases A/B/C
implement the same model.

### The restriction axis (and rule deltas)

Each indication sits on one ordered axis, most to least restrictive:

```text
forbidden  ->  allowed with permit (req id)  ->  allowed with id  ->  allowed (anonymous)
```

`req_id` is a *property of the level*: the two id-bound levels (permit, id)
require checking the bearer id; the anonymous level does not. A day's authored
rule change is a **delta along this axis** for some indication ("work moves from
allowed-with-id to allowed-with-permit today"). Which failure modes are reachable
follows from where each indication currently sits (see "Rules are an authored
story lever", A.5).

### Which rule applies (candidate -> bin)

A candidate is mapped to a restriction bin by three factors:

- **origin** (region),
- **purpose** (the intent indication: travel / work / emigrate / ...),
- **possessions** (contraband indications: weapon / drugs / secrets / ...).

origin + purpose + each possession select the level(s) that candidate must
satisfy.

### Two error surfaces per permit

A permitted indication needs a permit *and* verification of the permit against
the bearer id -- so there are **two independent places to introduce an error**:
the permit document itself (missing / bad / forged) and the id linkage (the
permit's holder reference vs. the presented id). Generation and inspection both
treat these as distinct surfaces.

### Mitigatable infractions vs. crimes

The disposition split turns on whether an error is *fixable in the moment*:

| Error                            | Class       | Fix (mediation)           | Unfixed |
| -------------------------------- | ----------- | ------------------------- | ------- |
| Missing document                 | mitigatable | produce it                | deny    |
| Missing seal                     | mitigatable | return to the signer      | deny    |
| Openly declared contraband       | mitigatable | hand it over (relinquish) | deny    |
| Forged seal                      | crime       | --                        | arrest  |
| Fake id / fake papers (knowing)  | crime       | --                        | arrest  |
| Concealed contraband             | crime       | (a search reveals it)     | arrest  |

Mitigatable errors are the Phase B mediation moves: a successful fix clears the
infraction (-> allow); refusal or inability escalates (-> deny). Crimes are not
clearable; a search is a *detection* move (it exposes concealment), not a fix.

### Origin bends severity (Phase C)

Origin is not only a bin selector -- it modulates outcome severity *after* the
base disposition is derived:

- a **privileged** origin can have a crime overlooked (arrest -> deny / allow);
- an **out-of-favor** origin can have a minor infraction charged up
  (deny -> arrest).

This is the nuanced form of whitelist / blacklist: not a binary pass/arrest, but
a shift along the severity scale.

---

## Phase A: derived disposition and generated packets

The scratch package under `scratch/mechanics/credentials/` already designed this
end to end. The work is **port-and-reconcile**, not new invention. Its
`README.md` is the canonical encounter spec (rules-per-indication, candidate
truth vs. presentation, derived expected disposition, blacklist/whitelist, and
the haggling twist where a candidate may bribe for a *denial*).

### A.0 Why generate, not validate (the central lesson)

The scratch work first tried to **algorithmically validate** an author-produced
packet -- inspect the documents, compare against the rules, and *infer* the
correct disposition. That path is a trap: it forces the engine to re-derive
intent from artifacts, and every new failure type needs new validation logic.

The decisive pivot was to **build the packet to match the intended disposition**
instead. Generation is strictly easier than inference, it guarantees the only
discrepancies present are the intended ones, and it is what makes the
specification funnel (A.3) possible at all. Do not reintroduce a packet-validator
to compute dispositions; dispositions are an *input* to generation, derived for
scoring only via `expected_disposition`.

**A.1/Phase 8 landed (2026-05-22/2026-07-21).**
`tangl.mechanics.credentials` holds the vocabulary (`Region`, `Indication`,
`RestrictionLevel`, `CredentialStatus`, `CredentialDefect`) and lean packet types.
`derive_defects` reads the concrete owner-bound manager and mediated findings once;
`derive_disposition` folds its failure classes. `expected_disposition` derives unless an authored
`correct_disposition` override is set; `credential_gate` now derives all three
dispositions. Rules are stored as a flat `Restrictions` model (a rule list with
`level_for` + a `from_map` authoring constructor) rather than an enum-keyed dict,
because the VM hashes node state with `json.dumps` and enum dict-keys are not
JSON-serializable. Later sections record extensions and remaining proposals.

### A.1 Derivation vocabulary (port)

The conceptual core is a chain:

```text
Indication --(restriction map)--> RestrictionLevel --> Presentation --> Outcome
```

- `credentials-2/enums.py` is the cleanest source: `Indication`,
  `RestrictionLevel`, `RestrictionMap`, `RegionalRestrictionMaps` (with worked
  LOCAL / FOREIGN_EAST / FOREIGN_WEST example maps), and a `Presentation` enum
  whose members are grouped by `Outcome` via `presentations_for_outcome`.
- Top-level `enums.py` is the complementary richer version: the **Flag `Outcome`
  severity hierarchy** (CRIME > DENY > ACCEPT, with specific members such as
  `FORGED_CREDENTIAL`, `MISSING_PERMIT`, `POSSIBLE_*`) plus the full `Move` set
  and `Move.appropriate_for(outcome)`.
- `tests/test_outcomes.py` locks the presentation -> outcome mapping; port it as
  the spec for the canonical vocabulary (reconcile the two enum files into one).

### A.2 derive_disposition (refactored in Phase 8)

`expected_disposition(case)` derives against the shift's `restriction_map` by
folding structured defects: any crime arrests, any remaining mitigatable defect
denies, and no defects pass. Authored
`correct_disposition` stays an explicit override for exceptional authored cases.
(The two design subsections A.1 and A.2 were
implemented together as the "A.1 derivation spine" increment.)

### A.3 Candidate factory: one pipeline, three entry points (the A.2 increment, LANDED)

**Landed (2026-05-22)** in `credentials_factory.py`: `build_valid(region, purpose,
rules, *, contraband)` produces a valid packet (derives PASS); `degrade(case,
modes)` / `apply_failure` corrupt it per the `FailureMode` catalog;
`make_case(...)` is the Tier 2 entry; `applicable_modes(case, class)` and
`sample_failure_mode(case, class, rng)` expose the reachable modes for sampling.
The round-trip invariant is tested: every mode derives to its class disposition,
and composition takes the worst. Tier 3 sampling / day spec / lazy roster is A.4
below (the A.3 increment), still pending.

```text
disposition --sample--> failure mode(s) --construct--> packet (CredentialCase)
   (Tier 3)               (Tier 2)                       (Tier 1)
```

Each tier supplies data from that point down; it is one funnel, not three paths.
Tier 1 = explicit packet (v1 today). Tier 2 = declare a failure mode (or none)
and build it against the current rules; disposition is then derived. Tier 3 =
declare a disposition and sample an appropriate failure mode.

The construction primitive is **start correct, then degrade**:

```text
case = degrade(build_valid(intent, restriction_map), failure_modes)
```

`credentialed.py::generate_credentials()` is the worked blueprint: build a proper
packet from the rules, then apply crime / invalidation / mediation mutators
(`_forged_credential`, `_wrong_id_holder`, `_hidden_contraband`,
`_bad_credential`, `_missing_credential`, `_possible_*`), with `outcome.specify()`
sampling a specific failure within a category. Its doctrine -- *credentials are
never tested against restrictions; they are created to pass or violate them* --
is what makes generation tractable. Failure modes compose (multiple corruptions
on one packet); a correct candidate is `degrade(..., [])`.

**Failure-mode catalog.** `degrade` is driven by an explicit `FailureMode` set,
and the same catalog is what A.3's sampler draws from. Each mode carries:

- a **class** -- *mitigatable* (-> deny if unfixed) vs *crime* (-> arrest), matching
  `CredentialStatus.is_crime` and the concealed-contraband case from A.1;
- the **mutation** it applies (which token/id status it sets, or contraband it
  conceals); and
- an **applicability** predicate: which modes a given indication can even exhibit
  at its current restriction level (you can only "miss a permit" where a permit is
  required; only "forge a seal" where a credential exists; only conceal contraband
  where contraband is present). This is the A.5 "rules shape the failure space"
  point made concrete -- the sampler asks the catalog which modes are reachable
  for an (indication, level) before choosing one.

A.1's structured truth is exactly the target this builds and mutates, and the
**round-trip invariant** test pins it: `derive(degrade(build_valid(intent,
rules), mode)) == expected_for(mode)`.

### A.4 Day spec, lazy offers, and editable roster (the A.3 increment, LANDED)

**Landed (2026-05-22)** in `credentials_roster.py` (compact form): `ShiftSpec`
(rules + origin distribution + disposition-class distribution + encounters +
purpose pool + pinned + seed); `generate_roster` samples origin + target then
picks a *feasible, verified* failure mode (so the linchpin holds by
construction); `ScenarioOffer` is the unmaterialized promise; `materialize(offer,
rules)` builds the packet deterministically; `CredentialsGame.offers` +
`active_case` materialize each candidate **on arrival** (cached in
`materialized`, a reset field). `render_narrative` (in the factory) projects the
inspect-loop strings from the structured truth so generated cases are playable.
Pinned whitelisted encounters (the "John Smith" case) work. Multi-day shifts and
live roster editing are deliberately left as repeated generation / ordinary list
edits -- no extra machinery.

This is the larger increment. It is authored at the **shift/day** level and
materializes candidates lazily.

**Day/shift spec (authored).** A `ShiftSpec` carries everything a day needs:

- the day's **rules** (a `Restrictions`; rules change between days -- "foreign-west
  is now allied: anonymous transit, no id; foreign-east is now work-permit-with-id
  only");
- an **origin distribution** set by the gate/location ("at the western gate: 50%
  foreign-west, 30% local, 20% foreign-east");
- a **disposition-class distribution** ("40% valid->allow, 30% mitigatable->deny,
  30% illegal->arrest");
- **encounters per day** and **number of days** ("5/day for 3 days");
- **pinned offers** -- scripted encounters that must appear ("John Smith arrives
  with an invalid political clearance, but he's whitelisted -> allow"). A pinned
  offer can fix any subset (origin, packet specifics, context override) and the
  rest is filled by sampling.

**Two-stage sampling.** For each non-pinned slot: (1) sample an origin from the
origin distribution and a disposition class from the class distribution; (2) ask
the failure-mode catalog (A.3) for the modes of that class **reachable** for this
origin under the day's rules, and sample one (or a composition). PASS = no mode;
deny = a mitigatable mode {bad/missing seal, missing doc, declared-unpermitted
contraband...}; arrest = a crime mode {forgery, fake id, concealment...}.

**Roster = offers, materialized on arrival.** The roster holds **scenario offers**
(origin + target class + chosen failure mode + any pins/overrides), *not* concrete
packets. The actual `CredentialCase` (the credential tokens) is built on demand --
via `build_valid` + `degrade` -- only when that candidate arrives in the story.
Until then an offer is just a promise of a scenario, so the roster can be
**pre-empted, edited, reordered, or inserted into** (drop in John Smith, retune a
day) before materialization. This unifies the three tiers: every roster entry is
an offer, fully-specified (Tier 1), failure-specified (Tier 2), or
disposition-specified (Tier 3), and materialization resolves it down the funnel.

The lazy hook fits the existing loop cleanly: materialize the next offer into the
active case at `advance_case` / setup time. The runtime loop still never learns
whether a case was authored or sampled. Port the distribution shape from
`credential_script_models.py` (`expected_disposition_ratio` per region,
`num_encounters`) and `credentials-2/cred_check_scene.py` (`sample_outcomes()`,
pinned `extras`).

**Tests** (the linchpin): every materialized offer derives to the disposition
class it was generated for; the origin/class distributions are hit under a seed;
pinned offers appear (and honor context overrides like John Smith's whitelist);
editing/pre-empting the roster before arrival changes who shows up.

### A.5 Rules are an authored story lever

The `restriction_map` is not engine configuration -- it is a **story knob the
author sets per day** ("no asylum from the east today"; "no weapons permits from
the west"). Changing the rules changes *which failure modes can even exist*: a
forbidden indication cannot be cleared by any permit, an allowed one cannot
produce a missing-permit failure, and so on. So the available failure-mode space
is **derived from the current rules**, and generation (A.3) samples only from
that derived space.

`outcomes_graph.py` exists for exactly this: it visualizes the
`Indication -> RestrictionLevel -> Presentation -> Outcome` graph under a given
rule set, so an author can *see* which dispositions and failure modes are
reachable today before committing a day's rules. It is an authoring/validation
aid for rule sets, not a runtime component.

**The rules are also a narrative surface.** In Pope's *Papers, Please*, daily
rule changes carry inscrutable political messages: who is currently allied or
belligerent, how much the regime trusts its own people, admissibility wielded as
a hammer against political foes. Different checkpoints can carry different
state-vs-local-enforcement variation, governance subtly diverging from rule. The
mechanic gives the author a way to *say something* through bureaucratic minutiae
alone -- the rules are the politics. This is the dramatic upside of the
data-driven design: changing a `Restrictions` instance between shifts is
authorially equivalent to a regime memo.

### A.6 Packet-as-tokens (when structure is needed)

When narrative-string findings are no longer enough, the structured packet model
is `credentials-2/credential.py`: `CredentialType` as a YAML-loaded Singleton
wrapped by `WrappedSingleton`, with `credential_status` as an overlay flag and
computed `seal` (`seal.py::Seal.type_for`), issue, and expiry. It deliberately
mirrors the **Wearable / Outfit-manager** pattern -- the credential packet is to
the candidate what an outfit is to an actor. `default_credential_types.yaml` is
the catalog (ticket, asylum, work permit, etc.). This becomes
`CredentialCase.packet`; the degrade mutators set `credential_status` overlays
rather than rebuilding tokens.

---

## Phase B: mediation moves

Phase B adds follow-up moves that can clear or confirm findings before a
disposition. The work splits into two increments because contraband mediation
has enough independent design surface to warrant its own pass.

### B.1 — Core mediation (v1 increment, LANDED 2026-05-23)

Adds three move kinds and a per-case ``finding_status: dict[str, str]``
(values: ``"cleared"`` / ``"verified"`` / ``"confirmed"``; reset by
``advance_case``).

- **``request_document``** — per-target fanout, one Action per *presented*
  permit. Committing it discloses the permit's standing: a mitigatable flaw is
  ``cleared`` (the candidate produces a corrected copy), a sound permit is
  ``verified`` (re-presented unchanged), a forgery is ``confirmed`` (cannot be
  reissued). Maps to ``accepts.kind="pieces"`` in the rendering contract
  (`bundles/credentials/EXTENSIONS.md`).
- **``verify_id``** — single Action, available whenever an id is presented.
  Answers only the holder question: ``confirmed`` for WRONG_HOLDER (a crime),
  ``verified`` otherwise. It never repairs a stale id, so an expired/mis-dated
  id stays a deny (id-reissue is B.2).
- **``request_search``** — single Action; reveals concealed contraband if any.

**Disclosure discipline on the move menu.** Mediation availability is gated on
*visible* state only -- which documents the candidate presented -- never on
hidden validity. A useful mediation is indistinguishable from a dud until it is
committed; the *outcome* discloses, not the move's presence. (A move absent
because a document is *visibly* not present, e.g. no id at all, reveals nothing
the client cannot already see.) Likewise, dispositions are never pre-gated by
the correct answer -- all of allow/deny/arrest stay available and correctness is
hidden until the shift resolves. ``available=false`` with a reason is reserved
for genuinely-blocked actions (e.g. deciding before any inspection), not for
leaking backend logic. Only a ``cleared`` mitigatable finding upgrades
``derive_disposition``; ``verified`` / ``confirmed`` are audit-only.

``derive_defects`` consults ``finding_status``: a cleared mitigatable doc defect
is absent from the derived list; ``derive_disposition`` then folds the remainder.
Verified and confirmed findings remain audit-only.

Enabled by a small base refactor: ``PickingGameHandler.resolve_round``
dispatches through a kind-keyed registry (with inspect/decide as defaults), so
the new kinds register cleanly without overriding ``resolve_round`` (and Phase C
moves follow the same pattern).

**v1 assumptions (deferred, see B.2):**
- *Missing*-document requests are out of v1: ``request_document`` only targets
  *presented-but-invalid* docs. Missing-doc requests need a different surface
  (pick from "required-but-absent" indications).
- All candidates comply truthfully with requests; no "declines mediation" path.

### B.2 — Contraband mediation (deferred follow-up)

Beyond ``request_search`` (which reveals concealment), full contraband mediation
needs a family of moves whose interactions span packet validity, possession
state, and candidate willingness. The matrix below is the spec to build against
when B.2 lands.

**Packet validity taxonomy** (for the contraband's permit specifically):

- **valid** — covers the contraband; everything in order.
- **incomplete** — required document is missing entirely (can be produced).
- **invalid** — present but mitigatably wrong (missing seal, expired, etc.);
  can't be repaired at the desk.
- **illegal** — forged / wrong-holder (the document itself is criminal).

**Mediation moves B.2 introduces** (in addition to ``request_search`` from B.1):

- ``request_complete`` — ask the candidate to produce the missing piece (for
  incomplete packets). Subsumes the "missing-doc request surface" deferred from
  B.1.
- ``request_disclosure`` — the polite "anything to declare?" ask. Subject to
  the candidate's compliance (the "oops, I forgot I had this in my pocket"
  path).
- ``request_relinquish`` — ask the candidate to yield declared contraband.

**Declared contraband** — what the player can do about visible possession:

| Packet | Outcomes available |
|---|---|
| valid | allow |
| incomplete | ``request_complete``, ``request_relinquish``, or deny |
| invalid | ``request_relinquish`` or deny |
| illegal | arrest |

**Concealed contraband** — outcomes depend on how (or whether) it surfaces:

| Packet | If disclosed / discovered |
|---|---|
| valid | ``request_disclosure`` (the "oops" path) → becomes declared+valid → allow |
| incomplete | ``request_complete``, ``request_relinquish``, or deny |
| invalid | confusing — probably arrest |
| illegal | arrest regardless of discovery |

Unsearched concealment is invisible to inspection; the player decides on
visible state alone.

**Multiple contraband types.** A candidate may carry several restricted items;
each is assessed against its own permit category and the worst outcome
dominates.

**Cross-product examples** (one indication's permit interacting with a
different contraband):

| Candidate | Outcome |
|---|---|
| medical permit (drugs) + open weapon (no weapon permit) | yield, ``request_complete``, or deny |
| medical permit + concealed weapon | arrest |
| medical permit + weapon that requires no permit | accept |
| medical permit + concealed weapon that requires no permit | **[open]** |

**Valid paperwork, nothing declared, but rules allow possible unpermitted
contraband.** The gatekeeper can always request a search; the candidate may
refuse (→ deny) or comply (search runs → arrest if anything is found, allow if
clean).

**Severity is environmental.** The arrest/deny boundary in several rows bends
with **environment, discretion, and bribery** (a Phase C cross-cut). B.2
computes a base disposition; Phase C composes the override on top.

**Resolved model (2026-06-04): declaration is the requirement.**

The matrix collapses once you see that **contraband is, by definition, what must
be declared.** If concealment doesn't matter for an item, it simply isn't
contraband — there is no fourth "ignored" category. So contraband has these
levels (from the restriction map for that indication):

- **declaration-only** (anonymous / id level) — allowed *if declared*.
- **permit-required** (with-permit level) — declared *and* a valid permit.
- **forbidden** — denied regardless (but *relinquishable* — surrender it and the
  candidate walks).
- **criminal** (`RestrictionLevel.CRIMINAL`, LANDED B.2.1 2026-06-05) — a **per-se
  crime**: mere possession arrests, and **neither declaring nor surrendering it
  rescues** (you cannot relinquish your way out of trafficking — heroin, slaves, a
  case of counterfeit). `_contraband_class` returns `"criminal"` and
  `_assess_contraband` short-circuits to ARREST before any rescue path. This is the
  arrestible-severity *forbidden* sits below: which goods are criminal is **per
  rule set** — a permissive regime simply maps the same good down to a lower level,
  and a privileged-origin **whitelist** exemption (Phase C overlay above
  `derive_disposition`) is the only thing that bends it back. It is also the target
  severity the deferred *planting* malfeasance move aims for: a discovered criminal
  good is what launders a shadow-blacklist arrest into "arrest with reason."

`RestrictionLevel` is shared by purpose and contraband rules, so two corners are
pinned for "weird but legal" authored configs: a **CRIMINAL purpose** (e.g.
`{WORK: CRIMINAL}`) derives ARREST (the stated purpose is itself a crime; the
purpose branch special-cases it like FORBIDDEN→DENY), and a **WITH_ID contraband**
good is routed through `_assess_requirement` (class `"credentialed"`, = needs a
permit and/or id) rather than treated as merely declarable, so its bearer-id check
is not bypassed. `build_valid` keeps raising only for criminal/forbidden
*contraband* (a caller asking to add a disallowed good); a criminal/forbidden
*purpose* is left to derive its inherent ARREST/DENY, which the roster relies on.

And **concealment is itself the violation** — concealing *any* contraband is a
problem, independent of whether it would have been permitted. The disclosure /
search distinction decides severity:

- **`request_disclosure` rescues.** Asking "anything to declare?" → (compliant)
  candidate declares → assess as *declared* (allow if permitted or
  declaration-only). This is the "oops, I forgot" path.
- **`request_search` forecloses.** The concealment stands; the player learns of
  it but forfeits the benign explanation.

| Contraband state | declaration-only | permit-required | forbidden |
|---|---|---|---|
| declared, valid permit | allow | allow | (n/a) |
| declared, no/invalid permit | allow | **deny** (produce/relinquish) | — |
| declared, forbidden | — | — | **deny** (relinquish) |
| concealed → disclosed | allow | allow if permit valid, else deny | deny (honesty mitigates arrest) |
| concealed → searched / undiscovered | **deny** | **deny** if permit valid (Q1), else **arrest** (smuggling) | **arrest** (smuggling) |

`request_relinquish` clears *declared* contraband (the candidate yields it →
allow). The god's-eye `expected_disposition` accounts for concealed contraband
(a perfect inspector would find it), so allowing an unsearched smuggler is wrong;
`request_disclosure` is the only move that *rescues* concealed-but-permitted goods
to allow.

**Generator note.** The sampler will **not** randomly produce a candidate that
conceals something it didn't need to declare-and-permit; that edge (concealing
declaration-only goods) is an **authored** teaching beat — flex it once, get
chided for the wrong call, see it again in a different context — not a random
spawn.

**B.2 scope (compliance assumed):** the new move kinds ``request_disclosure`` /
``request_relinquish`` (search forecloses: a disclosure *after* a search has
confirmed concealment is too late to rescue), plus the graduated contraband
assessment above and per-indication worst-case composition. **Deferred:**
``request_complete`` (the missing-doc surface — ``request_relinquish`` already
clears declared problematic contraband, so it was not needed for B.2); and **to
B.3**, the declines-mediation axis (the candidate who lies when asked or refuses
to yield), where disclosure can fail. Phase C severity overlay (origin bends
arrest↔deny) layers on top of all of it.

---

## Phase C: context and haggling

**Whitelist / blacklist — LANDED 2026-06-06 (was always data, not a subsystem).**
The override is `whitelist`/`blacklist` flags on the case feeding
`expected_disposition`: whitelist clamps the expected call **down** to PASS
(the sponsored carrier waved through even with per-se-criminal goods), blacklist
clamps it **up** to ARREST (wanted by name; DENY if `allow_arrest` is off). It is
authored data propagated by the roster (`ScenarioOffer.whitelist/blacklist` →
`materialize`), with `_packet_finding` flavor; an origin-scoped whitelist is just
"set the flag for those origins" at authoring — no engine set needed. This is the
parsimonious shape; nothing to build, only compositions to cover.

**Overt vs shadow blacklist is the `no_evidence_penalty` toggle, not new code.**
A blacklisted *clean* candidate derives ARREST via the override but has no surfaced
or self-evident grounds, so:
- *overt* (tax off, `no_evidence_penalty == 0`) — the name is authorization; the
  arrest is free.
- *shadow* (tax on, `> 0`) — the bare name-arrest reads as `unjustified`, which is
  exactly the pressure to manufacture cover (plant a CRIMINAL good and "discover"
  it → arrest *with reason*). The planting itself is the deferred malfeasance layer.

**Deferred — fold into the malfeasance layer, do NOT build piecemeal.** Bribe /
favoritism (`bribe_offer` exists only as a narrative data seam today) is the
*passive, low* pole of the one malfeasance axis (turning a blind eye), and
origin-bends-severity (a privileged origin overlooks *some* crimes — a graduated
bend rather than a hard PASS clamp) is the same family. Building `accept_bribe` or
a partial severity-bend now would fragment a layer that wants to ship as one thing
(blind-eye/bribe at the bottom, doctoring/false-testimony at the top, inventory +
catch-strike pricing throughout). The `ScreeningRound` narrative-override idea from
the dropped `screening.py` (`on_invalid_seal`, `on_allow`, …) is still worth
reviving as per-finding journal flavor when that lands.

---

## Phase B.3: declines, bluffing, and ambiguity

B.1/B.2 assume **compliance** — the candidate truthfully declares, produces, and
yields when asked. B.3 adds the **declines axis** and, with it, genuine
*ambiguity*:

- A candidate may **lie** when asked to declare, **refuse** a search, or **refuse
  to produce** a document.
- **Bluffing:** a smuggler with no permit (where a permit is even possible) tries
  to talk their way in and *declines the search*. The player can deny (safe), or
  arrest (right *if* guilty), or press.
- **Crucially, you also need innocents who decline** — someone who refuses a
  search on principle, or refuses to produce a permit they feel they shouldn't
  need. Declining is a *signal correlated with* guilt, not proof of it.

This breaks the single-answer assumption (see below): a declined search has no
one correct disposition. Deny is always *safe*; arresting a decliner is right
only if they were actually guilty, and a **fail if they were innocent**.

**Authored beat — the abandoned forgery.** A candidate departs and leaves behind
an unnecessary illegal id/permit. The player can offer to return it — or inspect
it, find it forged, *offer to return it* as a lure, and arrest the holder when
they come back for it. A scripted multi-step encounter (departure → left item →
inspect → set trap → return → arrest), which is **continuity-thread** content
(recurring candidate + delayed consequence), not core derive.

---

## Engine review: expressiveness gaps & refinements (2026-06-04)

The matrix captures the **document-validity logic** completely and correctly — it
is, if anything, more rigorous than Papers Please's per-person scripting. What it
does not yet model is the **pressure and ambiguity** that turn a correct
rule-checker into a *game*. Two genuine engine-level additions (the rest is
content/already-planned):

### 1. Attention / time budget — the missing tension (LANDED 2026-06-05)

Mediation was **free**, so the dominant strategy was "run every probe on
everyone" — which collapsed the very judgment the disclosure discipline was
protecting (you can't read the answer off the menu, but you *can* brute-force
it). Papers Please's core tension is **scarcity**: you can't scrutinize everyone,
so you triage on suspicion.

**Shipped model — a soft per-shift time budget.** `CredentialsGame.time_budget`
(None disables time pressure, the default). Every probe and decision costs time
(`_MOVE_TIME_COST` / `_DECISION_TIME_COST`): a glance at a document or a
date/seal check is cheap (1), verify-id and request-reissue cost 2, a **search**
is expensive (3); passing/denying is quick (1) but an **arrest costs more** (3 —
escort/paperwork, which also reinforces the matrix's "don't reach for arrest
idly"). Time accrues per shift (`time_spent`). Time over the budget converts to
penalty at `overtime_penalty_rate` and is folded into `total_penalty`, so going
over the budget pushes you toward the failure threshold.

**Soft, not a wall.** Actions are never blocked — you *can* go slow, but it costs
you toward the LOSE line. The pressure is economic: investigate thoroughly and
pay in time, or move fast and risk wrong calls. This is what makes the
disclosure discipline *matter* (probing has a price now) and the
concealed-contraband god's-eye rule *play* correctly (you can't afford to search
everyone, so you deny the suspicious and sometimes miss).

Costs are fixed defaults; the per-shift `time_budget` (and
`overtime_penalty_rate`) are the tuning knobs. *Deferred:* the thoroughness
slider (quick-vs-thorough search) and the reference-doc progression (checks get
cheaper as you build your rulebook). A hard-clock / throughput variant (the
shift *ends* when time runs out, leaving the queue unprocessed) is a possible
later mode; the soft overtime model was chosen for v1 because it bolts directly
onto the penalty accumulation with no early-termination machinery.

### 2. Graduated penalty scoring with a failure threshold (LANDED 2026-06-05)

Keep the **single** `expected_disposition` (there is always one correct call).
Replace the binary correct/incorrect score with a **penalty matrix** over the
ordered severity axis allow → deny → arrest, accumulated to a failure threshold
(Papers Please's citation/strike model):

```text
should allow   = { allow: 0,  deny: 2,  arrest: 5 }
should deny    = { allow: 2,  deny: 0,  arrest: 5 }
should arrest  = { allow: 5,  deny: 2,  arrest: 0 }
```

One step off costs 2; two steps off (allow ↔ arrest) costs 5; correct costs 0.
The shift is lost when accumulated penalty crosses a threshold.

This makes **deny the low-variance hedge**: for a suspicious decliner, denying
caps the downside at 2 whether they turn out innocent (should-allow) or guilty
(should-deny) — which is exactly the bluffing tension, and it falls out of the
matrix without any acceptable-set machinery. (The earlier "two-error /
acceptable-set" sketch is superseded by this.)

**+1 for right-but-unjustified — a toggle (`no_evidence_penalty`, LANDED).** When
> 0, a *correct* deny/arrest that the player never backed with surfaced evidence
costs that much: guessing right is fine but taxed, so gathering evidence (which
costs budget, §1) is rewarded without being mandatory. It is **off by default**
because it is regime-specific — a rule-of-law gate turns it on; an arrest-by-decree
regime (§3) must leave it off, since arresting without evidence is the *norm*
there. A rejection is **justified** (`_rejection_is_justified`) if it is backed by
either *surfaced* or *self-evident* evidence, and the tax errs toward justified so
it never punishes a fair call:

- *Surfaced* (`_has_surfaced_evidence`) — a revealed document/packet finding, an
  adverse `finding_status` (`confirmed`/`cleared`/`yielded`, but **not** a clean
  `search: cleared`, which turned nothing up), or a logged declaration of
  contraband actually present.
- *Self-evident* (`_has_visible_grounds`) — facts visible without investigation: a
  credential the purpose plainly requires but the packet lacks, or openly
  (non-concealed) contraband that is forbidden or plainly missing its permit. A
  concealed item is not self-evident; a declared declaration-only item is allowed,
  so neither counts.

The tax keys off `correct` (not `penalty == 0`), so a custom matrix that tolerates
a non-expected call at zero cost is never mistaken for a correct one, and it never
fires on an allow (the point of an allow is that there is *no* adverse evidence).
Justification will also grow **behavioral** evidence once B.3 lands ("the smuggler
tried to bribe his way out of a search" → grounds for arrest); `_EVIDENCE_FINDINGS`
is the seam for that.

`derive_disposition` is unchanged; this was a refactor of the **decision scorer**
(penalty lookup + accumulation + the evidence check) and the shift terminal
condition (penalty-threshold instead of correct-count). `CredentialCaseResult`
records the per-case `penalty` and an `unjustified` flag.

### 3. Per-rule-set scoring + malfeasance/doctoring (LANDED scoring 2026-06-05; malfeasance deferred)

Scoring is **per rule set**, not a global constant. The penalty matrix is a
per-game field (`penalty_matrix`, string-keyed by disposition value so it stays
JSON-safe), defaulting to the standard rule-of-law matrix above. A world overrides
it to score a different regime. The motivating example — **"arrest everyone, any
non-arrest is a failure"** — is just a matrix where a non-arrest is a hard failure
rather than a mild hedge:

```text
should arrest = { allow: 5, deny: 5, arrest: 0 }   # decree: only arrest is clean
```

There are **two independent ways to express such a regime**, and they compose:

- **Decree via matrix** — set `expected_disposition` (or the matrix) so ARREST is
  the only zero-penalty call even on *clean* packets. You arrest the innocent; the
  regime, not the packet, defines correct. Leave `no_evidence_penalty` at 0.
- **Manufactured grounds via generation** — author the shift with a skewed
  `disposition_distribution` (e.g. `{ARREST: 1.0}`); `generate_roster`/`make_offer`
  degrade every packet (FORGED / WRONG_HOLDER / CONCEALED, etc.) until it *derives*
  to ARREST. The arrest is then "justified" by a real (planted) violation. This is
  the existing factory machinery — "build legal, then degrade by target
  disposition" — pointed at a uniform target.

**Malfeasance: doctoring evidence (deferred — opens its own design space).** The
B.1/B.2 mediations are *clearing* and honest (request_document, relinquish,
disclosure). Their counterpart is the player **doctoring evidence** — lose a piece,
smear a date to invalid, strip or forge a seal — and that is a *malfeasance axis*,
not merely a regime event. Two observations fix its shape:

- It spans a **severity spectrum**. *Turning a blind eye* (don't investigate;
  accept a bribe to pass someone) is the low, passive end — this is the Phase C
  bribery/favoritism layer. *Actively doctoring the packet into false testimony*
  (manufacturing or destroying a finding) is the high, active end. Both can point
  **in favor of or against** the candidate. So Phase C bribery is the low-level
  instance of the same spine, not a separate mechanic.
- It is driven by the **no-evidence penalty**. Because `no_evidence_penalty` is a
  scalar strike-cost, fabricating a justification is "just another step to keep
  your strikes down." The balance question is therefore explicit and tunable:
  **is having (or manufacturing) evidence worth more than the expected penalty for
  getting caught at malfeasance?** A regime that prizes correct-seeming paperwork
  makes doctoring rational; one that catches-and-punishes hard makes honest
  investigation (paying budget, §1) the cheaper path.

The transforms already exist as `FailureMode`s (`MISSING_PERMIT` = lose a piece,
`EXPIRED_ID`/`BAD_DATE` = invalidate a date); what is deferred is the **live move**
that applies one mid-case and re-derives, *plus* the catch/strike model that prices
it (getting-caught probability, the malfeasance penalty, reputation). Model the
mutation as the adversarial counterpart of `finding_status` (a `case_mutations`
overlay so `advance_case` resets cleanly and the authored packet is untouched),
gated behind a regime flag. Defer the whole malfeasance layer — it pulls in
bribery, detection odds, and reputation at once — but build it as one axis with
blind-eye/bribe at the bottom and false-testimony doctoring at the top.

### Generation: presentation vs. truth (confirmed)

Always **build legal, then degrade by the target disposition**, with a single
expected disposition per candidate. Two presentation moves on top of the truth:

- A **legal** candidate (should-allow) may get a **degraded initial
  presentation** — looks suspicious but is actually fine (the innocent who looks
  guilty; the indignant decliner).
- An **illegal** candidate (should-deny/arrest) is degraded (made actually
  illegal) and then **illegally upgraded back to a legal-looking presentation**
  (the forger — fake seal / id makes the surface read as valid).

The gap between *presentation* (what they show) and *truth* (the expected
disposition) is what inspection and mediation close. The factory's
`build_valid → degrade` already models the truth axis; this adds a
presentation-degrade layer on top.

### Smaller / done / deferred

- **Forged document is always a crime** *(done, B.2)* — presenting a fake id/permit
  arrests on its own, regardless of whether it was required.
- **Behavioral demeanor** *(defer; content-heavy)* — nervousness/pleading/bluffing
  as a readable signal beyond the documents, and a justification source (bribe
  attempt → grounds for arrest). The psychological dimension; its own layer.

### What to keep unchanged

The matrix core, the single `expected_disposition`, most-severe-wins composition,
the disclosure discipline, and `finding_status` as the mediation surface are all
sound — the additions read from them, they don't replace them.

---

## Phase D: media (deferred)

The media layer is specced in `credential_forge/credforge.py`,
`credential_forge/credforge_configs.yaml`, and `credentials-2/journal_models.py`
(forge for ticket / id-card / permit images, seal images, holder portraits, and
`JournalCredential` media items). Keep these as the eventual design, but defer
until the interaction is proven, and use **SVG only** per the repository's
PNG/JPG LFS rules.

---

## Generality: one engine, many skins

The credentials engine is **theme-neutral**. A world supplies only *data* -- the
restriction map (rules), the permit/credential catalog, the indication
vocabulary, and the candidate extras -- while the runtime (roster of extras +
procedurally generated packets + inspect/decide + derived disposition) is
identical across themes. This is the same reuse the other `mechanics.games`
kernels already follow (Bag-RPS in `colony_loop`, etc.), and it is a concrete
*second use case*, which is what justifies generalizing the vocabulary now.

Build Phase A accordingly: **no border/travel nouns baked into the kernel.**
`Indication`, `RestrictionLevel`, and the permit catalog are per-world data; only
the abstract chain (Indication -> RestrictionLevel -> Presentation -> Outcome)
and the generator live in the engine.

### Worked composite: Steam-Automata Chop Shop

A notes-rich world concept (an underground robot fencing / modification ring)
uses the credential mechanic for robot legality, but is deliberately broader
than a credentials reskin. Its archived data lives in a *sibling checkout*, not
this repo:
`/Users/derek/dev/storytangl/scratch/old/worlds/chopshop/resources/`
(`automata_credential_types.yaml`, `automata_parts_list.yaml`,
`automata_upgrades.yaml`, `scene_notes.yaml`).

- `automata_credential_types.yaml` is `default_credential_types.yaml` reskinned:
  anonymous "activation stamps" (`valid_period: 0`, no id) and id-bound
  "inspection / waiver tags" (`valid_period: 100`), over indications
  work / skilled / luxury (purpose) and passing / weapons / thinking
  (contraband), with origins CoD / CMG / black-market mapping onto `Region`.
- A unit's **components and upgrades determine its true indications**: a milspec
  chassis grants combat (needs a weapon waiver), a simulacrum chassis grants
  `passing` (needs a passing waiver), and illegal mods like `thinking` or
  `cloaking` are contraband (deny / arrest). Same Indication -> ... -> Outcome
  derivation, with candidate truth *computed from config* rather than authored
  directly.

The catalogs repeatedly use three-value axes -- local / allied / hostile
origins, ordinary / specialized / luxury purposes, and harmless / restricted /
illegal capabilities. That symmetry makes authored content easy to reason about;
it is not a runtime cardinality. A world may define two origins, five severity
tiers, or four dispositions without changing the mechanic.

More importantly, one assembled automaton is the semantic source for several
mechanical projections:

- its installed parts and upgrades derive credential indications and therefore
  its compliance requirements;
- those same parts and upgrades donate capability tags and situational effects
  to stat challenges against the environment or another automaton;
- installation, removal, repair, legalization, purchase, and sale become
  contextual choices backed by transactions;
- component condition, appearance, provenance, and permits contribute presence,
  story-info, and journal projections;
- challenge and training results can change stats or qualify later upgrades.

The permits are evidence attached to the unit, not a duplicate statement of its
construction. Compliance compares the indications derived from the current
assembly with the presented evidence and current rules. Changing a component can
therefore change legality, challenge behavior, visible description, and future
growth without synchronizing several independent models.

The old `Badge` vocabulary should likewise be read as an authoring precursor,
not as a runtime type to restore. In the converged design, a manually installed
upgrade is component-owned state, an automatic upgrade is derived from an
assembly condition, and both expose their effects through facets adopted by the
relevant credential, challenge, interaction, or projection handler.

### Direction: assess -> remediate (legalize) loop

Chop shop also inverts the gatekeeper framing. The disposition is not terminal:
it **feeds an outer shop loop** (buy / repair / legalize). The player can
*remediate* a unit to change its legality -- part it out, or forge / procure the
right stamps -- which is the degrade / generate machinery applied from the player
side (inspect -> assess -> remediate -> re-assess). That is a composite loop
(shell = shop economy, spike = legality assessment), noted as a future direction
(not v1 scope) and a natural wing of the unified showcase world.

### Worked third skin: Hall Monitor (evolving daily rules)

Another reskin, exercising a dimension Chop Shop doesn't really test: **rules
that vary day-by-day with explicit exceptions**. Border rules and chop-shop
permits are mostly static catalogs of who-needs-what; the Hall Monitor's daily
rules compose several orthogonal exception axes on top of the indication
catalog:

The checkpoint side of this catalog comparison is preserved as reference data
in `worlds/credential_gate/credential_types.reference.yaml`. It is not a live
loader contract; it records which semantics belong to the mechanic and which
nouns, seals, labels, and consequences belong to the skin.

The comparison also exposes current convergence debt: the fixed `Indication`
enum still contains checkpoint nouns such as `travel`, `weapon`, and `secrets`
even though indication identifiers belong to the world catalog. A future
catalogue contract should preserve the semantic categories (purpose versus
controlled item) and restriction operations while allowing authored indication
ids. Do not generalize by adding hall-monitor nouns to the engine enum.

- **attribute thresholds** -- "no one with a grade lower than a B is allowed to
  go to the bathroom"
- **calendar / event exceptions** -- "anyone can go to the gym for the pep
  rally in the afternoon without a note because it's a Friday"
- **documented exemptions** -- "students using inhalers should have
  documentation of need on file with the nurses office"

Each candidate (student) has attributes (grade, schedule, prior referrals) and
a purpose (bathroom / nurse / gym / class). The day's rules combine the
restriction map with these exception axes; the same `derive_disposition` shape
applies, with the rule lookup parameterized over more axes than the border
case. Locker searches and principal referrals reskin ``request_search`` and
ARREST respectively.

Mechanically, this is the strongest validation of the rules-as-authored-story-lever
framing (A.5): when the rules are mid-week school schedules with calendar
carve-outs and per-student exemptions, the per-day rule churn isn't a corner
case -- it's the gameplay. The same framework supports authoritarian-dystopia
fiction at any scale (checkpoint, chop shop, hallway, badge desk, comp tier,
exam proctor, customs office); the engine is fundamentally a **bureaucratic
gatekeeping kernel**.

---

## Beyond the phased roadmap: cross-shift continuity and recurring candidates

A procedural candidate today is generated for one shift and disappears at
terminal. A *real* checkpoint story wants candidates to return: the
procedurally-sampled traveler you wrongly admitted on day 1 walks back through
your line on day 4 and recognizes you; the hand-crafted recurring character
appears at multiple checkpoints; the unjustly-denied applicant comes back with
new paperwork. This needs **cross-shift continuity** the engine doesn't have
today.

The seams already exist; persistence is the missing piece:

- **Identity persistence.** A `CredentialCaseResult` already captures one
  decided candidate. Continuity needs a stable *candidate id* (and the option
  to persist a materialized `CredentialCase` snapshot keyed to that id).
- **Recurrence as an authored offer.** A recurring candidate is a normal
  `ScenarioOffer` whose payload carries prior `CredentialCaseResult`s alongside
  the current packet and any narrative overrides.
- **Prior-encounter context on the case.** A `prior_encounters:
  list[CredentialCaseResult]` field (on `CredentialCase` or a "candidate
  dossier" wrapper). `derive_disposition` and `expected_disposition` read it
  for recognition-driven severity bending; `get_journal_fragments` narrates
  "you've seen this one before."

**Promotion paths** (procedural → recurring):

- *Wrongly admitted.* A procedural candidate dispositioned ALLOW that should
  have been DENY/ARREST is promoted into a future shift's authored offers as a
  returning narrative thread -- the smuggler whose forged permit you missed
  comes back to blackmail you (the engine equivalent of Pope's recurring
  political consequence).
- *Unjustly denied.* A procedural candidate denied who *should* have been
  allowed returns with a grievance, new paperwork, or as a sympathetic NPC in
  another scene.
- *Hand-crafted recurring.* Authored candidates pinned across multiple shifts;
  their `prior_encounters` accumulate naturally as they're processed.

**Cross-cuts with the existing phases:**

- This is where **Phase C's "context bends severity"** gets its sharpest
  narrative edge: the context is *the player's own past mistakes catching up*.
  Whitelist-by-political-favor becomes blackmail-by-another-name when the
  candidate carries a `prior_encounters` record of your error.
- **`ShiftSpec`** (A.3) gains a `recurrences: list[CandidateDossier]` field
  (or a hook predicate) that pins prior candidates back in when conditions
  match (region, days-since, prior-disposition).
- The promotion **bridges procedural and authored** without breaking the
  funnel: a recurring candidate is just a Tier 1 offer enriched with prior
  context; the rest of the engine never learns whether it was sampled or
  authored.

This is design intent only; no implementation in scope. Worth capturing now
because it's a cross-shift persistence step the engine doesn't currently
support, and the seams (`ScenarioOffer`, `CredentialCase`,
`CredentialCaseResult`) all need to admit the continuity story when this lands.

---

## Scratch disposition: keep / adapt / drop

- **Keep as canonical narrative:** `README.md` (the encounter spec) and
  `notes.md` (the discrepancy / mediation taxonomy). These are the design of
  record for the mechanic, not just background.
- **Keep / port:** `credentials-2/enums.py` (derivation chain), top-level
  `enums.py` (Flag severity + `Move` set), `credentials-2/credential.py` +
  `seal.py` + `default_credential_types.yaml` (token packet model),
  `credentialed.py::generate_credentials` (degrade-from-correct algorithm),
  `credential_script_models.py` + `credentials-2/cred_check_scene.py` (roster
  distribution + pinned extras), `tests/test_outcomes.py` +
  `tests/test_credential_types.py` (specs).
- **Keep as deferred:** `credential_forge/*`, `credentials-2/journal_models.py`
  (media).
- **Keep as an authoring aid:** `outcomes_graph.py` -- visualizes the reachable
  failure-mode / disposition space under a given rule set (see A.5), for vetting
  a day's authored rules. Not a runtime component.
- **Drop (superseded by v38 Block/HasGame):** `screening.py` (old Challenge/Scene
  scaffolding -- but salvage the narrative-override hook idea),
  `papers_please_example.py`, and the empty stubs `credential_check.py`,
  `candidate.py`, `credentials.py`, `credentials-2/cred_check_*.py`,
  `id_card.py`, `enums_1.py`, `id_mint.py`, `utils.py`.
