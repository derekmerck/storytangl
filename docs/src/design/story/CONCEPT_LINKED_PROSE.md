# Concept-Linked Prose and Journal Revoicing

```{storytangl-topic}
:topics: prose, journal, revoicing
:facets: design
:relation: documents
:related: observation, lang, roles, journal, compiler
```

> **Status:** #534 slice 1 implements explicit concept references and naming in
> optional `tangl.prose.naming`, with the executable `concept_naming_demo` world.
> Slice 2 adds exact scoped Role/Setting lexical linking in optional
> `tangl.prose.linking`, with the executable `concept_linking_demo` world.
> The broader linguistic
> adoption/revoicing discussion below is future design, not shipped behavior.
> The live #534 contract and its exception-recovery scope comment govern this note.
>
> **Scope:** how an author may write ordinary prose against a convenient
> reference cast while the compiler links references to scene-local semantic
> roles and the renderer later realizes those references against the current
> providers, narrator knowledge, discourse state, and concept state.
>
> **Neighbouring contracts:** `EPISODE_SYUZHET_RENDERING.md` remains the current
> rendering contract; `JOURNAL_COMPOSE_CONTRACT.md` remains the current journal
> composition contract; `engine/src/tangl/story/OBSERVATION_DESIGN.md` owns the
> proposed vantage/observation boundary. This note fills the missing middle:
> **referent linking and re-realization of authored prose**.

---

## Shipped exact-linking grammar (#534 slice 2)

The implementation boundary is documented in
`engine/src/tangl/prose/PROSE_DESIGN.md` and the executable world's README.
It adopts only exact scoped binding symbols, unambiguous proper reference-cast
spellings. Automatic naming is one-way: authors write proper reference-cast
names for adaptive naming; descriptive text such as `the blonde girl` remains
literal before/after introduction or recasting. No anonymous-phrase adoption,
initial-capital variant adoption, or `link_forms.anonymous` route is supported.
This approved narrowing supersedes the earlier anonymous-adoption proposal
throughout this note. Explicit anonymous semantic references/template APIs and
replaceable runtime anonymous wording remain supported. Ordinary proper spellings lower to
AUTO, not forced PROPER. Narrative `#intro` is an explicit ordered disclosure;
dialog names and markers remain literal. Actor/Location templates supply
spellings, while durable links address Role/Setting declarations by owner path
and edge label, and dereference current providers at realization. Complete-marker
recognition and diagnostics use the same `#intro\b` boundary: `#introduction`
and `#introvert` are literal. A descriptive phrase followed by actual `#intro`
is an unmatched instruction, not a guessed referent.

The source frontend is world-local and separately opted in via the existing
codec contribution seam, plus `link_prose` at world/scene/block scope. Raw
segments and escaped adopted forms bypass linking. Explicit template segments
are opaque to the linker; ordinary whole-block Jinja retains its old path.
Interleaving templates, lexical narrative, and literal dialog requires ordered
segments. Opted-in dialog callout content is rejected with an instruction to
use speaker segments. No arbitrary Markdown/template AST, NLP, pronoun,
determiner, alias, or spoken-name inference is implemented.

Catalog compilation does not create a runtime graph or mutate knowledge. Normal
constructor-form/JSON restoration, patch replay, and explicit rollback retain
symbolic links and historical output. Fresh-process restore still requires
normal world bootstrap. No custom persistence serializer or failure-recovery
mechanism is introduced. The broader examples below are design direction, not
additional syntax supported by this exact frontend.

---

## Thesis

StoryTangl should allow authors to write from a natural, stable point of view
without freezing that wording into story semantics.

An author should be able to write:

```text
Rin hands the ball to the gray-haired girl.
```

because, under the scene's reference cast, that is the clearest way to express
the event. If a later traversal casts Tisato into the role that Rin occupied
when the prose was written, the author should not have to maintain a parallel
version:

```text
Tisato hands the ball to ...
```

Instead, the compiler may opt in to a **concept-linking pass** that recognizes
the authored references, associates them with scene-local roles, and preserves
the intended realization form. The renderer then dereferences those links
against the currently provisioned concepts.

```text
clean authored prose
        ↓
optional concept linker
        ↓
linked prose: role references + realization intent
        ↓
runtime role provisioning / concept state / vantage / discourse
        ↓
surface realization
        ↓
journal fragments
```

The principle is the same from the smallest anonymous-until-met substitution to
full revoicing:

> **Authors write clearly from a convenient reference realization; the compiler
> links prose to semantic concepts; the renderer realizes those links under the
> current story state.**

This is one consequence of StoryTangl being a declarative story format rather
than a collection of already-final strings.

---

## The raw-text floor remains sacred

Concept linking is **opt-in**.

With linking disabled, authored text is opaque. The compiler does not inspect,
reinterpret, or rewrite it.

```text
linking OFF:
    "Rin walks into the room."
        → exactly that text
```

With linking enabled, the standard is deliberately conservative:

1. Link only references the compiler can resolve with high confidence.
2. Preserve enough information to reproduce the source under its reference
   environment.
3. Raise on an intended-but-ambiguous reference rather than guessing.
4. Never silently introduce a new referent or discontinuity.

The core acceptance property is a lossless semantic round trip:

```text
source prose S
reference environment E
linked form L = link(S, E)

render(L, E) == normalize(S)
```

That reference environment must include matching naming policy and narrator
knowledge. An anonymous runtime need not reproduce proper names in the source;
ordinary linked names use automatic policy selection rather than forced proper
wording.

`normalize` may remove compiler-only authoring hints such as `/r`, `her_`,
or `#intro`, but it must not change the ordinary prose they annotate.

A failed round trip is a linker bug. An alternate cast producing an invalid
realization is a renderer or semantic-policy bug. Keeping those failure classes
separate makes the system testable.

---

## Roles are the normal lexical scope

A role declaration may define a concept and, when authored inside a scene, also
publish a scene-local role symbol:

```yaml
roles:
  rin:
    name: Rin
    gamer_tag: "{{ self.mr() + 'Northstar' }}"
    hair_color: blonde
    gens: XX
    nominal: "{{ self.hair_color() + self.girl() }}"
```

Conceptually this can establish both:

```text
Actor("rin")
SceneRole("rin") → Actor("rin")       # reference / identity cast
```

A later scene may request the same identity without redefining it:

```yaml
roles:
  rin: ""
```

which means, in authoring terms, "bind this scene's `rin` role to the existing
compatible actor if one exists; otherwise report the unresolved binding."

The important distinction is that normal prose in a scene refers to the
**scene-local role**, not permanently to the actor that happened to occupy it in
the author's reference cast.

```text
authored "Rin"
    ↓ link
scene role "rin"
    ↓ runtime provisioning
current provider
```

If Rin is unavailable and Tisato is cast into the `rin` role, the same linked
reference now resolves through Tisato. No old passage needs to be edited to list
the new substitution.

To discuss the Actor concept Rin while some other actor currently provides a
scene role named `rin`, the prose must obtain that concept through another
semantic scope: another role, a relationship, a remembered identity, or an
explicit concept reference. The scene-local role remains the ordinary meaning
of the local symbol.

---

## Adoption: linking surface forms to roles

The compiler needs a policy for deciding which clumps of text "belong" to a
role. Call that policy an **adoption plan**.

The following broader adoption plan is historical/future exploration, not the
approved exact grammar. Anonymous descriptive adoption in particular has been
superseded by the one-way naming rule above; it would require a separate explicit
adoption contract, not inference from runtime descriptions.

Under such a broader reference cast, role `rin` might adopt forms such as:

```text
Rin
the blonde girl
a blonde girl
Ms. Northstar
she
her
her_
hers
```

Those strings do not all mean the same realization. They link to the same role
with different **reference intent**:

```text
Rin               → Ref(rin, AUTO)
the blonde girl   → Ref(rin, NOMINAL, DEFINITE)
a blonde girl     → Ref(rin, NOMINAL, INDEFINITE)
Ms. Northstar     → Ref(rin, ALIAS=gamer, HONORIFIC)
she               → Ref(rin, PRONOUN, SUBJECT)
her               → Ref(rin, PRONOUN, OBJECT)
her_              → Ref(rin, PRONOUN, POSSESSIVE_ADJECTIVE)
hers              → Ref(rin, PRONOUN, POSSESSIVE)
```

The source spelling is useful for linking and round-trip verification. After a
successful link, the durable semantic fact is the role reference and its
realization intent, not the original word sequence.

### Compiler-friendly hints

Ordinary English is intentionally the default. Hints appear only when English
is insufficiently precise.

Existing pronoun conventions such as `her_` / `his_` distinguish possessive
adjectives from object pronouns:

```text
her dog      → her_
he pinched her → her
```

A short git-style role prefix may disambiguate otherwise compatible referents:

```text
She/r handed the ball to her/t.
```

If the scene contains roles `rin` and `tisato`, and `r` / `t` are unique
prefixes, this links as:

```text
Ref(rin, SUBJECT) handed the ball to Ref(tisato, OBJECT).
```

A prefix must be unique in the current scene namespace. If both `rin` and
`ruka` are present, `/r` is ambiguous and compilation must fail until the
author writes a longer unique prefix such as `/ri`.

The escalation ladder should stay small:

```text
ordinary prose
    ↓ if ambiguous
tiny linker hint: she/r, her_/t, #intro
    ↓ if genuinely unusual
explicit template / semantic expression
```

The hints assist linking. Explicit semantic template expressions bypass lexical
inference.

---

## Conservative resolution, not heroic NLP

The linker should prefer false negatives to false positives.

A useful precedence is:

1. Explicit semantic/template expression: already bound; do not reinterpret.
2. Explicit adoption hint: `she/r`, `her_/t`, `Rin#intro`.
3. Exact unique proper-name or alias adoption.
4. Exact unique nominal adoption.
5. Unique compatible pronoun adoption.
6. Otherwise unresolved or ambiguous.

For example:

```text
Rin talks to Tisato. She frowns.
```

must not be assigned by intuition when both roles are compatible with `she`.
The compiler should report the ambiguity and ask for authoring information, not
guess which role the pronoun names.

This is the same safety principle as a linker refusing an unresolved or
multiply-defined symbol.

---

## Linked text is semantic; template languages are backends

Jinja is useful because StoryTangl already has `TextRenderSession`, recursive
rendering, and namespace access. It is not privileged as the semantic
representation.

A linked passage might conceptually be:

```text
[
    Ref(role="rin", form=SUBJECT, capitalize=true),
    Text(" handed the ball to "),
    Ref(role="tisato", form=OBJECT),
    Text("."),
]
```

A Jinja backend could emit:

```jinja
{{ rin.as_subj().capitalize() }} handed the ball to {{ tisato.as_obj() }}.
```

A TypeScript/npm runtime might instead consume a serialized linked form
directly, or lower it to a JavaScript template system:

```text
["ref", "rin", "subject"]
["text", " handed the ball to "]
["ref", "tisato", "object"]
["text", "."]
```

Portability therefore depends on a mapping from linked concepts and reference
intent to prose, not on reproducing Jinja internals.

A useful minimal linked-text vocabulary is likely smaller than a universal
content IR:

```text
Literal
ConceptRef
Sequence
SemanticDisclosure / SemanticEffect
```

Do not promote that vocabulary beyond what real consumers require. The
important contract is behavioral: stable referent + requested realization +
ordered position.

---

## Rendering is dynamic dereferencing

Once prose is linked, realization follows the current graph rather than the
reference cast.

```text
Ref(role="rin", form=NOMINAL)
        ↓
scene role "rin"
        ↓
current provider
        ↓
current concept state
        ↓
current narrator knowledge / belief
        ↓
current discourse context
        ↓
surface phrase
```

If `rin` is currently provided by Tisato, an anonymous nominal may become
"the gray-haired girl" without the author ever mentioning Tisato in that
passage.

If the provider remains Rin but Rin dyes her hair, the same linked nominal may
change from "the blonde girl" to "the red-haired girl."

If Larry learns a gamer handle and prefers it, a proper-style reference might
change from "Rin" to "Ms. Northstar." If the relevant gender state later
changes, the same alias projection may become "Mr. Northstar" while a plain
given-name projection remains "Rin."

Only projections depending on changed inputs should change.

This is why mutable state changing halfway through one passage is a useful
stress test rather than a pathological exception. Two references to the same
linked concept may legitimately render differently when a semantic transition
occurs between them.

---

## Truth, belief, vantage, and discourse stay separate

Concept linking answers **what semantic thing this text refers to**. It does not
collapse the different state sources that determine how that thing should be
described.

Keep at least these layers distinct:

```text
world truth
    current concept properties and relationships

observer/narrator knowledge or belief
    what this vantage knows or believes about the concept

discourse context
    how this mention should be realized here
    (proper name, nominal, pronoun, definite/indefinite, alias, etc.)
```

A mistaken belief should not mutate world truth. If Rin is male but Larry
believes otherwise, Larry's realization may use a feminine pronoun or honorific
while another vantage uses the current true state. The linked referent remains
Rin in both cases.

This follows the boundary in `OBSERVATION_DESIGN.md`: observation is
truth-preserving; belief, unreliability, and distortion are explicit state or
downstream presentation concerns.

---

## Inline disclosure and introductions

### Approved naming and dialog boundary (#534)

This clarification governs the naming slice and supersedes broader introductory
examples below where they imply automatic processing of spoken dialog. It is an
approved contract, not a claim that every authoring adapter is implemented.

Three operations must remain distinct:

| Operation | Uses current naming policy | Changes narrator knowledge |
| --- | --- | --- |
| Literal authored dialog body | No | No |
| Explicit concept reference or resolved speaker display label | Yes | No |
| Explicit introduction | As required for its authored output | Yes |

"Read-only" references are non-disclosing reads of concept/narrator state; they
may produce different output as that state changes. They neither create unknown
knowledge records nor mark a concept identified. Rendering a different speaker
label changes the output, not the concept's name, graph label, or knowledge.
Previously emitted journal text remains historical output, not a live view.

Spoken text instead preserves what the author says the character uttered. For
example, when neither Rin nor Nanae has been identified to the active narrator:

```text
[Rin] This is my sister, Nanae.
Nanae #intro smiles at you.
```

The intended output is:

```text
[the blonde girl] This is my sister, Nanae.
Nanae smiles at you.
```

The name in the speech stays literal; it is not substituted with Nanae's
anonymous nominal. The following explicit narrative introduction identifies
Nanae, not Rin. Neither a proper name appearing in speech nor a resolved speaker
label implies disclosure. Do not parse introduction markers or adopt concept
references automatically inside dialog bodies in this slice. Recognizing a
speaking role does not select a different narrator or infer the speaker's own
epistemic state.

An author may intentionally override that literal floor through an explicit
semantic instruction. Effects, template calls, and compiler-lowered macros are
three authoring forms of the same idempotent introduction transition on the
actual provider for the selected narrator:

- An UPDATE effect introduces before the turn's prose and labels are realized.
- An explicit template call introduces at its evaluation position, including
  mid-dialog if deliberately authored. A non-printing Jinja form is
  `{% set _ = introduce(rin) %}`; exact public helper spelling is adapter-specific.
- The opted-in exact frontend lowers narrative `#intro` into a position-preserving,
  template-neutral semantic introduction in #534 slice 2;
  the marker is an instruction, not evidence inferred from a name or quotation.

Introduction is therefore not intrinsically a JOURNAL-only operation. Authored
effects may call it at a normal mutation boundary, while the journal adapter
may call it during explicit ordered realization. Previewing or resolving an
ordinary reference/label never calls it implicitly. Keep normal phase mutation
rules and diagnostics; this is not blanket permission for implicit render effects.

An ordered ProseSegment speaker label resolves before its utterance. If an explicit template call
introduces Rin inside that utterance, that label stays anonymous and later labels
may use Rin. The explicit call does not authorize rewriting other literal names
in the speech. The ordered adapter does not re-execute generated wording as template code.
Ordinary raw/Jinja whole-block templates retain their existing evaluation and
composition order: labels bind afterward and see current/end-of-block knowledge.
Explicit calls there remain allowed, but per-utterance pre-body naming is not
promised. Authors needing that timing use ordered ProseSegment values.

Successful persistence, replay, and existing explicit rollback must retain
introductions. Unexpected traversal exceptions follow the existing non-atomic
failure contract; automatic recovery and safe retry are separate VM design work,
not prerequisites for this slice. Likewise, constructing another ServiceManager
does not reset World singletons, domain classes, or dispatch authorities. A
fresh-process restoration witness must perform normal world bootstrap before
opening the saved session. Soft reset/hot reload is a separate future feature.

Anonymous-until-met is one narrow application of linked prose.

An author-friendly marker such as:

```text
"I'm Rin #intro."
```

can link to a semantic reference equivalent to:

```text
Ref(role="rin", form=PROPER, disclose=IDENTITY)
```

or, in a Jinja backend:

```jinja
I'm {{ rin.nominal(intro=True) }}.
```

The shipped semantic introduction immediately identifies the actual provider
for the active narrator during explicit ordered JOURNAL realization or normal
UPDATE/FINALIZE effects. Forced proper wording alone does not
identify it. There is no staged receipt or deferred FINALIZE disclosure.
The explicit reference vocabulary preserves referent, intent, and introduction
independently of template syntax. Exact narrative `#intro` recognition is shipped;
spoken introduction inference is not.

Repeated introductions are idempotent:

```text
UNKNOWN    + intro → IDENTIFIED
IDENTIFIED + intro → IDENTIFIED
```

An optional block may introduce a role earlier than a later required block:

```text
optional: "Catch it, Rin #intro!"
required: "I'm Rin #intro and this is Tisato #intro."
```

Different paths and exits may legitimately leave different narrator knowledge.
There is no mandatory equal-knowledge-at-every-exit check. Guaranteed-introduction
postconditions and bounded scene analysis require a separate consumer/contract.

The same mechanism can later express disclosure of aliases, relationships,
locations, object identities, or other knowledge without inventing a separate
anonymous-name feature for each class.

---

## Direct semantic authoring remains an escape hatch

The natural-language linker should cover common cases, not every conceivable
surface realization.

An author may deliberately bypass it:

```jinja
{{ rin.nominal(known=False) }}
```

to force an anonymous reference even when the active narrator knows Rin, or:

```jinja
{{ rin.gamer_alias(honorific=True) }}
```

to request a specific lexical identity.

A world plugin may expose richer realization vocabulary:

```jinja
{{ paint.my_code(amount > player.inv + 1) }}
```

for distinctions such as countable objects versus substances, world-specific
honorifics, or other grammatical policy.

These expressions are rendering instructions, not hints. The compiler should
not reinterpret them as ordinary prose.

Semantic side effects are different. Arbitrary world helpers must not become
hidden story effects merely because they execute during rendering. Effects that
matter to story analysis should use a small discoverable semantic vocabulary
such as identity disclosure, so the compiler can reason about them.

---

## Full revoicing is the same architecture at higher resolution

A more aggressive front end may tokenize and parse whole sentences with tools
such as spaCy or Stanza:

```text
authored prose
    ↓ tokenization / morphology / dependency parse / NER / coreference
linked linguistic structure
    ↓ adoption into story roles
semantic references + grammatical relations
    ↓ transform
PoV / tense / cast / knowledge / register
    ↓ realize
new prose
```

That was useful for transformations such as:

```text
"I met her at a bar."
    ↓ first-person past → second-person present
"You meet her at a bar."
```

The concept-adoption layer remains the important StoryTangl-specific part.
Generic NLP can suggest that a pronoun corefers with a named entity; the scene
namespace grounds that entity to a durable role or concept.

Modern LLMs reduce the value of hand-built deterministic surface rewriting.
They do **not** remove the need for referent binding, disclosure control, or
semantic provenance.

An LLM is therefore best understood as another realization backend:

```text
linked concepts + permitted observations + discourse constraints
    → LLM realization
    → stored journal prose
```

The graph remains authoritative for meaning. The emitted fragment remains
authoritative for what the reader actually experienced. The model is not
trusted to reconstruct story identity from flattened prose after the fact.

---

## Existing StoryTangl pieces

This design mostly connects machinery that already exists or has prior art:

- `Role` / `Setting` binding and gathered scene namespaces.
- `EntityKnowledge` and narrator-keyed concept-local epistemic state.
- `tangl.lang.PersonalName`, aliases, titles, and gender-aware title
  normalization.
- `tangl.lang.Nominal`, determiners, quantifiers, and noun-phrase realization.
- `tangl.lang.Pronoun`, grammatical person/case, and gendered pronouns.
- `TextRenderSession` and recursive Jinja rendering.
- `render_text_as(...)` and Story dispatch for named textual aspects.
- `compose_journal` as the post-merge journal rewriting seam.
- `scratch/discourse/refrazer/` and `scratch/discourse/revoice/` as prior
  deterministic revoicing experiments.
- `OBSERVATION_DESIGN.md` for vantage, observation, discourse context, and the
  earlier "un-substitute → adopt → re-substitute" formulation.

The missing piece is not another prose generator. It is the explicit
**source-reference linking contract** between clean authored prose and those
runtime presentation mechanisms.

---

## Delivered first implementation slice

World domains import `tangl.prose.naming` and expose its `get_authorities()`
before normal compilation. `NamingActor` / `NamingLocation` add optional anonymous
wording and concept policy overrides. `ProseBlock` contains ordered segments and
explicit concept-linked `choice_labels`, keyed by stable action label.

The shared `NamingOperations.reference()` resolves a Role/Setting to its current
provider and reads its narrator record without creating one. `introduce()` owns
creation/writes during UPDATE/FINALIZE effects or actual JOURNAL realization. Named text aspects
`reference_auto`, `reference_proper`, and `reference_anonymous` use existing Story
dispatch, permitting world authorities to replace wording through that seam.

Precedence is explicit concept override (including `off`), then the closest
matching kind in the provider's MRO in world `naming_defaults`, then `off`.
`concealed` selects anonymous wording until identified; `proper` selects proper
wording without disclosure on read. Missing anonymous wording raises an error
identifying the provider and source block. No Presence dependency is required.

Each segment resolves its speaker display name before realizing its body.
References in the body run left to right; later segments and choices observe
immediate introductions. Speaker/action IDs remain unchanged. Literal segments
remain opaque; a segment's explicit Jinja `template` evaluates once against the
same `reference` / `introduce` operations. Generated wording is not recursively
re-evaluated. Arbitrary Jinja is a Python-native escape hatch, not portable IR.

Successful constructor-form and JSON service restoration, patch replay, explicit
rollback, narrator isolation, provider recasting, and historical wording are
covered by `engine/tests/prose/test_naming.py`. Raw worlds need no adoption.

### Ordinary dialog ordering: resolved bounded scope

The existing raw/Jinja pipeline evaluates an entire block through
`story.system_handlers._render_text()` before `compose_dialog_markup()` calls
`DialogHandler.parse()` and binds speakers. A compiled-world probe starts with
unknown Rin, introduces her through a non-printing template call in the first
utterance, and then emits a second utterance. At composition time both labels
see `IDENTIFIED`, producing `[Rin, Rin]`. This is the approved ordinary
whole-block limitation; ordered ProseSegments instead produce
`[the blonde girl, Rin]`. The literal body `This is my sister, Nanae.` remains
unchanged throughout. Introducing Nanae never implicitly identifies Rin.

The human resolved the checkpoint by retaining ordinary realization order and
using ProseSegment when precise timing matters. Resolved ordinary labels now
use the adopted `reference_auto` text-aspect policy as a non-disclosing read at
the existing composition point; absent an adapter, vanilla display-name fallback
is unchanged. No early parsing, template splitting, retrospective snapshot,
lexical body rewrite, or multiple-narrator inference is installed.

### Existing failure seam

A real compiled-world probe introduced Rin during JOURNAL and raised in FINALIZE.
It left Rin identified, emitted no introduction output or failed-hop patch, and
constructor restore preserved that identification. UPDATE and other mutations
can likewise remain partially applied. Automatic failed-traversal recovery is
outside this slice by the human design decision recorded on #534. Unexpected
exceptions propagate; safe continuation/retry of a partially executed live
story is not promised. No Frame callback, prose undo accumulator, transaction
framework, or deferred disclosure is installed. Existing explicit rollback is
distinct from automatic exception recovery.

## Deferred exact-reference linking slice

The first issue should prove the concept with the smallest useful consumer:
**epistemic naming of scene roles**.

Suggested slice:

1. Add an opt-in concept-linking flag at an authoring scope no broader than
   world/scene.
2. Build a reference-cast adoption table for scene roles from:
   - proper name;
   - exact role symbol;
   - explicit `#intro` marker.
3. Link only exact, unambiguous references. No generic NLP or broad coreference.
4. Preserve realization intent:
   - automatic policy-aware naming;
   - explicit forced anonymous/proper semantic references (not lexical descriptions);
   - identity disclosure.
5. Lower linked references through one initial backend, probably Jinja because
   the runtime already supports `TextRenderSession`, while keeping the
   semantic contract backend-neutral.
6. At JOURNAL realization, resolve the scene role to its current provider and
   render against narrator knowledge.
7. Make identity disclosure idempotent and patch/replay-safe.
8. Permit divergent knowledge at exits; optional guaranteed-introduction
   analysis is a separate future contract.
9. Round-trip every linked fixture under the reference cast.
10. Fail compilation on ambiguity rather than guessing.

Explicitly deferred:

- automatic pronoun adoption;
- `she/r` / `her_/t` prefix hints;
- aliases and gamer handles;
- generalized belief models;
- NLP parsing, NER, coreference, tense, or PoV rewriting;
- LLM realization;
- a universal persistent content IR;
- cross-language grammatical realization.

Those extensions should fall out of the same linked-reference contract if the
first slice is correctly factored.

---

## Design invariants

1. **Raw text always works.** Linking is optional.
2. **Authors write prose, not template soup.** Template code is an escape hatch,
   not the baseline.
3. **Scene-local roles are the normal referents.** Runtime provider substitution
   must not require passage rewrites.
4. **Linked references preserve realization intent.** A proper name, anonymous
   nominal, alias, and pronoun are different projections of the same role.
5. **Reference linking is conservative and lossless.** Ambiguity is an error,
   not a guessing opportunity.
6. **The source round-trips under its reference environment.**
7. **Current state is read late.** Recasting or mutable concept state can change
   realization without relinking the prose.
8. **Vantage and discourse are not concept identity.** They influence how a
   linked concept is realized, not what it refers to.
9. **Story-significant render effects are discoverable.** Arbitrary presentation
   helpers must not secretly mutate canonical story meaning.
10. **Template engines are replaceable.** Jinja may be the first backend; it is
    not the semantic contract.
11. **Generated prose is not story truth.** Graph state and semantic receipts
    remain authoritative; journal fragments preserve the realized experience.
12. **Anonymous-until-met is a proof case, not the architecture.** The same
    mechanism should support aliases, role substitution, mutable traits,
    alternate vantages, localization/revoicing, and richer realization hooks
    without changing its core model.

---

## Non-goals

This design does not require StoryTangl to:

- understand arbitrary English;
- solve unrestricted pronoun coreference;
- bless one NLP library;
- replace authored prose with generated prose;
- make Jinja part of the story ontology;
- rebuild a general natural-language-generation system;
- silently smooth ambiguous or malformed prose;
- infer semantic effects from arbitrary executable template functions.

The goal is narrower: make semantic references in prose optional, explicit when
necessary, conservatively recoverable when convenient, and stable under the
same dynamic story state that already drives the rest of StoryTangl.
