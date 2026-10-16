# Salon Season

**Status:** design brief, revised 2026-10-16 after review on PR #568. Nothing is
built.

- All three engine checkpoints are approved (Appendix A).
- Four contract defects were found in review and are fixed here: offer target
  disposition, committed influence, faction-only readouts, and what a caught
  forgery reveals.
- Grafting this world onto *Coronate the Regent* is deferred.

> **The Season teaches you to make people useful. The Terror asks what you're
> willing to do to them. Thermidor reveals what they remember about you.**

## 1. The idea

**A dating sim whose favor meters are reread by a revolution.**

| Act | Setting | What you are doing |
| --- | --- | --- |
| **The Season** | Paris, spring 1789 | Cultivating people: dressing, flirting, gossiping. Favor is the accounting, not the point. You are also choosing who will carry you into power, and how much influence you will have once you get there |
| **The Terror** | 1793–94, in short episodes | Your proxy sits on a Revolutionary committee. People you knew in 1789 come before it. You *assemble* their cases from what you and others can produce, to get the outcome you want |
| **Thermidor** | July 1794 | The record is read a third time, and the case is yours. This time you are not its only author |

The record never changes. Only the institution reading it changes.

What drives the design is mechanical as much as narrative:

1. a player learns to optimize a social system;
2. a different institution then reads the same history;
3. the consequences land on people the player actually knows.

### Three layers, never collapsed

| Layer | Example | Who controls it |
| --- | --- | --- |
| **Historical truth** | She attended the prince's salon and said something in 1789 | Fixed once it happens |
| **Institutional interpretation** | That attendance now demonstrates royalist sympathy | The regime's readout weights, which change |
| **Admitted evidence** | A rival's testimony, or a surviving letter, places that fact before the committee | Whoever witnessed it, wrote it down, or kept a copy |

**The institution is not omniscient just because the engine is.** Evidence
reaches a case only through someone who holds it. Who witnessed a
conversation, who wrote it down, who kept the document, and who can produce,
suppress, challenge or falsify it are story questions. They are also the
player's affordances.

Characters *carry* their evidentiary contributions, the same way other
StoryTangl concepts carry their own affordances. There is no encyclopedic
committee script.

The sharpest consequence: **a successful intervention can become evidence
against you.** Suppose you save a former lover by showing intimate knowledge of
his private correspondence. Thermidor will ask how you knew.

### Lineage and IP

- The mechanical lineage is *Ambition: A Minuet in Power* (Joy Manufacturing
  Co.): faction favor gates events, you grind at salons, you court at
  rendezvous.
- Its *shapes* carry over: the vanished patron, the salon rival, the gossip
  broker, the debts, a trial.
- **No source prose, names, characters or plot are used.**
- History supplies the background: places, figures, the Law of Suspects, the
  *certificat de civisme*.

## 2. The Season: making people useful

### What you are really doing

- **Cultivating relationships** and making socially consequential choices.
  That is the primary activity. Favor, tiers and outfits keep the books.
- **Choosing a proxy.** The suitor you bind yourself to (marriage, alliance,
  patronage) is your route to power in 1793.
  - The proxy need not come from your preferred faction.
- **Learning what each person will refuse to do.** In the Terror that matters
  more than affection.
- **Building influence:** how much weight you can push through your proxy. It
  is read off Season favor (Appendix A.1).
- **Building exposure.** Everything that raised you in 1789 can be read against
  you in 1793: Crown esteem, things you said in front of witnesses, debts, and
  the papers you are living on.

### The proxy is a relationship, not a vote

A proxy is someone through whom you try to exercise power. Each has
convictions, and high affection does not make them compliant:

- The revolutionary may love you and still refuse to condemn without evidence.
- The prince may protect an enemy.
- The bourgeois heir may defend a profiteer whose supply contracts feed a
  neighborhood.

Low influence is not just a worse roll. It means your proxy acts on convictions
you had chances to understand in the Season.

### The cast

A small, interconnected cast. **Each character appears in the others'
dossiers,** not just in their own final scene.

**Madeleine, the modiste.**

- *Season:* witty, ambitious, generous with credit. She is the first to suspect
  your papers are false.
- *Terror:* accused of dressing aristocrats, or supplying prohibited clients.
  The best proof of her innocence is an invoice that also exposes your
  identity.
- She is **the first full case.** It brings outfit, debt, trust, documents,
  assembly and self-exposure into one story.

**Lucien, the revolutionary suitor.**

- *Season:* an earnest young lawyer who believes rational law will make society
  just.
- *Terror:* by 1793 he has real authority, and he still believes in due
  process. You courted him partly for his influence. His principled refusal to
  alter a dossier is what makes him hard to love.
- An affection-maxed Lucien is not infinitely compliant.

**Hélène, the rival.**

- *Season:* petty, snobbish, capable of cruel public humiliation.
- *Terror:* her dossier reveals someone who spent money protecting servants and
  relatives. She is still disagreeable at her hearing.
- Saving her is generosity toward someone who has not apologized. It is not a
  reveal that she was secretly wonderful.

**Victoire, the gossip broker.**

- She controls information and printers. She rarely needs to lie, only to
  choose which true facts become visible.
- In 1789 that is gossip. In 1793 it is prosecution.
- At Thermidor she produces a surviving copy of something you believed
  destroyed: *"You didn't destroy the truth. You destroyed your copy."*

**The patron.**

- He genuinely saved you, through an illegitimate identity arrangement.
- He is responsible for your social existence, and also the strongest witness
  that it is fraudulent.
- His disappearance gains several possible explanations before it is resolved.

**Also in the cast:**

- *The prince,* a royal-blood suitor.
- *The bourgeois heir.*
- *The landlord,* who is unpleasant and holds your debts.

**Debts make the Terror personal.** The two people you owe most, Madeleine and
the landlord, are two people whose deaths would free you.

### Persistent objects, not a wardrobe simulator

A few garments become **historical artifacts.** For example:

- Madeleine advances credit for a spectacular royalist dress.
- Its invoice carries your assumed name, and the patron guarantees the debt.
- The landlord has a copy.

In 1789 that is fashion and money trouble. In 1793 it is an evidence packet
involving four people. The same assembly shape matters twice, for different
reasons. Most garments stay simple. A few memorable objects do the work.

Likewise, the Season keeps a **small number of parlour challenges,** each doing
something distinctive. The salon loop is not polished before the flip is
proven.

### Season loop (brief)

- **Calendar.** About three weeks. Afternoons for rendezvous, the modiste, or
  the rumor mill. Evenings for salons, reached by invitation letters
  (Appendix A.3).
- **Factions.** Crown and Revolution are the majors and are opposed. The
  Bourgeoisie is the minor and swings.
- **Gossip dilemmas.** Questions like "Is the Queen's necklace power, or
  excess?"
  - Each answer moves favor now.
  - If someone witnessed or recorded it, it is also **evidence later.**

## 3. The Terror: what you're willing to do to them

### Short episodes, shifting readings

The Terror is **a few short episodes, not one long phase.** Each episode reads
the same record with different weights:

| Episode | Reading |
| --- | --- |
| **Late 1793** | Revolution standing reads as influence. Crown standing reads as taint |
| **Spring 1794** | The Revolution's own credentials are reread: who was a Hébertist, who an Indulgent, who was too merciful. Factional fortunes change fast, so friends from 1789 become liabilities on a schedule |
| **Thermidor** | The final rereading |

This shows the central invariant twice before the finale: the record is the
same, the policy table is different.

### Four years later

These people have lived four or five years without you. **The dossier is how
the player discovers who they became:**

- the modiste may now supply uniforms, have apprentices, hide old clients, or
  have lost her business;
- a former revolutionary may be frightened by his colleagues;
- the rival may have done real good without becoming pleasant.

A few letters and a reunion carry the rest. Assembling a packet is exploration
as well as a puzzle.

### The institution

**Disposition is not fate.**

- The committee's ruling maps onto the credentials dispositions:

  | Committee ruling | Credentials disposition |
  | --- | --- |
  | release | PASS |
  | continued surveillance, or exile | DENY |
  | referral to the Revolutionary Tribunal | ARREST |

- What happens next (trial, political intervention, the mob) is the world's
  business. The evaluator never decides fates.
- The exact body is a historical decision and still open (§7). A police-side
  committee that detains and refers fits case-level work better than the
  governing Committee of Public Safety.

**Holding office in your own name** needs an explicit historical premise. The
institution barred women, and the story says so.

- For most of the story she exercises informal power, through her proxy.
- Formal office is a rare, exceptional outcome. One possibility: the proxy
  falls, she survives his shadow, and an alternate-history opening lets her
  take the seat. It is earned and costly. It is never routine inheritance.

### The core mechanic: assemble the packet

This is credentials inverted. In the checkpoint games, you check a packet
someone else assembled. Here you **assemble** it, and the committee judges the
**presented record.**

| Part | In the Terror |
| --- | --- |
| **Accusations** | Deeds and associations the prosecution's witnesses can produce |
| **Answers** | Testimony, certificates, alibis, invoices: whatever covers an accusation |
| **The rules** | The Law of Suspects, plus the current episode's reading |
| **Your pool** | Evidence *you* hold or can obtain from people who will give it to you, plus forgeries you can commission |
| **Your goal** | Declared at the start: release, surveillance/exile, or referral |

Your moves mirror the checker's sins:

| Checker's sin | Your move | Effect |
| --- | --- | --- |
| Ignoring an error | **Sandbag** | Withhold an exculpatory piece. Hélène hangs |
| Inventing an error | **Embellish** | Present a forgery, to free a friend or bury an enemy |
| (none) | **Challenge** | Discredit a prosecution piece. See below |

**Challenge is where the Season pays off:**

- discrediting a witness may need a relationship you built in 1789;
- proving a letter forged may reveal that you know the supposed author's
  handwriting unusually well.

Winning the case in front of you can become a liability later.

**Make cases about *why*, not combinations.** Each case asks three things:

- why you want this verdict;
- whom your intervention exposes;
- what it costs the next case.

Influence is committed and does not come back (Appendix A.2). Forgeries risk
being caught, and being caught raises **suspicion,** the Terror's meter pointed
at you.

### Who comes before the committee

- **Known characters** get personalized cases the player can intervene in. In
  the first slice, only they do.
- **Strangers** are still processed. The world goes on without you, and the
  docket shows it.

### Thermidor: what they remember about you

The regime turns again, and your case comes up. **You are no longer the
dossier's only author.**

- After a Terror spent deciding which evidence defines everyone else, you face
  what others kept, believed and remember.
- Some testify for you, some against, and some refuse to speak. Each acts from
  their own history and holdings, not from a terminal branch table.
- The strongest version asks whether you can assemble **a truthful defense of
  yourself.** Not an impeccable one, and not necessarily an acquittal.

The record never changes, but a person can. Someone might sincerely embrace
aristocratic society in 1789, sincerely back the Republic in 1793, and sincerely
regret the Terror after. An institution has every incentive to recast that as
hypocrisy. The question underneath:

> **What does it mean to be accountable for a person you used to be?**

### Endings

The four main endings are read off the shape of your record:

| Ending | Record | Outcome |
| --- | --- | --- |
| **Robespierre** | All-in on one corner | You rose, then fell |
| **Talleyrand** | Hedged toward the center | You survive every regime, and no one loves you |
| **Émigré** | You got out | Fled, possibly with whoever you saved |
| **Martyr** | Influence spent on others | They lived, and the cost was you |
| **Refusal** | You stopped playing | Walked away, burned the papers, vanished, or protected someone at the cost of the career the Season built. Not necessarily happy, but your desires changed |

**Stretch endings:**

- **The Incorruptible.** Institutional capture, not a body count.
  - Removing the rival power-holders is necessary but not sufficient. You must
    have **taken their authority.**
  - The result is victory by destroying everyone whose judgment used to matter.
  - The title is still to be settled. Robespierre's own epithet is the ironic
    candidate.
- **The Restoration gambit.** Everyone is gone but the prince.
  - A foreign crown backs a counter-revolution with him as figurehead and you
    as architect.
  - The restored order then discards the accomplice who made the restoration
    possible.
  - That ironic failure is the whole ending. No further survival path is
    planned.

### Prestige gating (New Game Plus)

The stretch endings unlock only after a main ending. A first run teaches the
flip, and later runs are played knowing what the Season is for.

- Each ending opens something specific:
  - *Émigré* opens the foreign envoy the Restoration gambit needs;
  - *Talleyrand* opens Victoire's own line;
  - *Robespierre* or *Martyr* opens the Incorruptible.
- **Deferred until the base game works:** new factions (Church, Army),
  cast-generation matrices, and large additional routes.

## 4. Why this is more interesting than the source

The source never contests its frame. Salons are grind, rendezvous are an
interchangeable cross-product, favor buys only more favor, and its mystery runs
beside the social loop rather than through it.

| What changes | Why it matters |
| --- | --- |
| **The genre is on trial** | Charm, appearance and patronage are aristocratic sociability. A dating sim set in 1789 can be about its own values |
| **Rereading, not rewriting** | The engine rule that regime change writes nothing (Appendix A.1) is also the theme. History rereads people |
| **Dramatic irony** | The player knows 1793 is coming and the character doesn't. **Advertise the Terror; don't spring it.** Every flirtation becomes a visible future liability |
| **People, not abstractions** | The cases are people you dressed with, owe money to, slept with, and humiliated, and who have lived four years since |

## 5. What it drives in the engine

### Integration demo: existing mechanics composed

| Mechanic | Where it shows up |
| --- | --- |
| Assembly (`ComponentManager`, slots, budgets) | Outfits in the Season, case packets in the Terror |
| Credentials kernel | `derive_disposition`, `Restrictions`, packet materialization |
| Asset wallet and tokens | Favor, livres, committed influence, gossip and evidence tokens, invitation letters |
| Progression | A few parlour challenges, using `forced_outcome` |
| Sandbox schedule | The calendar |
| Provisioning | Invitations as open edges that materialize salons on traversal |

### New mechanics it forces

1. **Readouts over favor** (Appendix A.1). Each episode is a new set of readout
   weights.
2. **Assembly-mode credentials** (Appendix A.2), judged on the presented record.
3. **Evidence with holders.** Admitted evidence is a token someone holds. The
   player holds gossip and evidence tokens, and NPCs hold their own. No new
   framework is needed on day one; holders are ordinary asset holders.
   Thermidor needs NPCs to contribute evidence from their own holdings, and
   that is the part to design when the slice reaches it.
4. **The journal as truth.** The journal records what happened. Retrieval from
   it uses the journal segmentation and retrieval contract (#191, closed). It
   decides *what is true*. Holders decide *what is admitted*.
5. **Ending-gated unlocks.** #448 (open) defines account-level achievements,
   with Coronate's NG+ entry as the first repeated-play consumer. #208 (closed)
   left broader meta-resources for a distinct consumer. Salon Season is that
   consumer: *which* ending unlocks *which* content. Build it after #448 lands,
   and after the slice.

## 6. First slice: does the flip land?

| Act | Contents |
| --- | --- |
| **One Season week** | Two salons; Lucien and one other suitor; one gossip decision; Hélène's and Madeleine's lines |
| **The boundary** | A time skip that rereads the record |
| **One committee session** | Two cases. Madeleine is tempting to save because she is liked. Hélène is tempting to sandbag because she is hated |

**Requirements:**

- At least one concrete **fact, document or witness from the Season** is
  visibly reused in *each* case.
- A proxy with at least one recognizable conviction or limit.
- A cost that outlives the packet: committed influence, suspicion, someone's
  testimony, or future exposure.

**Acceptance:** not "can one assembly kernel build outfits and dossiers?" but
**"does the player remember what happened in the Season and feel differently
about using it now?"**

If the flip lands, build Thermidor, NPC testimony and the endings. If it
doesn't, more salons or a fourth faction won't fix it.

## 7. Open questions

- **The institution.** Which committee, which powers, and which outcomes can
  the player plausibly cause?
- **The protagonist's papers.** How explicit is the forged identity, and when
  does the player learn about it?
- **Historical figures.** Background only, or recurring presences?
- **How much Season?** Enough for the flip to hurt, and no more. The slice will
  calibrate this.

---

## Appendix A. Engine resolutions

### A.1 Checkpoint 1: favor and readouts (approved, review fix applied)

**Store.** Raw favor mass per faction, held in the player's `AssetWallet`.
`Faction` subclasses `CountableAsset`. Mass is nonnegative and clamped at zero.
Favor is history, and it is never rewritten.

**Readouts,** computed and never stored. They read **faction assets only**:

- *renown:* the total faction mass;
- *alignment:* faction mass divided by renown, a barycentric point;
- *standing(f):* `Quality(w[f] · favor)`, with each faction authoring its own
  weight row.

The wallet also holds livres and other countable assets. An unfiltered
`total_value` would let money inflate renown and skew alignment. So readouts
pass a faction-only mapping to the shared weighted-sum method.

**Coupling is the weights.** For example, the Crown's row is
`{crown: 1, revolution: -0.5}`.

**One pathway.** The wallet gains a weighted-sum method over an explicit
mapping, and `total_value` is re-expressed through it.

**Regime change adds readouts** over the same store, one set per episode. The
boundary writes nothing. *Committed* influence is a separate fact (A.2).

### A.2 Checkpoint 2: assembly-mode credentials (approved, review fixes applied)

**Truth is the offer.** The world builds one `ScenarioOffer` per case from
story state:

- estate → `region`
- deeds → `contraband`
- missing papers → `failure_modes`
- actor uid → `bearer_id`

**Target disposition is derived, not defaulted.** `ScenarioOffer` defaults to
PASS, and `materialize` raises when the derived disposition disagrees with
`target_disposition`. So the builder derives the truth's disposition first and
sets the target from it. The invariant stays as the builder's consistency
check.

The truth is for the world: fates, later discoveries, Thermidor witnesses. It
is **not** what the committee sees.

**The packet is the presented record.** The case's `CredentialPacketManager` is
what gets assembled:

- **Prosecution pieces** are what the prosecution's witnesses hold, pre-assigned.
  This is not the offer's full truth.
- **The player's pool** sits in the existing `unpresented` slot. It contains
  evidence the player holds, or can obtain from willing holders, plus
  commissioned forgeries.
- **Present** = `assign` to the packet slot.
- **Sandbag** = leave a piece unpresented.
- **Embellish** = present a forged component.
- **Challenge** = strike a prosecution piece, at a committed cost (below).

**Testimony answers accusations the way permits answer contraband.** A deed is
covered by a valid answer keyed to its indication. A forgery is a `FORGED`
component. The rules table is the Law of Suspects, plus the current episode's
reading.

**Influence is committed, and persists across cases.** Two facts make the
budget:

1. The **influence readout** (A.1). It is computed and never stored.
2. **Committed influence:** a durable coda-local counter, held as a countable
   asset in the wallet. It grows whenever influence is spent.

*Available = readout − committed.* Each case's manager gets a `tracked_resource`
capacity equal to available influence at case start. It is a local preview cap
only.

- `SlottedContainer.unassign` recalculates consumption from what is still
  assigned. Pulling a piece back during assembly therefore refunds within the
  case, which is fine while the player is still deciding.
- **On commit,** the presented pieces' cost is added to committed influence.
- **Challenge is a debit on committed influence,** not an `unassign`. An
  `unassign` would refund rather than cost.

Scarcity therefore holds across cases and episodes, and Thermidor reads the
remaining balance.

**Commit and evaluate.** The player declares a goal and commits.

- The evaluator runs `derive_disposition` on the presented record.
- Each forgery makes one seeded, replayable catch roll.
- **A caught forgery is struck** from the record, and the remaining record is
  re-derived. Pieces the player withheld **stay withheld.** Catching a forgery
  is not omniscience.
- Suspicion rises. The forgery itself becomes a durable fact, which Thermidor
  witnesses can raise.
- Success means the verdict matches the goal.
- The result records:
  - the goal and the verdict;
  - the pieces presented, withheld and struck;
  - `caught`;
  - the truth's derivation, for the world's use only.

**Kernel footprint.** A sibling game mode over the same kernel, reusing
`derive_disposition`, the packet manager, `materialize` and the assembly
budget. It adds:

- assembly moves;
- a goal-match result;
- the committed-influence charge at commit.

Inspection mode (`credential_gate`, `hall_monitor`) is untouched.

### A.3 Checkpoint 3: no generic offer (approved)

An invitation is an **invitation-letter asset token** whose locals hold its
sampled parameters. Those parameters are sampled once, at UPDATE.

- The evening hub offers one choice per letter.
- Each choice's successor requirement carries the salon template as
  `fallback_templ`.
- Provisioning materializes the salon on traversal.

`ScenarioOffer` stays credentials' domain record. Promoting it would duplicate
`EntityTemplate` and provisioning.

## Appendix B. Salvage from the old `minuet` folder

| Old artifact | Disposition |
| --- | --- |
| Faction ladder and "the majors never align" | Keep, reduced to 3 factions × 3 tiers |
| Salon hub, slots, arrival judgment | Keep the shape, with new prose, kept small |
| Parlour game as a forced walk to a fixed outcome | Keep a few |
| Gossip dilemmas | Keep the shape, with new dilemmas. Witnessed answers become evidence |
| Rendezvous suitor × place reactions | Keep the shape as reaction tables |
| Formal wear | Keep as outfit assembly, with a few persistent artifacts |
| Vanished patron, rival, broker, debts, trial (source *shapes*) | Keep as the new cast |
| Archetype × faction matrix for a generated cast | Defer |
| Jinja-dereferenced prose, `afc.*` Python | Drop |
| Ripped string dumps | Not content. Keep them local as a detangl test corpus |

## Appendix C. Slice validation

**Flip.** The same Season record yields different influence and taint under the
episode readouts, and the boundary writes nothing.

**Readouts ignore money.** Adding livres to the wallet changes neither renown
nor alignment.

**Offers.** An offer built from state that derives DENY or ARREST materializes
without error. Its target was derived, not defaulted.

**Assembly.** For a fixed case:

- presenting the exculpatory piece yields release;
- sandbagging it yields referral.

**Caught forgery.**

- An uncaught forgery wins.
- With the catch roll forced, the forgery is struck, withheld genuine evidence
  stays withheld, and suspicion rises.
- Sabotage check: restore the withheld pieces on catch, and confirm this target
  fails.

**Committed influence.**

- Committing case one reduces case two's capacity.
- Challenge lowers available influence.
- Pulling a piece back before commit refunds only within the case.

**Season reuse.** Each slice case presents at least one piece whose holder and
provenance trace to a Season event.

**Persistence.** Mid-Season and mid-session saves survive a fresh-process JSON
round-trip, committed influence included. Replay is deterministic.
