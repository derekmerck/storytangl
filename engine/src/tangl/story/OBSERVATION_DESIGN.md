# Vantage, Observation, and Description

```{storytangl-topic}
:topics: observation
:facets: design
:relation: defines
:related: journal, presence, credentials, media, widget, open_link
```

**Document Version:** 0.8
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
made mutually exclusive; PoV example corrected. v0.7 (second review pass): observe()
is a truth-preserving PROJECTION (soundness + opacity), not set subtraction; call
direction corrected -- describe() is the leaf, render_text_as the controller; the
observation fold needs its own on_observe task (do_render_text is typed str|None);
both journal records preserved (semantic provenance AND experienced syuzhet), with
re-rendering as replacement+tombstone rather than silent regeneration; unreliability
separated from omniscience in non-goals. v0.8 (third review pass): opacity replaced by
NONINTERFERENCE (inference from visible evidence is expected; dependence on hidden state
is the leak); describe() is a local leaf taking only a detail hint while the controller
owns vantage and child recursion via render_as; Vantage is request-scoped context
referencing observer/scope/knowledge, not cursor identity or grammatical person;
referring expressions split into vantage-selects-identity then discourse-selects-form
(known names no longer suppress pronouns); ladder recast as four independent axes where
only realization quality soft-fails; composition de-specified to ordered collection with
arbitration deferred to a second consumer; type boundary downgraded to auditable
chokepoint with the condition for it to become structural; three-way record split
(graph = meaning, fragment = experience, observation = optional snapshot); LLM is a
realization backend, not a constraint; DispatchLayer.DOMAIN (invented) corrected.*
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

Each step is one more constraint over one authored string, which is why they compose
rather than multiply. The last two are not qualitatively harder than the first two —
they are the same substitution with a different constraint source.

---

## The cut

Three layers, each with one job:

```text
observe(subject, vantage) -> data    what is perceptible from here (the disclosure step)
describe(detail=...)      -> prose   an object's LOCAL default contribution
nominal(...)              -> phrase  how a thing is referred to in this mention
```

**Vantage never reaches the leaf.** `describe()` stays the object's local, default
semantic prose contribution — it may accept a `detail` *hint* (`nominal | short |
extended`), which is a rendering request, but it does not take a vantage and does not
consult story state. The existing 14 `describe()` sites stay valid as written.

**The controller owns perspective and recursion.** `render_text_as` / `render_as`
applies observation, runs the authority chain, walks children, and bounds recursion via
`TextRenderSession`. Children are reached **through `render_as`**, not by a leaf calling
`child.describe()` directly — otherwise per-child authority overrides and the recursion
bound are silently bypassed.

**Call direction — `describe()` is the leaf, not the controller.** This matches the
live code (`render_look_text` / `render_outfit_text` are `@on_render_text` handlers that
call `caller.describe()`), and inverting it would recurse:

```text
render_text_as(target, aspect, ctx)        story/presentation.py — the controller
  └─▶ on_render_text handlers              authority chain selects the source
        └─▶ target.describe(...)           the object's LOCAL default prose leaf
```

The controller's resolution order (not the leaf's):

```text
1. observe(target, vantage)        if the subject participates in disclosure
2. dispatch on_render_text         authority chain picks the source
3. target.describe(detail=...)     local default leaf, if no override wins
4. render_as(child, ...)           recurse per child THROUGH the controller
```

So `assembly.describe()` works unchanged today, and gains vantage-gating when the
controller starts observing it — no signature change to the leaf. Adoption is opt-in per
concept, and no parallel rendering path appears: controller, authority chain, and
recursion bound are all the ones that already exist.

### Detail levels

`describe(detail=...)` where detail ∈ `nominal | short | extended`. Recurring
mentions need not be exhaustive: first sighting may be `extended`, later references
`nominal`. Detail is a *rendering* request, not a disclosure control — it may never
widen what `observe()` permitted.

---

## Vantage

> **Vantage** — the epistemic position a projection is rendered from: what is
> perceptible, and what is known, at a point in the story.

**Vantage is request-scoped context, not an identity and not a grammatical mode.** It
*references* three things rather than owning them:

```text
observer         whose perspective this is (the focalizer)
spatial scope    what is currently in view / reachable
knowledge        persistent per-observer knowledge state, held as concept state
```

**Default binding: limited to what the current observer knows at the cursor's scope.**
That is where a vantage is normally *derived* from — but it is not identical to a cursor
and does not own the knowledge store:

- two readers may share one cursor;
- one reader may change focalizer mid-scene without moving;
- narrator knowledge is durable concept state keyed by narrator, so it outlives any
  single request while a vantage does not.

Multi-reader still falls out cheaply — distinct observers yield distinct vantages over
one graph — it just isn't a one-to-one identity with cursor or namespace.

**"Limited" here is epistemic, not grammatical.** Whether narration says *I / you / they*
is `PoV` (see below); whether the narration is *restricted to one observer's knowledge*
is vantage. The two commonly move together and are still separate axes.

Knowledge state is what lets `nominal()` return *"a guy with a backpack"* or *"Dave"* for
the same actor — the vantage supplies the answer, the knowledge store holds it.

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

### Observation is truth-preserving, not belief

An `Observation` carries **true content** — never false content. But `observe(vantage)`
is a *truth-preserving projection over permitted inputs*, **not** set subtraction.
Normalizing raw state into typed observations, aggregating components, and reporting
*"a silhouette"* instead of a person are all transformations, and all legitimate. The
invariant is about information flow, not about which operations are allowed:

```text
soundness         every claim in observe(...) is true of the underlying state
                  — it may abstract, aggregate, generalize, or re-type, but never invent

noninterference   the projection is computed ONLY from permitted inputs and does not
                  encode excluded state — vary a hidden fact with permitted inputs
                  held constant, and the output must not change
```

Set subtraction is one way to satisfy both. Abstraction ("a silhouette"), aggregation
(component union), and re-typing (raw state → `ValidityObservation`) are others.

**Noninterference, explicitly not non-inference.** A player *is supposed to* infer
hidden correctness from permitted evidence — in credentials that is the entire game, and
in correlated data non-inference is unachievable anyway. Inference from legitimately
visible evidence is expected and desirable. The leak is *dependence*: a projection whose
content varies with hidden validity or expected disposition, even if no excluded fact is
stated outright.

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
| `noun.describe(detail=...)` | local default prose leaf | convention exists across mechanics; no detail hint ✘ |
| `observe(subject, vantage)` | perceptible data (controller-invoked) | credentials-local only ✘ |
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
| **2 · Observation** | what of that is perceptible and known *from here*? | + vantage → `Observation` | engine (this doc) | ◐ credentials only (presence has related visibility/description behaviour, no formal `Observation`) |
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

This is **two decisions, not one ladder** — which is exactly why vantage and discourse
context were separated above. Collapsing them is what makes a known name suppress
pronouns forever (*"Dave … Dave … Dave"*).

**Decision 1 — vantage selects the permitted lexical identity.** What may this observer
call the subject at all?

```text
known_name(vantage, x)   ->  identity = PROPER    ("Dave")
otherwise                ->  identity = ANONYMOUS (a Nominal: "a girl with blue pants")
```

**Decision 2 — discourse context and grammatical role select the realization form**,
within whatever identity decision 1 permitted:

```text
not first_mention AND sole_salient  ->  pronoun(...)        "he" / "it"
owned_by_subject                    ->  Nominal.ppdet()     "her coat"
first_mention                       ->  PROPER: name()      "Dave"
                                        ANON:   idet()      "a brass key"
otherwise (subsequent)              ->  PROPER: name()      "Dave"
                                        ANON:   ddet()      "the brass key"
```

So a known person can still pronominalize on an unambiguous subsequent mention, and an
unknown one still moves indefinite → definite. Pronominalization stays deliberately
conjunctive — never a first mention, and only when exactly one active referent matches —
so it fails safe: a redundant *"the brass key"* is clunky, a wrong *"it"* is unreadable.

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
gating, and PoV switching are **not three features**. Issue #241 (LLM journal smoothing)
is not a fifth constraint — a model is a realization **backend**; the tone/smoothing
policy handed to it is the constraint. Every constraint here runs *downstream of*
`observe()`, so none widens disclosure.

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

### Four independent axes — not a degradation ladder

An earlier draft framed these as rungs where each degrades to the one below. That is
wrong in a way that matters: **vantage gating does not depend on name lifting, an LLM
does not depend on deterministic NLP, and a disclosure-sensitive projection must not
"degrade" to ungated prose.** Calling a safety downgrade graceful degradation is how
leaks get shipped.

They are four independent choices:

| Axis | Options | Note |
|---|---|---|
| **Authored source form** | raw string · explicit template · compile-time lifted | what the author writes |
| **Disclosure projection** | none · vantage-gated | **safety axis — never soft-fails** |
| **Realization backend** | template · deterministic NLP · model | quality axis — may soft-fail |
| **Durable output** | `ContentFragment` (+ optional observation snapshot) | what persists |

**Only realization quality may soft-fail.** No parser or no model available → prose gets
plainer. That is fine. But a story whose content is disclosure-sensitive may not fall
back to ungated rendering; if the projection cannot run, the correct behaviour is to
fail, not to narrate more than the observer knows.

**The floor is still real:** raw string → `ContentFragment` (axis 1 = raw, axis 2 = none,
axis 3 = template) is the only commitment, and it is what exists today. Everything else
is opt-in per axis.

**Compile-time lifting is the cheapest single move**, and it is *detangl easy mode*: with
a declared cast you can lift `Jane` → `{{ role.jane.name() }}` by matching names, no
parser required. It buys role rebinding for nearly nothing and keeps authored prose
readable. Note it is independent of vantage gating — either can be adopted first.

### What LLMs change (and what they sharpen)

Most of the machinery above predates practical LLM rewriting. Stanza is itself a small
task-specific learned model — the same family, differing in scale and generality — so
the useful distinction is not neural-vs-rules but **structured reproducible output vs.
generated text**. Given a model, the realization axis shifts:

- **The deterministic-NLP option largely collapses.** Parse → un-substitute → re-substitute, sense
  substitution, and conjugation lookup were mechanical means to an end a model now
  reaches directly. External conjugation/dictionary services are hard to justify.
- **Source form and disclosure matter *more*.** A model cannot know that `john` is bound to jane this
  playthrough, or that the viewer has not met her. That is story state, not language.
  Referent binding stays ours; compile-time declared-cast lifting is unaffected.
- **Stage 2 becomes load-bearing rather than optional.** **An LLM cannot be redacted
  after the fact.** Given full state and asked to describe a scene, it will disclose —
  helpfully, not maliciously. So `observe()` stops being a correctness nicety and
  becomes *the constructor of the model's input set*. The disclosure boundary must sit
  upstream of the model, which is where this document already places it.

**Determinism resolves via the existing thesis.** LLM prose is not reproducible, but
fabula-invariance never required identical discourse — replay-as-reskin explicitly wants
different words for the same events. The constraint that follows is narrow:

> **Three records, three jobs.** *Authoritative semantics* live in graph state, case
> receipts, and referenced concepts with their provenance. *Experience* lives in
> `ContentFragment.content` — the prose the reader actually read. An *`Observation` is a
> transient projection*, optionally snapshotted when audit or exact replay needs a record
> of what was disclosed.

An earlier draft called observations "the durable semantic provenance." That
overreached: an observation is deliberately **narrowed**, so it cannot be the authority
for meaning. Meaning stays with the graph and its receipts; the observation records only
what was shown.

The journal contract is unchanged: realized prose is stored as the historical
projection, and **ordinary retrieval returns what was read, never a silent
regeneration**. Scrolling back must not quietly reword the past.

Re-rendering is therefore an explicit operation, not a retrieval side effect. Replay,
reskin, and retcon **produce replacement fragments and tombstone the superseded ones**
— the same provenance-bearing tombstone discipline used elsewhere — so the record of
what the reader saw, and the fact that it was later re-realized, both survive.

The failure mode to avoid is narrower than "don't store prose": it is letting generated
prose become the *only* record of an event — a fact that exists in the text and nowhere
in the graph. Keep the graph authoritative for meaning and fragments authoritative for experience. A model is then simply one realization backend among several.

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

**The override is an ordinary dispatch handler — but it cannot ride the text hook.**
`do_render_text` is typed to `str | None` and raises `TypeError` on anything else, so a
fold returning `Observation` data must **not** overload `on_render_text`. The correct
shape reuses the same `BehaviorRegistry` with its own task:

```text
on_observe / do_observe    a future story-dispatch task returning Observation data
                           (same registry, same authority layers, distinct task)
on_render_text             existing, str | None — prose only, unchanged
```

An outfit-aware fold registers on `on_observe` at a layer above the shipped default —
`AUTHOR` or `USER` for world-supplied overrides, given the real ladder is
`GLOBAL < SYSTEM < APPLICATION < AUTHOR < USER < LOCAL` and the shipped fold sits at
`APPLICATION`. (An earlier draft cited a `DOMAIN` layer, which does not exist.) No new registration *mechanism*
— but a new *task*, because the type contracts genuinely differ. Keeping the two tasks
separate is also what makes the observation/prose type boundary real rather than
nominal.

### Composition: start ordered, defer arbitration

An earlier draft specified a full merge scheme — key of
`(subject_id, observation_type, aspect)`, scope-distance arbitration, stable `source_id`
sort. That was **over-specified for one consumer**: the base `Observation` shape has not
been chosen, today's credential observations carry none of those identity fields, and
they preserve authored order. Writing generic arbitration before a second consumer
exhibits the same collision is exactly the premature generalization this codebase
otherwise resists.

Start with the minimum that is actually forced:

```text
boundary     a typed Observable surface: observe(subject, vantage) -> Observation
collection   deterministic ORDERED collection over children (authored order preserved)
folding      concrete domains filter or fold via a distinct on_observe task
```

Deterministic ordering is enough for replay stability, and authored order is what the
existing credential observations already rely on. **Extract generic arbitration only
when a second consumer demonstrates the same collision** — and let that consumer's real
collision choose the key, rather than guessing it now.

---

## Why this matters: disclosure becomes a type boundary

The load-bearing consequence — stated at the strength it actually holds. If realization
consumes only `Observation`s, a leak must occur inside `observe()`: **one auditable
chokepoint per concept** rather than a property to re-check at every prose site.

**Today that is a chokepoint, not a type-enforced guarantee.** `on_render_text` handlers
receive the original `caller` and a `PhaseCtx` exposing the graph, so a handler *can*
re-acquire the raw subject and inspect hidden state after an `Observation` was produced.
"Cannot leak" becomes structurally true only when realization is handed the
disclosure-safe `Observation` plus a suitably bounded rendering context, without the raw
subject in reach. That is the target; until then the honest claim is auditability.

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
- Not a narrator subsystem. **Omniscience** is a vantage configuration (a vantage with
  no occlusion). **Unreliability is not** — false or distorted narration is the separate
  authored distortion/revoicing layer downstream of `observe()`, per the
  truth-preserving rule above.
- Not a fragment channel. Observations feed descriptions, which feed journal
  fragments, which remain the only narrative output surface.
- Not a merge of facets and observations (rule vs. result).
- Detail levels are not a disclosure control.
- Not an NLG system. Stage 3 rewrites authored prose under constraints; it does not
  generate sentences from semantics. Stages 1 and 3 keep naive implementations until a
  consumer justifies better ones.
- Not a commitment to a parser. Stanza and spaCy are both candidates; the pipeline only
  requires POS + dependency head + referent resolution from whatever is chosen.
- Not a degradation ladder. The four axes are independent; only realization *quality*
  soft-fails. Disclosure gating never degrades -- if the projection cannot run, fail
  rather than narrate beyond the observer's knowledge.
- Generated prose is not the authority for *meaning*, but it IS durably stored as the
  experienced record. See "Durable records" above for the three-way split.
