# Prose authoring: voices, names, and introductions

```{storytangl-topic}
:topics: prose
:facets: overview, design
:relation: documents
```

> **Status:** Current authoring guide for the shared mu-block renderer, optional
> concept naming, and runtime exact-name linking. Environment customization is
> explicit; there is no active engine `Voice` class or automatic Voice loader.

## Why these are prose extensions

A story can know which person fills a role without revealing that person's name
to its narrator. The same graph state might be described as "the blonde girl",
"Rin", or some deliberately authored title. That wording is a realization
policy, not a different actor and not necessarily a gameplay mechanic.

Think of three separate inputs:

- **Voice:** how this passage chooses and combines words.
- **Narrator knowledge:** what this viewpoint knows about each actual concept.
- **Speaker:** who is attributed with a particular utterance. A speaker does not
  automatically become the narrator or donate their knowledge to it.

The graph/delta history records semantic state. JOURNAL projects an ordered
account into fragments; Service transports them and clients choose how to display
them. These tools operate at the prose projection boundary, not in client layout
or an alternate content channel. Already emitted journal wording is historical:
introducing someone changes later realization, not earlier fragments.

Worlds adopt naming through their domain package, like optional mechanics. A
vanilla world need not import naming, use special actors, or link its text.
Naming policy and automatic lexical rewriting are separate opt-ins.

## The types that still exist

| Type | Responsibility |
| --- | --- |
| `ProseBlock` | Optional Story block owning an ordered `prose` list and explicit semantic choice labels. |
| `MuBlock` | One authored narrative unit: literal/linked `text`, or an explicit `template`. |
| `DialogMuBlock` | The same unit with a symbolic speaker and full dialog class. |
| `ConceptReference` | A namespace symbol, wording intent, optional introduction, and scalar form parameters. |
| `NamedConcept` | Optional concept-side names, adoption data, and narrator-specific identification. |
| `NamingOperations` | Context-bound provider/policy resolution shared by references, introductions, and labels. |
| `TextRenderSession` | An ephemeral scoped template session, with an explicitly configurable Jinja environment. |

**`ProseBlock` was not retired.** `ProseSegment`, the duplicate authored-unit
model, was replaced by shared `MuBlock`/`DialogMuBlock` values. A block is the
graph-owned container; its mu-blocks are embedded values, not separate graph
entities. Parsing raw callouts and storing authored units use the same vocabulary.

## Adopt the feature in a world

A minimal domain module imports the optional types before compilation and exposes
the naming authority through the existing loader convention:

```python
from tangl.core import BehaviorRegistry
from tangl.prose.naming import NamedActor, NamedLocation, ProseBlock
from tangl.prose.naming import get_authorities as naming_authorities


def get_authorities() -> list[BehaviorRegistry]:
    return naming_authorities()
```

The world's `world.yaml` selects that module with `domain_module`, as in the
`concept_naming_demo` world. A compact script can then say:

```yaml
label: meeting_demo
globals:
  naming_defaults: {NamedActor: concealed, NamedLocation: proper}
actors:
  rin:
    kind: NamedActor
    name: Rin
    anonymous_name: the blonde girl
  nanae:
    kind: NamedActor
    name: Nanae
    anonymous_name: a girl in a red sweater
scenes:
  practice:
    roles:
      host: {actor_ref: rin}
      sister: {actor_ref: nanae}
    blocks:
      start:
        kind: ProseBlock
        locals: {link_prose: true}
        prose:
          - text: "Rin waits. Rin #intro smiles. Rin waves."
```

For a fresh narrator this passage becomes "the blonde girl waits. Rin smiles.
Rin waves." Linking does not automatically capitalize a generated nominal or
infer articles; the deliberately small default preserves authored punctuation.

Class defaults follow the nearest matching provider type in its MRO. An explicit
concept `naming_policy` overrides those defaults; absent a policy, it is `off`.
`concealed` requires usable `anonymous_name` wording rather than leaking a proper
name as fallback. `proper` displays proper wording immediately. `off` does not
perform identification when the standard introduction helper is called.

## Names, forms, and knowledge are different

`NamedActor` and `NamedLocation` compose `NamedConcept` with Story's ordinary
types. The mixin also works on another graph-owned concept, such as a named sword;
it does not require a person schema, Presence, or demographics.

In an adopted world's template:

```jinja
{{ reference(host) }}
{{ reference(host, 'proper') }}
{{ reference(host, 'anonymous') }}
{{ introduce(host) }}
```

These mean, respectively: policy-aware wording; forced proper wording without
disclosure; forced anonymous wording without disclosure; and proper wording plus
an explicit, idempotent identification for the active narrator.

`reference(host, form='formal')` requests a form, not disclosure. An unknown
concealed person can still be anonymous. `reference(host, 'proper', form='formal')`
explicitly forces that wording without introducing anyone. `PersonalNamedActor`
can optionally supply forms from the existing `PersonalName` value; ordinary named
actors, places, and items need no personal-name parser. Worlds may override nominal
selection or ordinary named text-aspect handlers for their own policy.

Knowledge is stored on the **actual provider**, keyed by narrator, not on every
role it fills. Two roles filled by Rin share Rin's identification for that
narrator; recasting a role with Nanae does not transfer it. The standard narrator
key comes from context metadata, defaulting to `_`. Reading references or
`peek_knowledge()` does not create an unknown record. Speaking does not select a
new narrator automatically.

## Three authoring paths, one naming policy

**Portable explicit parts** do not require Jinja or lexical discovery:

```yaml
prose:
  - text: [{ref: host}, " waits."]
  - label: host_role
    dialog_class: npc.excited
    text: ["Hi, I am ", {ref: host, introduce: true}, "."]
  - text: [{ref: host}, " smiles."]
```

`params: {form: formal}` on a reference carries the same scalar form request as
the Python helper. Labels are exact current namespace symbols; `host_role`
resolves its current provider before name, ID, style, or media projection.

**Opted-in source linking** uses `link_prose: true` in the gathered namespace.
World globals can enable it and nearer scene/block locals can override it. It
links narration in `ProseBlock.prose` string text, not every string in the world
and not ordinary `Block.content`. Discovery sees only currently afforded named
concepts in that namespace, including ancestor/world contributions. It does not
scan or provision the whole graph or use a catalog to authorize a reference.

Matching is exact, case-sensitive, longest-first, and bounded: `Ringo` is not
`Rin`. Anonymous descriptions stay literal unless a custom adopter explicitly
provides them. `Rin#intro` and `Rin #intro` identify at that position; unmatched
complete markers and ambiguous mentions fail with source information.
`#introvert` is not a marker. Backslash escapes such as `\Rin #intro` and
`\#intro` preserve literal wording; inline/fenced Markdown code is literal for
all worlds. There is no pronoun/coreference inference.

**Explicit templates** bypass lexical discovery/lowering and call the same
naming operations directly:

```yaml
prose:
  - template: "{{ reference(host) }} waits."
  - template: "{% set _ = introduce(host) %}{{ reference(host) }} waves."
```

Declare Jinja as a requirement of that authoring adapter; it is not the portable
story ontology. A mu-block accepts `text` OR `template`. Templates execute once
through the mu-block path; their generated output is not lexically relinked.
Text units containing Jinja delimiters are opaque to the lexical linker, not
implicitly promoted into templates. Split mixed authoring into ordered units.

Ordinary `Block.content` has a different existing contract: scoped
`text_template` chooses `fstring` by default or `jinja`. Its Jinja path uses bounded
recursive `TextRenderSession.render()`, allowing deliberately generated templates
and detecting cycles/depth exhaustion. Do not confuse that recursive path with a
mu-block's single-pass `template` or assume `text_template` enables lexical linking.

## Dialog and introduction order

Opted-in raw source may use the existing callout parser:

```yaml
prose:
  - text: |
      Rin waits.

      > [!npc.excited] host_role
      > This is my sister, Nanae. Rin #intro stays spoken.

      Nanae #intro smiles. Nanae waves.
```

Spoken names and markers in the callout body stay literal/non-disclosing. The
speaker label is policy-aware but read-only; it does not introduce the speaker.
The narration afterward explicitly identifies Nanae. The full callout class is
preserved; the house convention splits mode and attitude at the first dot.

Ordered mu-blocks prepare speaker metadata **before their own body** runs. An
intentional `introduce(host)` in that body can affect later units without changing
the label already prepared for this utterance. Explicit semantic references and
templates inside structured speech are still intentional author instructions.

Ordinary raw/Jinja block content is evaluated as a whole before dialog composition;
its labels can therefore see end-of-block knowledge. Use ordered mu-blocks when
that distinction matters. Explicit `choice_labels` use the same reference policy
but prohibit semantic introductions; no blanket automatic rewriting of arbitrary
choice strings is implied.

## Escape hatch: one-off world helpers, including groups

The standard path is a convenience, not a restriction on authored wording. Suppose
two unnamed people should be "two girls", then "Rin and a girl in a red sweater",
then "Rin and Nanae". That phrase needs no group entity or group knowledge store.

Add a pure world helper to the gathered namespace. This example deliberately
assumes concealed naming defaults for both people. Add it to the domain module
above, replacing `get_authorities()` with the combined version here:

```python
from tangl.core import BehaviorRegistry
from tangl.prose.naming import NamingOperations, Referent
from tangl.story import get_narrator_key
from tangl.vm.runtime.frame import PhaseCtx

world_prose = BehaviorRegistry(label="meeting_demo.prose")


@world_prose.register(task="gather_ns")
def prose_helpers(*, ctx: PhaseCtx, **_kwargs: object) -> dict[str, object]:
    naming = NamingOperations(ctx)
    narrator = get_narrator_key(ctx)

    def practicing_pair(first: Referent, second: Referent) -> str:
        knowledge = [naming.provider(person).peek_knowledge(narrator)
                     for person in (first, second)]
        if all(state is None or state.state != "IDENTIFIED" for state in knowledge):
            return "two girls"
        return f"{naming.reference(first)} and {naming.reference(second)}"

    return {"practicing_pair": practicing_pair}


def get_authorities() -> list[BehaviorRegistry]:
    return [*naming_authorities(), world_prose]
```

Then author an explicit template:

```yaml
prose:
  - template: "{{ practicing_pair(host, sister) }} practicing."
```

`practicing_pair` is world-defined, not a built-in group API. The helper reads the
actual providers and current narrator, then lets ordinary `reference` choose each
individual name. Its context is local to this render, not a globally captured
story. The helper registration must be reachable through the world's authorities;
a bare module-level `get_ns` function is not automatically a loader hook. Existing
entity namespace contributions can also supply values/helpers through their normal
gathering path. None of these functions needs to be serialized into graph state.

Other legitimate choices are a complete Jinja `if`/`else` expression, an ordinary
world-owned text-aspect handler, or a value computed by UPDATE effects and stored
in existing locals. An UPDATE-computed phrase is an intentional **pre-journal
snapshot**: subsequent JOURNAL introductions do not recompute it. Evaluate at
render time only when within-journal ordering matters. No group framework or
automatic repair of that snapshot is needed.

## Escape hatch: environment helpers and voice policy

"Voice" describes an author/world policy here, not a shipped `Voice` subclass
protocol. Older Voice implementations live in `scratch/discourse`; importing
them is not how a current world enables this feature.

Code that constructs a `TextRenderSession` can explicitly supply its environment:

```python
import jinja2
from tangl.prose import TextRenderSession

environment = jinja2.Environment(undefined=jinja2.StrictUndefined)
environment.globals["join_pair"] = lambda first, second: f"{first} and {second}"
session = TextRenderSession(ctx=ctx, environment=environment)
```

In a world adapter using that session, `join_pair(reference(host), reference(sister))`
combines existing namespace-aware naming operations. Environment helpers supplement
the gathered namespace; they do not replace the cast, narrator context, or concept
knowledge. A context-aware Jinja helper can use `jinja2.pass_context`; pure
formatting helpers need not know about the story at all. Do not capture one
player's context in a shared global environment.

A world-specific Voice/environment wrapper is a possible local authoring tool,
not an engine-wide registration requirement. The stock mu-block renderer creates
its own default session: merely defining an environment subclass does **not**
install it there. Use a world-owned realization handler/adapter when explicit
environment customization is needed. Namespace helpers are the simplest option
for ordinary mu-block templates because they already receive that scoped namespace.

Document any required helper names, inputs, template backend, and evaluation
timing alongside the world. Do not expect portable linked references to reconstruct
arbitrary Python/Jinja helper semantics or require every author to use the same
convenience syntax.

## Durability, boundaries, and examples

Authored mu-blocks and symbolic references persist with their owning block through
`unstructure()`/`structure()`. Mutable embedded fields use the existing explicit
`include`/`unstructurable` markers and declare their supported concrete variants;
resolved text and helper closures are not written back into authored source.
Successful save/JSON restore, patch replay, and explicit rollback retain narrator
knowledge and historical fragments. Fresh-process restoration bootstraps the world
and its authorities normally before opening a saved session.

Read-only projections must not introduce anyone or mutate gameplay state.
Deliberate introductions use the phase-aware operation during UPDATE, FINALIZE,
or actual committed JOURNAL realization. Unexpected exceptions propagate under
the existing non-atomic traversal contract; these features promise no selective
knowledge undo or safe retry of a partially failed traversal.

Stable role-owned spellings across recasting, automatic anonymous-description
generation, richer narrator/formality models, and generalized group realization
are not defaults. Current runtime discovery uses the current providers' explicit
spellings. Destination-owned choice-text rendering is a separate integration
tracked by #558, not a reason to evaluate arrivals while describing a choice.

For a working world and implementation contracts, see:

- `worlds/concept_naming_demo`: executable actor/place/item, dialog, template,
  runtime-linking, and CLI examples.
- `engine/src/tangl/prose/PROSE_DESIGN.md`: projection, ownership, and naming policy.
- [Concept-linked prose](CONCEPT_LINKED_PROSE.md): rationale and deferred directions.
- [Journal composition](JOURNAL_COMPOSE_CONTRACT.md): output transformation boundary.
- `engine/tests/prose/test_naming.py`, `test_named_concept.py`, and `test_linking.py`:
  narrator isolation, recasting, disclosure order, restore/replay, and pure discovery.
