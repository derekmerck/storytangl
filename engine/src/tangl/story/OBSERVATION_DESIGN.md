# Vantage, Observation, and Description

```{storytangl-topic}
:topics: observation
:facets: design
:relation: defines
:related: journal, presence, credentials, media, widget, open_link
```

**Document Version:** 0.6
**Status:** DESIGN — proposed coarse-grid nouns (`Vantage`, `Observation`), a
description protocol over them, and a strawman prose pipeline. Not a migration plan.
*v0.2: three-stage prose pipeline (self-description / observation / realization),
discourse-context-vs-vantage split, strawman referring-expression selection policy.
v0.3: stage 3 corrected to constrained RE-realization of authored prose (parse →
un-substitute → adopt → re-substitute); four constraint sources unified (vantage,
PoV/tense, voice/register, skin) with #241 as a fifth; `scratch/discourse/refrazer/`
prior art recorded; parser placed in-pipeline. v0.4: authoring principle (authors
write prose, not template soup) with the worked constraint-escalation example; adoption
ladder with a rung-0 floor (raw string -> fragment) and graceful degradation; rung 2
(declared-cast compile-time lift) named as the cheapest next step. v0.5: LLM impact —
rung 4 collapses, rungs 0-2 and stage 2 sharpen (a model cannot be redacted after the
fact); durable record is the observation, generated prose is a projection. v0.6 (PR #350
review): Observation defined as redacted truth (never belief; distortion is a separate
authored layer); lang/story dependency inverted via a VantageLike protocol; describe()
and the non-commutative fold anchored to the existing render_text_as / on_render_text /
BehaviorRegistry dispatch; observation merge key defined; referring-expression rules
made mutually exclusive; PoV example corrected.*
**Relevant layers:** `tangl.lang` (noun protocol), `tangl.story` (vantage, dispatch),
`tangl.mechanics.presence` / `.credentials` / `.sandbox` (consumers),
`tangl.journal` (downstream output).

---

## Problem: three encodings of "what can be seen"

The same question is answered three different ways today, and none of the three
knows about the others:

| Encoding | Where | Shape | Vantage |
|---|---|---|---|
| `describe()` convention | presence (outfit, wardrobe, ornaments), assembly (vehicle) — 14 methods | prose (`str` / `list[str]`) | **implicit** ("the narrator, now") |
| `Observation` types | `mechanics/credentials/presentation.py` — `CredentialAttestationObservation`, `CredentialValidityObservation`, `CardProjection.visible_parts` | data, `neutral`/`visible` | **explicit** but local |
| `SandboxVisibilityRule` | `mechanics/sandbox/visibility.py` | booleans (`suppress_location_description`, `suppress_asset_affordances`, `suppress_fixture_affordances`) | implicit, ns-predicate driven |

No `Vantage` or observer concept exists anywhere in the engine (the only "observer"
symbols are unrelated tick observers). `describe()` therefore hardcodes a single
implied perspective, which is why multi-reader and knowledge-gated cases have no
place to attach.

This is one coarse-level gap wearing three costumes. Reconciling the three encodings
locally would generate the same finding every pass; naming the missing noun dissolves
all three.

---

## Authoring principle: authors write prose, not template soup

The requirement that motivates the whole stack. An author should write:

```text
you open the door and find john waiting for you
```

and **not**:

```text
{{ person.mc }} opens the door and finds {{ person.john }}
waiting for {{ person.mc.obj_pronoun }}.
```

The engine's job is to detangle authored prose and retangle it to match the current
story. Each step below adds exactly one constraint to the *same* authored source:

| Constraint added | Result |
|---|---|
| — (authored) | you open the door and find **john** waiting for you |
| role binding (john → jane) | you open the door and find **jane** waiting for you |
| vantage (jane not known) | you open the door and find **a girl wearing a pair of blue pants** waiting for you |
| tone / register | you open the door **brusquely** and find a girl wearing a pair of **worn** blue pants waiting **anxiously** for you |
| PoV + tense (2nd present → 3rd past) | **he opened** the door brusquely and **found** a girl wearing worn blue pants waiting for **him** |

Each rung is one more constraint over one authored string, which is why they compose
rather than multiply. The last two are not qualitatively harder than the first two —
they are the same substitution with a different constraint source.

---

## The cut

Three layers, each with one job:

```text
observe(vantage)   -> data    : what is perceptible from here (the redaction boundary)
describe(vantage,  -> prose   : how that reads, at a requested level of detail
         detail)
nominal(vantage)   -> phrase  : how the thing is referred to, given what is known
```

**`describe()` is the primary and expected surface.** Prose is assembled from
`describe()` calls; an implementation may be raw text or a Jinja template. The
existing 14 `describe()` sites stay valid.

**`observe()` is opt-in.** A concept implements it only when its perceptibility is
genuinely vantage-dependent. `describe()` consults it when present.

Default `describe()` resolution order:

```text
1. self.observe(vantage)              — if implemented, render from the observation
2. [c.describe(vantage) for c in self.components]   — else compose children
```

So `assembly.describe()` works unchanged today, and gains vantage-gating the moment
that assembly grows an `observe()`. Adoption is strictly opt-in per concept.

**`describe()` is not a new controller — it routes through the existing prose
dispatch.** Text realization goes through `story/presentation.py::render_text_as`
(which already dispatches `on_render_text` / `do_render_text` over the ordinary
authority chain) and composes under `prose/rendering.py::TextRenderSession` for bounded
recursion. Concretely: `observe()` supplies *what* may be said, and the existing
`on_render_text` chain decides *how it reads*. No parallel rendering path is
introduced, and no new registration mechanism is required.

### Detail levels

`describe(vantage, detail)` where detail ∈ `nominal | short | extended`. Recurring
mentions need not be exhaustive: first sighting may be `extended`, later references
`nominal`. Detail is a *rendering* request, not a disclosure control — it may never
widen what `observe()` permitted.

---

## Vantage

> **Vantage** — the epistemic position a projection is rendered from: what is
> perceptible, and what is known, at a point in the story.

**Default: third-person limited, pinned at the current cursor position.** Each
namespace carries its own vantage, which is what makes multi-reader work fall out
rather than require a mechanism: two readers on one graph are two cursors, therefore
two namespaces, therefore two vantages over the same state.

Vantage carries **knowledge state**, not only sightlines. Whether a concept's name is
known is part of the vantage, which is what lets `actor.nominal(vantage)` return
*"a guy with a backpack"* or *"Dave"* from the same actor.

### Deliberate misuses that validate the shape

A good coarse noun should support uses it was not designed for. Three that fall out:

- **Relayed vantage.** Talking a partner through a bomb defusal: your observations are
  filtered through what a remote actor reports. Vantage composes — one vantage is the
  input to another.
- **Narrative mode switch.** Moving from second-person to third-omniscient reveals
  everyone's tattoos under their clothes: same graph, same `describe()` calls, a
  vantage with no occlusion.
- **Unreliable narration.** A narrator who reports confidently but wrongly. See the
  truth-vs-belief decision below: this is *not* simply a lossy vantage.

That the first two are configurations rather than features is the argument that
`Vantage` is a real noun and not a parameter.

### Observation is redacted truth, not belief

An `Observation` is **true content, narrowed** — never false content. `observe(vantage)`
is a *filter*, and the only operation it may perform is removal:

```text
observe(vantage) ⊆ the true state.   It may omit. It may not invent or alter.
```

This is the decision that keeps the disclosure guarantee meaningful. If observations
could carry vantage-relative falsehood, "nothing downstream of `observe()` consults
hidden state" would no longer imply "downstream output is trustworthy," and replay,
audit, and the type boundary all become murky. It also honours the standing principle
that the engine guarantees determinism but never invents semantics — a lie is *authored
content*, not an engine-inferred filter.

Consequences:

- **Redaction and distortion are different layers.** Two observers seeing the same fact
  at different detail is redaction (this mechanism). A narrator asserting something
  false is authored, explicitly marked, and sits *downstream* of `observe()` as a
  distortion pass — never inside it.
- **Belief, when modelled, is state — not a vantage mode.** "What Jane thinks is in the
  box" is a fact about Jane's beliefs, observable in the ordinary way. It is not
  `observe()` returning something untrue.
- **Durable records stay objective.** A stored observation is a true-but-narrowed view,
  so replay and audit can rely on it.

### Vantage vs. PoV — adjacent, not the same

`tangl.lang.pov` already exists: **PoV is grammatical person** (how a subject is
addressed — I / you / they), consumed by `pronoun(pt, pov, gens)` and
`conjugate(pov)`. **Vantage is epistemic position** (what may be known). The
omniscient example moves both at once, which is why they blur; keep them distinct.
Open question below: whether `Vantage` carries a `PoV` or merely references one.

---

## The noun protocol

The `lang` package already has the pieces but no unified protocol — the subcalls
exist, the controller does not:

| Call | Purpose | Status today |
|---|---|---|
| `proper_noun.name()` | the bare proper name | `PersonalName.name()` ✔ |
| `noun.nominal(vantage)` | referring phrase, knowledge-gated | `Nominal` + `DeterminativeType`/`DetHandler` exist; no vantage ✘ |
| `noun.describe(vantage, detail)` | prose rendering | convention exists across mechanics; no vantage/detail ✘ |
| `noun.observe(vantage)` | perceptible data | credentials-local only ✘ |
| `noun.pronoun(type)` | pronoun for a slot | `pronoun(pt, pov, gens)` ✔ |
| `noun.conjugate(verb, tense)` | agreement | `conjugate(pov)` ✔ |

`Observation` is the missing member of a family that was already designed. That is
evidence for promotion rather than invention: the shape was predicted, the subcalls
were built, and the connective noun was the piece left out.

### Dependency direction: `lang` must not import `story`

`Vantage` is Story state, but the noun protocol lives in `tangl.lang` — so a naive
`nominal(vantage)` signature would invert the layering. `tangl.lang` currently imports
nothing from `tangl.story`, and that stays true.

Resolution is ordinary dependency inversion: **`lang` declares a minimal structural
protocol; `story` owns the concrete type and satisfies it.**

```text
tangl.lang    VantageLike(Protocol)   — only what realization needs:
                                        knows_name(subject) -> bool
                                        pov  -> PoV
                                        gens(subject) -> Gens
tangl.story   Vantage                 — full epistemic state; satisfies VantageLike
```

`lang` therefore never learns about cursors, namespaces, or perception; it learns only
the three questions a referring expression actually asks. This also answers open
question 4 below: `nominal()` stays in `lang`, `Vantage` stays in `story`.

---

## The prose pipeline (strawman)

Separating the concerns so they stop being reinvented per mechanic. Four inputs
produce one prose segment:

```text
  Observable ──observe(vantage)──▶ Observation ──describe(detail)──▶ Description
                                                                          │
   Vantage ─────────────────────────────────────────┐                     │
   (perception + knowledge)                          │                     │
                                                     ▼                     ▼
   DiscourseContext ──────────────────────────▶  realize(role) ──▶ Phrase ──▶ segment
   (what has already been said)
```

| Stage | Question | Input → output | Owner | Status |
|---|---|---|---|---|
| **1 · Self-description** | what is there to say about this thing, at this detail? | concept + detail → content | world / domain author | ✔ exists (14 `describe()` sites, text or Jinja) |
| **2 · Observation** | what of that is perceptible and known *from here*? | + vantage → `Observation` | engine (this doc) | ◐ credentials + presence only |
| **3 · Realization** | how does this thing enter *this* sentence, under current constraints? | + role + discourse + constraints → phrase / rewritten clause | `tangl.lang` + a rephrase layer | ◐ phrase generators exist; selection policy does not; a full rewrite pipeline exists in `scratch/` |

This is the standard natural-language-generation decomposition (content determination
→ referring-expression generation → surface realization) with **one StoryTangl-specific
insertion**: stage 2. Ordinary NLG has no epistemic filter as a first-class stage.
Naming that alignment matters because it tells us which stages are *replaceable with
existing art* (1 and 3) and which are *ours to own* (2).

### Discourse context is not vantage

The distinction most likely to be conflated, and the one that causes trouble later:

- **Vantage** — *what I can perceive and know.* Persistent, epistemic. Decides
  `"Dave"` vs `"a guy with a backpack"`.
- **Discourse context** — *what has already been said in this passage.* Transient,
  textual. Decides `"a key"` vs `"the key"` vs `"it"`.

Both feed the determiner choice, from different sources. A first mention of a
well-known person is `"Dave"` (vantage: known) with no determiner; a second mention of
an unknown one is `"the man"` (vantage: unknown → nominal; discourse: seen → definite).
Keep them separate or referring expressions will be wrong in ways that are very hard
to trace.

### What exists, and the one missing piece

`tangl.lang.Nominal` is already substantial — noun synonym lists, adjectives,
adjective synonym groups, quantifiers, plural inference — with working determiner
forms:

```text
Nominal(nouns=['pants','trousers'], plural=True,
        adjective_groups=[{'blue'}], quantifiers=['pair of'])

  .idet()  -> "a pair of blue pants"      .ddet()  -> "the blue pants"
  .ppdet(is_xx=True) -> "her pair of blue pants"
```

Plus `pronoun(pt, pov, gens)`, `conjugate(pov)`, `PersonalName.name()`,
`DeterminativeType` (indefinite/definite/possessive/demonstrative, with `use_an`
heuristics), and a thesaurus.

**The phrase generators exist; the selection policy does not.** Nothing decides *which*
of `idet` / `ddet` / `ppdet` / pronoun / proper name applies at a given mention. That
policy is the missing controller, and it is exactly where vantage and discourse context
meet.

### Strawman selection policy

Deliberately naive, obviously improvable, good enough to stop reinvention:

Two *orthogonal* predicates decide this, so a flat ladder gets it wrong — ownership and
salience are independent of first-vs-subsequent mention. Ordered by precedence:

```text
known_name(vantage, x)        vantage knows the proper name
owned_by_subject(x)           possessed by the current discourse subject
first_mention(discourse, x)   not yet mentioned in this segment
sole_salient(discourse, x)    only active referent matching gender/number in window

1. known_name                       -> PersonalName.name()   "Dave"
2. owned_by_subject                 -> Nominal.ppdet()       "her coat"
3. not first_mention AND sole_salient -> pronoun(...)        "it"
4. first_mention                    -> Nominal.idet()        "a brass key"
5. otherwise (subsequent)           -> Nominal.ddet()        "the brass key"
```

Rules 4 and 5 are the exhaustive fallback pair, so the discriminating checks must
precede them. Rule 3 is the classic ambiguity trap and is deliberately conjunctive:
never pronominalize a first mention, and only when exactly one active referent matches
— otherwise fall through to rule 5. Naive, but it fails safe (a redundant
`"the brass key"` is merely clunky; a wrong `"it"` is unreadable).

Detail level modulates *within* a choice — `nominal` picks the shortest form, `extended`
admits more adjectives and quantifiers — but never overrides vantage.

### Stage 3 is re-realization, not generation

The above understates stage 3, and one earlier framing here was wrong: parsing is *in*
this pipeline, not banished to authoring tooling.

Most story prose is **authored, then rewritten to fit the current pass** — not generated
from semantics. The authored line says *"Jane came in."* This pass needs:

- *"a girl with blue pants came in"* — vantage: Jane is not yet known;
- *"a girl with blue pants comes in"* — and this pass narrates in the present tense.
  (The clause subject stays third-person; only the *narration frame* is second-person,
  which is why tense and person move independently.)

So the operation is a round trip, not a render:

```text
authored prose
  ─ parse ─────────▶ words tagged with POS, dependency head, pov / pronoun-type / gens
  ─ un-substitute ─▶ resolve surface forms back to referents
                     ("Jane" → the Jane concept; "she" → most recent feminine referent)
  ─ adopt ─────────▶ apply current constraints
  ─ re-substitute ─▶ re-realize each referent + propagate agreement to dependents
```

**Un-substitute is `detangl` at sentence scale; re-substitute is `tangl`.** The same
round trip as the compression thesis, one unit smaller — which is why the two efforts
should share machinery rather than grow separate parsers.

### One mechanism, four constraint sources

The constraint that drives re-substitution is pluggable, and this is the unification
worth keeping:

| Constraint | Rewrites | Example |
|---|---|---|
| **Vantage** | referring expressions by knowledge | "Jane" → "a girl with blue pants" |
| **PoV / tense** | person and agreement | "came in" → "comes in" |
| **Voice / register** | word senses within a register | "ate the delicious sandwich" → "nibbled the nasty gruel" |
| **Skin** | domain diction over identical structure | issue #220 narrative skins |

Same parse, same rewrite, different constraint. That means narrative skins, vantage
gating, and PoV switching are **not three features** — and **issue #241 (LLM journal
smoothing) is a fifth constraint source**, not a separate layer. It also stays
structurally safe: every one of these runs *downstream of* `observe()`, so none can
widen disclosure.

### Prior art: `scratch/discourse/refrazer/`

A working version of this existed at ~v2.1.1 and should be mined rather than
reinvented:

- **`rephrase/{document,statement,word}.py`** — a `Document → Statement → Word`
  hierarchy where each `Word` carries `pov`, `pt` (pronoun type), `gens`, and `head`
  (its dependency head), with `render(ctx)` at every level. Built from a parse via
  `from_stanza()` / `from_passage()`. **`Word.head` is the substrate for agreement
  propagation**, and `Word.gens` is the substrate for the most-recent-referent tracking
  that resolves a later *"she"* back to Jane.
- **`Document.adopt_voice()` / `adopt_voices(*voices)`** — constraints are *adopted*
  onto a parsed document, and plural from the start. That is exactly the
  multi-constraint composition the table above needs.
- **`eurynym.py`** — a "broad word": a concept's sense collection across registers,
  with the full worked pipeline in its docstring (identify lemmas → check referent →
  select sense → per-POS morphological transform).
- **`dep_matcher.py`** — a spaCy `DependencyMatcher` sketch for propagating a
  substitution to dependent words, so swapping a noun carries its modifiers.
- **`sample_lingo.yaml`** — an authoring surface of `sememes` (sense sets per register)
  and `paradigms`.

It used **Stanza**; `dep_matcher.py` was a spaCy experiment. Parts already migrated
into the engine: `lang/pos/treebank_symbols.py`, and `lang/apis/`
(`language_tool`, `verbix`, `reverso`, `mw`) for morphology and lookup.

**The name carries the decomposition.** *refrazer* contracted "**ref**erence
dictionaries, conjugation, and expression **razor**s" into a homonym for *rephraser* —
and those three categories are still legible in the tree:

| Category | Where it lives now |
|---|---|
| reference dictionaries | `lang/apis/mw.py`, `apis/reverso.py`, `thesaurus.py`; `eurynym.py` sense sets |
| conjugation | `conjugates.py`, `apis/verbix.py`, `pronoun.py`, `gens.py`, `pov.py` |
| **expression razors** | **not built** |

A razor is a rule for choosing among candidates, so *expression razor* is the original
name for the selection policy identified as missing above: which of `idet` / `ddet` /
`ppdet` / pronoun / proper name applies at this mention. The strawman policy in this
document is one. Notably, the two categories that *were* built are the two with
external services to lean on; the razor is the part that was always going to be ours.

### Adoption ladder — a defined floor, optional rungs

**It starts with converting raw strings into fragments, and is built out from there
with whatever tooling is wanted.** That floor is the only commitment; every rung above
it is optional, independently adoptable, and degrades to the rung below.

| Rung | What it does | Needs | Status |
|---|---|---|---|
| **0 · Fragments** | raw authored string → `ContentFragment` | nothing | ✔ today |
| **1 · Templates** | explicit substitution — `{{ role.jane.name() }}` | Jinja (present) | ✔ today |
| **2 · Compile-time lift** | author writes `Jane`; the compiler rewrites it to `{{ role.jane.name() }}` against the declared cast | name matching, no parser | lowest-cost rung |
| **3 · Vantage re-realization** | referring expressions gated by knowledge | `observe()` + discourse tracking | this doc |
| **4 · Deterministic NLP** | tone, register, PoV/tense over parsed prose | parser + `refrazer` machinery | experimental |
| **5 · LLM refinement** | final polish over already-determined content | model access (#241) | proposal |

**Rung 2 is the lowest-cost rung**, and it is *detangl easy mode*: with a declared
cast you can lift `Jane` → `{{ role.jane.name() }}` by matching names, no parsing
required. It buys the first two rows of the escalation table (role rebinding) for
nearly nothing (sequencing is an implementation decision, not part of this design), keeps authored prose readable, and produces exactly the templates rung
1 already renders.

Graceful degradation is the property that makes this safe to build incrementally: no
parser available → you still have rung 2; no model available → you still have rung 4.
Prose quality degrades; nothing breaks. This is the same "additive and soft-failing"
posture the widget contract takes toward media.

### What LLMs change (and what they sharpen)

Most of the machinery above predates practical LLM rewriting. Stanza is itself a small
task-specific learned model — the same family, differing in scale and generality — so
the useful distinction is not neural-vs-rules but **structured reproducible output vs.
generated text**. Given a model, the ladder shifts:

- **Rung 4 largely collapses.** Parse → un-substitute → re-substitute, sense
  substitution, and conjugation lookup were mechanical means to an end a model now
  reaches directly. External conjugation/dictionary services are hard to justify.
- **Rungs 0–2 matter *more*.** A model cannot know that `john` is bound to jane this
  playthrough, or that the viewer has not met her. That is story state, not language.
  Referent binding stays ours; the declared-cast lift (rung 2) is unaffected.
- **Stage 2 becomes load-bearing rather than optional.** **An LLM cannot be redacted
  after the fact.** Given full state and asked to describe a scene, it will disclose —
  helpfully, not maliciously. So `observe()` stops being a correctness nicety and
  becomes *the constructor of the model's input set*. The disclosure boundary must sit
  upstream of the model, which is where this document already places it.

**Determinism resolves via the existing thesis.** LLM prose is not reproducible, but
fabula-invariance never required identical discourse — replay-as-reskin explicitly wants
different words for the same events. The constraint that follows is narrow:

> The durable record is the observation / fragment. Generated prose is a projection over
> it, never the stored artifact.

Store generated text as the journal and replay breaks; store the semantic fragment and
render at display time, and a model is simply the fifth constraint source, behaving like
the other four.

### What that fixes about the dependency question

- **A parser (spaCy or Stanza) belongs in stage 3**, at un-substitute. It is how
  referents are recovered from authored text. Not an authoring-only tool.
- **Stage 2 stays ours.** No parser models "what this observer may know"; vantage is
  the StoryTangl-specific insertion and cannot be delegated.
- **Stage 1 stays authored.** The source prose is the input to the round trip, so
  authoring quality still dominates output quality.

---

## Composition and folds

An observation composes from its parts:

```text
assembly.observe(v)  ->  default: union of [c.observe(v) for c in components]
```

**Union is the commutative default; a domain handler owns any non-commutative fold.**
Coverage masking is exactly where union is wrong — a tattoo under a coat must not
appear — so outfit-aware composition overrides it. This is the posture already settled
in `../mechanics/assembly/COMPONENT_DESIGN.md`.

**The override is an ordinary dispatch handler, not a new registration path.** There is
no separate "manager registry": an outfit-aware fold registers on the existing
`on_render_text` / `BehaviorRegistry` chain at `DispatchLayer.DOMAIN`, and the shipped
commutative union is the application-level default it supersedes. Same mechanism every
other handler uses; nothing new to wire.

### Merge contract for the union

"Union" needs a key, since composed observations are heterogeneous:

```text
merge key   : (subject_id, observation_type, aspect)
duplicates  : same key from multiple children -> keep the nearest-scope contributor
              (the arbitration order already used for grants), then stable-sort by
              source_id for determinism
disjoint    : different keys accumulate; no coercion between Observation subtypes
```

Subtypes never merge into one another — a `ValidityObservation` and an
`AttestationObservation` about the same document coexist as separate entries. Only
identical keys contend, and contention resolves by scope distance rather than by
arrival order, so composition stays replay-stable.

---

## Why this matters: disclosure becomes a type boundary

The load-bearing consequence. If `describe()` consumes only `Observation`s, prose
**cannot** leak hidden state — a leak has to occur inside `observe()`, which is one
auditable place per concept.

This converts a rule that people must remember into a structure that holds by
construction:

- *"no client may receive hidden mechanic state in order to make a choice legible"*
  (issue #337);
- no inferring correct/incorrect or new/old from action ids, metadata, or wording;
- credentials' `neutral, visible` observation docstrings become an enforced property
  rather than an authoring convention.

---

## Relationship to neighbouring concepts

- **Facets** (`ComponentFacet`) are the *rule*; observations are the *result*. A
  `hider` facet suppresses; an observation is what survived suppression. Shared
  subject matter, different intent — do not merge them.
- **Journal fragments** are downstream: `observe → describe → prose → ContentFragment`.
  Observation must not become a parallel fragment channel.
- **The four parity axes** in `docs/src/design/story/STORYTANGL_WIDGET_VOCAB.md` §0.2
  resolve cleanly against this stack: `observe()` is the **information parity**
  (decision legibility) boundary; `describe()` and its dispatch spine
  (`story/presentation.py` `render_text_as`, `prose/rendering.py` `TextRenderSession`)
  are semantic→text; the **CLI floor** is capability parity downstream of both. This
  disambiguates "presentation," which currently spans all of these plus display hints.

---

## Promotion assessment (two-key gate)

**(a) Invariants stateable without the originating demo** — yes:

> An observation is a fact about a subject as perceptible from a given vantage.
> Observations compose, union by default. A description is prose over observations at
> a requested level of detail. Nothing downstream of `observe()` may consult hidden
> state. Detail may narrow a description but never widen disclosure.

**(b) Positive reason to predict multiple mechanism-consumers** — yes: presence and
credentials are consumers *today*; sandbox visibility is the same question in boolean
form; multi-lane (issue #346) is a *scheduled* consumer that cannot be built without
an explicit vantage; media (which image is shown is a visibility question) and guides
/ inner voices (issue #340) follow.

→ **Promote** as a coarse noun, predictively, on spectrum argument — not on consumer
count.

---

## Open questions

1. **Typed-per-domain or generic `Observation`?** Credentials has domain subtypes. A
   small base plus subtypes (the `fragment_type` pattern) is the likely answer; the
   failure modes are dict-soup at one end and type explosion at the other.
2. **Does `Vantage` carry a `PoV`, or reference one?** The omniscient switch moves
   both; the bomb-defusal relay moves only vantage.
3. **Where does vantage come from at a call site** — an explicit argument, or read
   from `ctx`/namespace? Sandbox darkness is ns-predicate driven today; multi-lane
   forces an explicit answer.
4. *(resolved — see "Dependency direction" above: `nominal()` stays in `lang` against a
   `VantageLike` protocol; `Vantage` stays in `story`.)* Remaining: what the minimal
   protocol surface actually is — `knows_name` / `pov` / `gens` is a first guess.
5. **Retrofit shape for `SandboxVisibilityRule`** — does it become a vantage filter, or
   stay a facet-style `hider` whose *result* is an observation?

---

## Non-goals

- Not a migration plan. Existing `describe()` implementations remain valid and
  unchanged; `observe()` is opt-in per concept.
- Not a narrator subsystem. Unreliable/omniscient narration are vantage
  configurations, not new machinery.
- Not a fragment channel. Observations feed descriptions, which feed journal
  fragments, which remain the only narrative output surface.
- Not a merge of facets and observations (rule vs. result).
- Detail levels are not a disclosure control.
- Not an NLG system. Stage 3 rewrites authored prose under constraints; it does not
  generate sentences from semantics. Stages 1 and 3 keep naive implementations until a
  consumer justifies better ones.
- Not a commitment to a parser. Stanza and spaCy are both candidates; the pipeline only
  requires POS + dependency head + referent resolution from whatever is chosen.
- Not a required stack. Rung 0 (string -> fragment) is the only commitment; rungs 2-5
  are independently optional and each degrades to the rung below.
- Generated prose is never the durable record. Whatever renders -- template, parser, or
  model -- the stored artifact is the observation/fragment it rendered from.
