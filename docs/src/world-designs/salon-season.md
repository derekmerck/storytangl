# Salon Season

**Status:** design brief, revised 2026-10-16 after review on PR #568. Nothing is
built.

- All three engine checkpoints are approved (Appendix A).
- Four contract defects were found in review and are fixed here: offer target
  disposition, committed influence, faction-only readouts, and what a caught
  forgery reveals.
- Grafting this world onto *Coronate the Regent* is deferred.

## Catalog position and implementation boundary

**Purpose:** prospective social-history showcase, under
[#395](https://github.com/derekmerck/storytangl/issues/395).
**Experiential invariant:** the same historical record supports different
institutional readings without rewriting what happened.

This remains an unimplemented story brief. Its 2026-10-16 review approvals below
settle proposed design checkpoints, not the existence of a playable world or every
API described in Appendix A. Recheck those interfaces before implementation.

| Connection | Existing floor and proposed experiment |
| --- | --- |
| Assembly, credentials, wallet/tokens, progression, sandbox schedules | Existing reusable rails; the two-act social/evidence composition is not yet a maintained consumer. |
| Favor and institutional readouts | Proposed faction-only interpretations of the same holdings. Test one regime change before generalizing social standing. |
| Assembled cases and testimony | Proposed distinction between historical facts, evidence holders, the presented packet, and an institution's judgment; existing inspection proofs do not establish this game mode. |
| Ending-gated return play | Separate account-persistence work in [#448](https://github.com/derekmerck/storytangl/issues/448), deferred beyond the first slice. |

Section 6 defines the first playable proof: one Season week and one committee
session reuse particular earlier facts in two cases. It would establish whether
institutional rereading changes the meaning of the player's own decisions. The
source/inspiration and rejected alternatives below remain part of the design.

**Recovered research opportunities (capability matrix A05 / A12; not selected
implementation work).** A05 suggests realizing a **single six-event history**
both chronologically and as an interrogation or institutional retelling,
including a later reclassification of an earlier assertion without mutating
its historical record. Two independently authored versions would not
demonstrate a genuine fabula/syuzhet separation.

A12 suggests analyzing promises as long-range obligations. Can an authoring
tool discover a promise never checked, a later demand without a reachable
producer, or two mutually unkeepable commitments, all from ordinary
world declarations rather than a separate list of flags? This is a possible
source-mapped [#396](https://github.com/derekmerck/storytangl/issues/396)
analysis consumer, not a prerequisite for the literary proof in Section 6.


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

### Talk of the salons: the news as a record

The gossip dilemmas are not invented questions. They are **the scandals of the
day**, and the period supplies plenty: self-dealing, war as a political
distraction, bought favor, cronyism, kleptocracy, a captured press, and a
public-health crisis that was really about bread. Whatever you say about them,
in front of whoever is listening, becomes part of the record the Terror and
Thermidor will read.

**Stay in period.** The parallels with other ages are obvious enough that
players will draw them themselves. Historical rhyme is sharper satire than a
headline, it ages better, and it keeps the world from turning into a tract. No
modern figure is named or caricatured.

| Theme | In the Season (1789) | Later in the record |
| --- | --- | --- |
| Self-dealing | Calonne's deficit and the ministers' pensions | The East India Company liquidation (1793–94): deputies forged a decree to profit, and the affair was used to bring Danton down with them |
| War as distraction | Talk of a foreign war to rally the country | The Girondins push for war in 1792 partly for domestic advantage, and that war drives the Terror |
| Favor and cronyism | Court pensions, purchased offices, the Necklace affair's afterglow | Speculation in assignats and nationalized lands; army supply contracts |
| The press | Royal censorship, and then the flood of pamphlets | Desmoulins is guillotined after calling for clemency in *Le Vieux Cordelier*. Meanwhile the War Ministry buys *Le Père Duchesne* in bulk for the armies: state-approved news |
| Paper money | The Caisse d'escompte's notes, convertible to coin only on the crown's say-so since 1788 | Counterfeit assignats printed by émigré presses, widely believed to have British connivance: a forged currency used to sabotage a regime |
| Scarcity | Bread prices; the Réveillon riot (April 1789) | The price Maximum and hoarding as a capital crime |
| Suspicion itself | Lettres de cachet | The Law of Suspects (September 1793), under which failing to show enough attachment to the Revolution is itself suspect. Also the "foreign plot": the charge that foreign gold, through the Baron de Batz, had bought deputies. It could be laid against almost anyone with money or foreign friends |

The Directory's open kleptocracy comes after the Season ends. It can colour an
epilogue, not a case.

**Each scandal owns its talk.** A topic is an owned episode, offered at any
salon while the scandal is live. Its arc (rumour, exposure, trial, aftermath)
sets when it is available. That is the landed scoped-offer path. Adding a
scandal adds one episode and touches no salon.

**What you say is a remark record.** It holds the topic, your stance, the
venue, who was present, and when. Like testimony, it is consumer-owned history:
it outlives the conversation and any binding. Those present are the people who
can later testify to it. Silence counts as a stance when someone notices it.

**Dress is a remark too, and so is the body.** Putting something on at a
venue writes the same record as speaking: stance, venue, who was present, and
when. The garment is a held token, and wearing it is the remark. The only extra
fact is how long the mark stays visible, because marks differ in how fast they
can be undone:

| Mark | Undone in | Period readings |
| --- | --- | --- |
| Tricolour cockade | A moment | Mandatory for men in practice by 1792 and by decree for women from September 1793, weeks before the Convention proclaimed freedom of dress. Too showy after Thermidor reads as Jacobin zeal |
| Breeches or trousers, the red cap | An evening | Silk knee-breeches mark the aristocrat. The *sans-culotte*'s trousers, carmagnole jacket and Phrygian cap are protection in 1793 and a target in 1795 |
| Dress and pockets | A season | The *chemise à la reine* scandal (1783) is both fashion and the Lyon silk trade. Slim 1790s gowns leave no room for tied-on pockets, so papers move into the reticule, mocked as the *ridicule* |
| Collars | An evening | Thermidor's *muscadins* wear black or green collars, the green reading as royalist |
| Patches, rouge, stays | A day to a season | Court rouge is aristocratic, Rousseau's natural face virtuous. Addison's *Spectator* (1711) mocked Whig and Tory ladies who patched opposite cheeks. Giving up stays reshapes the silhouette |
| Hair | Months | Powder gives way to the cropped *à la Titus*. After Thermidor, royalists crop *à la victime*, as the condemned were cropped for the guillotine |
| Brand | Never | The state's mark on convicts: the fleur-de-lis, later letters such as V for *voleur* |

Reversibility is what makes the body interesting. Crop your hair for the
Jacobins in spring 1794 and you are still visibly a Jacobin at Thermidor. You
cannot change your mind as fast as your clothes. Mechanically it is a mark with
a visible-until date, read like any other fact. And a wardrobe that turns with
each regime leaves its own record of opportunism.

**Who controls the truth is a reading, not a fact.** The remark sits in the
*historical truth* layer and never changes. Each regime supplies its own
reading over the same records, and that reading produces the charge:

| Remark in 1789 | Late 1793 | Spring 1794 | Thermidor |
| --- | --- | --- | --- |
| Mocked the Queen's spending | Sound republican instinct | Unremarkable | Unremarkable |
| Defended a censored pamphleteer | Patriotic | "Indulgent", if the pamphleteer was Desmoulins | A credential |
| Said nothing about the bread riot | Indifference: suspect | Suspect | Prudence |
| Praised a minister who later profited | Corruption by association | Worse once the East India affair breaks | Depends who is judging |
| Kept a confessor who later refused the clergy oath | Refractory ties: suspect | Suspect, now against a state cult of the Supreme Being | Tolerated; public worship is freed again in February 1795 |

**Two adjudicators that cover for each other.** Readings are not impartial
about who is accused. Under the old regime the crown names the bishops, the
church votes the crown a "free gift" instead of taxes, and each judge looks
away from the other's failings:

- At Metz in 1744 the bishop of Soissons refused Louis XV absolution until he
  sent his mistress away. The king recovered, recalled her, and the bishop fell
  from favour. No one preached that sermon again.
- The Toulouse parlement broke the Protestant Jean Calas on the wheel (1762),
  lending the state's court to the church's quarrel.
- The Parlement acquitted Cardinal de Rohan, Grand Almoner of France, in the
  Necklace affair (1786).

The Revolution rebuilds the same arrangement with itself on both sides. The
Civil Constitution of the Clergy (1790) makes priests state officials and
splits every parish over the oath. Dechristianization follows, and then, in
June 1794, Robespierre presides over the Festival of the Supreme Being. Terror
is declared the emanation of virtue, and the moral and the legal judge become
one committee. The mockery of that festival is one of the things that brings him
down.

Mechanically, collusion is a reading whose weights depend on the accused's
affiliation: an ally's swindle reads as nothing. That is more data, not a new
mechanism. The confessor is a witness no one else can be. Whether what you
confessed in 1789 can reach a case, and whether a juring priest would carry it
there, is a custody question like any other.

Whether a remark reaches a case is the *admitted evidence* layer, and that is
where the narrative is fought over:

- **Victoire and the printers** decide which remarks circulate and in which
  version. She rarely needs to lie.
- **Informants misreport.** An informant's account is a claim about the record,
  not the record itself. A false account is a forgery the player can challenge,
  or commission.
- **Patronage buys circulation.** Funding a paper is a wallet spend. Under the
  Terror it is also a remark of its own.

**Design rule: every stance is dangerous under some reading.** Early outrage,
loyal applause and prudent silence should each end up in somebody's indictment.
Being right too early is the classic revolutionary crime. No reading is the
true one, which is what keeps the world from preaching.

**What it needs from the engine.**

- Topic offers use the landed scoped-offer path.
- Remark records are the consumer-owned history listed as need 4 in §5's declarative section.
- Readings are journal retrieval ([#191](https://github.com/derekmerck/storytangl/issues/191)): journal, then slice, then Selector, with each regime supplying the selector and weights.
- One gap: a donated topic episode cannot yet see which salon invoked it or who was present. Until invocation context lands, the topic reads the venue from the walk (the call's return site) or the salon is passed in as a payload.

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

These people have lived four or five years without you. The dossier is the
first account the player gets of who they became, for example:

- the modiste may now supply uniforms, have apprentices, hide old clients, or
  have lost her business;
- a former revolutionary may be frightened by his colleagues;
- the rival may have done real good without becoming pleasant.

**The dossier is an interpretive document, like everything else.** It is the
institution's version of those years, built from what happened to be collected
and framed by whoever compiled it. "Supplied uniforms to the Army" reads as
patriotism or profiteering depending on who wrote it up. Victoire never needs
to lie, only to choose which true facts made the file.

So reading a dossier is the player's first act of judgment, before any
assembly: is this who she became, or who someone needs her to have become?

- **Other sources test it:** a letter from the accused, a reunion that
  contradicts the file, a witness the player trusts more.
- **A discrepancy is evidence.** Where the file is wrong, the gap is something
  the player can bring to a Challenge.
- **It cuts both ways at Thermidor.** Someone else's file describes *your*
  missing years, and you know exactly where it is wrong.

You *want* to know what happened to Hélène. The only account you get comes from
the people deciding whether she dies. Assembling a packet is exploration as
well as a puzzle, and the map you explore with is biased.

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

The main endings are read off the shape of your record:

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

### Integration hypotheses to prove

1. **Readouts over favor** (Appendix A.1). Each episode is a new set of readout
   weights.
2. **Assembly-mode credentials** (Appendix A.2), judged on the presented record.
3. **Evidence with holders.** Admitted evidence is a token someone holds. The
   player holds gossip and evidence tokens, and NPCs hold their own. No new
   framework is needed on day one; holders are ordinary asset holders.
   Thermidor needs NPCs to contribute evidence from their own holdings, and
   that is the part to design when the slice reaches it.
4. **Historical record and admitted evidence.** The evolving graph and replay
   history carry semantic state; the journal is its ordered narrative projection.
   The world may consult a witnessed record through the journal retrieval contract
   (#191) as part of its evidence policy, without treating prose as a complete or
   independent state authority. Holders decide *what is admitted*. Client-generated
   embellishment does not change that record.
5. **Ending-gated unlocks.** #448 (open) defines account-level achievements,
   with Coronate's NG+ entry as the first repeated-play consumer. #208 (closed)
   left broader meta-resources for a distinct consumer. Salon Season is that
   consumer: *which* ending unlocks *which* content. Build it after #448 lands,
   and after the slice.

### Declarative play authoring (relation to #702 and #703)

[#702](https://github.com/derekmerck/storytangl/issues/702) promotes sandbox's
scoped sponsor → receiver contribution path into ordinary provisioning. Its first
slices have landed: an Actor's `episodes` lower to graph-owned scenes, and a scene
`offer` with a `source_requirement` projects an ordinary call Action at matching
receivers whose scope exposes the owner, through a bound Role or setting. A scene
Role can own an episode independently of its current provider. The paired
Crossroads worlds (`worlds/crossroads_receiver`, `worlds/crossroads_sponsor`)
show both authoring stances, and the
[design note](../api/story/SCOPED_DONATION_DESIGN.md) records the limits: EAGER,
mutable stories only, and no trigger, invocation context or per-cause instances
yet. [#703](https://github.com/derekmerck/storytangl/issues/703) proposes provider
availability policies and a replaceable claim pass over provider capacity. The
geopolitical brief maps its crises onto the same path
([#704](https://github.com/derekmerck/storytangl/pull/704)). Salon Season is a
third consumer, and the most character-driven: most of its play is people bringing
their own episodes to places.

**Most of this world is sponsor-owned.** The brief already rejects a terminal
branch table for Thermidor. The receiver-owned alternative anywhere else would be
the same table.

| Authored layer | Owner | Receiver | Status |
| --- | --- | --- | --- |
| A known character's case | That character | A committee session that names the accused in a Role | Landed path |
| The proxy's powers ("ask Lucien to challenge") | The session's proxy Role, whoever fills it | The session's own blocks | Landed path (Role-owned) |
| Rendezvous, fittings, the rumor mill | A suitor, Madeleine, Victoire | An afternoon hub | Landed path; capacity per period is #703 |
| Gossip dilemmas | The salon | Its own blocks | Ordinary episode with optional Roles |
| Salons | An invitation letter in the wallet (A.3) | The evening hub | Needs custody scope |
| "Ask her for the invoice" | Whoever holds a relevant piece | The case's assembly | Needs custody scope |
| Thermidor testimony | Each surviving acquaintance | Your hearing | Needs a historical record and custody |
| The docket's strangers | The rule set | A committee session | Needs world exposure, triggers and per-cause instances |
| Endings | The rule set | The finale | Needs world exposure |

**What locality means here.** In Crossroads, adding Bram costs an actor with an
episode plus one shared Role in *both* versions; only the receiver-first version
also adds a call at every site. The same holds here. Adding a third case costs the
character's episode plus one line naming her among the session's accused. That line
is not a workaround: the committee does decide who comes before it. What the
sponsor-owned version saves is the case content and wiring at the session. A docket
computed from state, rather than authored, needs a world exposure handler (the BoP
consumer's first ask on #702).

**What this world needs from the model, beyond what has landed:**

1. **Scope through custody.** A letter or a piece of evidence donates because
   someone holds it, not because it fills a Role or a setting. Wallet membership
   could be a deliberately exposed scope path; surrendering the token would detach
   the offer. `HasAssets` is precedent, not an implemented donation path.
2. **Session context inside a case, and the proxy beyond it.** A character's
   case is her own scene, and the landed path adds no caller cast to a donated
   episode. So inside the case, the session's proxy Role and the episode's reading
   are not in scope. That needs invocation context, a follow-up #702 already
   names. Until then, the proxy's Role-owned powers attach at the session's own
   blocks, and the case reads world state. Reaching the seat from outside any
   session (player → proxy → seat) further needs a declared relationship chain,
   and a grant whose beneficiary is the player, not its provider. Recasting
   already keeps a Role's owned offers while the provider changes.
3. **Refusals filter, and they show.** BoP's attitudes mostly rank. Here a
   proxy's conviction is a hard gate, because learning what each person will
   refuse to do is the Season's lesson. A matching but unavailable offer already
   keeps a disabled Action. The refusal's reason ("Lucien will not alter a
   dossier") must reach disclosure.
4. **History is the world's, and outlives bindings.** Who was present when you
   answered a gossip dilemma is an optional Role in 1789 and a witness in 1793.
   The binding ends with the salon. The record of who was there is a
   consumer-owned historical record, not a live witness, and later availability
   policies must be able to read it.
5. **Creatable providers.** A stranger on the docket does not exist until the
   case is selected. Asking whether a role can be filled may count a provider
   creatable through the existing template path, without creating or sampling it
   during the read.
6. **Availability reads computed readouts.** Hostesses, holders and the committee
   judge by current standing, and a regime change only swaps readout weights
   (A.1). Offer and provider availability already evaluate in the receiver's
   namespace; the world must expose its readouts there, evaluated at semantic
   boundaries, so every offer re-evaluates at the boundary, which writes nothing.
7. **One owner, many receivers.** Madeleine donates a fitting to a Season hub, a
   case to a committee session and testimony to a hearing. Each is its own
   owned episode with its own receiving requirement.

**Hazards.**

- Covering an accusation with an answer is the credentials kernel's rule
  (`derive_disposition`), not requirement matching. Provisioning offers ways to
  *obtain* pieces. It does not decide what they prove.
- Committing influence is spending, not capacity. It stays a wallet counter (A.2),
  and no claim pass has to model it.
- Cases are not identified by accused plus episode. The same person can come
  before the committee twice for different causes, so per-cause identity is the
  world's, until #703's consumers settle it.
- Character arcs need no hierarchical owners. Owned episodes already reference
  their owner without making it a namespace ancestor.

**Sequencing.** The first slice (#669) can hand-wire its two cases: that is the
receiver-first baseline. Moving them to character-owned episodes with a proxy-Role
power at the session, then adding a third case, is this world's extension
experiment. It needs nothing beyond what has landed, as long as the case reads
world state rather than the session's Roles (point 2). Thermidor waits for points 1, 3 and 4. It is
the natural sponsor-owned consumer, and the reason not to build it as a table.

Illustrative, in the landed syntax where it exists:

~~~yaml
actors:
  madeleine:
    episodes:
      case:                             # owned by her, offered where she is accused
        action_name: Take up Madeleine's case
        offer:
          source_requirement: {has_tags: [committee_session]}
          once: true
        blocks: {...}
scenes:
  late_1793:
    tags: [committee_session]
    roles:
      proxy: {actor_criteria: {has_tags: [proxy]}}  # whichever suitor you bound
      madeleine: {actor_ref: madeleine}             # the docket: who is accused
  push_through:                          # owned by the seat, offered at the session
    owner_ref: late_1793.roles.proxy
    action_name: Ask your proxy to challenge a witness
    offer: {source_requirement: {has_tags: [committee_session]}}
    blocks: {...}
~~~

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
