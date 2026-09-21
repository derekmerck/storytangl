# Episode-to-Syuzhet Rendering

```{storytangl-topic}
:topics: prose
:facets: overview, design
:relation: defines
:related: journal, observation, presence, media, lang
```

> **Status:** Current rendering contract with explicitly marked extension points
> **Scope:** The episode-to-syuzhet transformation assembled across namespace
> gathering, typed presentation adapters, JOURNAL emission and composition,
> media provisioning, service delivery, and client presentation. “Rendering”
> here names that transformation space, not one additional VM phase.

**Implementation status:** the text and fragment floor is landed.
``TextRenderSession`` performs bounded recursive Jinja rendering against a
``PhaseCtx`` namespace and carries ephemeral discourse state.
``tangl.story.presentation.render_text_as(...)`` selects one named textual
aspect through Story dispatch; explicit authored content is a complete
replacement. Presence and Credentials register their own adapters, and the
credentials vertical proves recursive person, document, packet, and encounter
text without moving validity or disposition authority into presentation.

Story JOURNAL handlers emit ordered typed fragments for content, media, and
choices. The optional ``compose_journal`` fold transforms that merged batch
before service projection. Credentials additionally proves the non-text path:
a presentation-safe card projection requests portrait and printable-text media,
provisioning resolves those requests into a composed ``MediaRIT``, and JOURNAL
emits an associated ``MediaFragment`` beside the ordinary text and piece floor.

There is no universal persistent ``ContentRequest`` or renderer-result union.
Observation/vantage policy, broad revoicing, richer structural syuzhet adapters,
and media catalog strategy remain proposals or separate follow-ups.

## Purpose

The rendering phase transforms the currently invoked episode—its block, story
state, entities, mechanics, and relationships—into a realized syuzhet:
narrative, dialog, visual descriptions, journal fragments, media requirements,
and other presentation products.

The engine does not require one universal renderer. It supplies the bounded
namespace, stable referents, lifecycle timing, dispatch, and provenance that
specialized content adapters need.

```text
episode + phase-assembled namespace
    -> typed presentation adapter
    -> narrative fragment or downstream resource specification
    -> JOURNAL fragment stream
    -> ordered composition
    -> service delivery
    -> client presentation
```

Narrative and dialog enter the JOURNAL as fragments. A downstream resource
specification such as ``MediaSpec`` first resolves to a resource and then
re-enters the same narrative output surface as ``MediaFragment``. It is not a
parallel client-delivery channel.

## Projection-to-realization pipeline

The path from story state to a user's experience is a small dataflow pipeline,
not one rendering operation:

```text
graph checkpoints and deltas
    -> JOURNAL projection and composition
    -> ordered journal registry
    -> service envelope and transport
    -> client display and interaction
```

The graph history is the replayable semantic source: it records accepted
actions and their effects on the parameterized story shape. JOURNAL samples
that evolving shape at the current cursor and linearizes the disclosed result.
Its handlers may emit a coarse episode packet, a prose block, attributed
utterances, choices, media requirements, or a procedural specification. The
journal registry stores that ordered projection; it is neither a second story
graph nor a record of pixels, HTML, terminal control sequences, generated
speech, or other final client output.

Service packages and transcribes the stored projection, adds lifecycle and
transport metadata, and dereferences resources where its contract requires it.
It must not invent narrative meaning or make a renderer-specific realization
authoritative. A client maps the fragment vocabulary into its own display and
input facilities. Reference clients should realize the supported public
vocabulary completely, with accessible fallbacks; specialized clients may
discard prose, enrich packets with maps, TTS, images, or generated text, or
present the same choices differently. Only actions accepted by the backend and
their resulting state changes return to semantic authority. Ephemeral client
realizations need not be negotiated back into the journal.

Two independent choices therefore remain open:

- **Projection resolution** controls how densely JOURNAL samples and identifies
  the episode: one gloss, one block, individual utterances, annotated spans, or
  another typed packet. A fragment boundary is warranted by independent
  semantic or interactive identity, provenance, ordering, replay, update, or
  deletion—not merely by a styling boundary.
- **Realization binding** controls how a projection is represented or rendered:
  renderer-neutral JSON, bounded Markdown or attributed text, classed HTML,
  Rich spans, ANSI, native widgets, audio, or another adapter-local form.
  Styling and themes remain advisory mappings over semantic presentation
  tokens rather than backend-mandated final appearance.

These axes must not collapse into one closed render-profile taxonomy. New
projection families may preserve, aggregate, refine, or interpolate the source,
but must keep stable identity, provenance, and correspondence where those are
observable; make lossy transformations explicit; preserve essential
interaction or fail clearly; and default unsupported decoration to an identity
or documented fallback. Three replay claims stay distinct: graph replay
reconstructs causal state, journal replay re-emits the stored projection, and
exact rendition replay would require an optional archival contract that is not
currently promised.

## The rendering namespace

Before rendering, the phase pipeline assembles the namespace valid for this
step. It may contain:

- the current block, scene, encounter, and selected action;
- graph-owned actors, objects, locations, and relationships;
- mechanic state such as outfits, credential packets, vehicles, or markings;
- world-, scenario-, block-type-, and block-instance content contributions;
- narrator knowledge, discourse focus, locale, and ephemeral render-session
  state;
- scoped catalogs, templates, and adapter hooks.

The namespace is bounded by the current story and world authorities. A renderer
must not search process-global state or reach into unrelated worlds.

## Content requests and adapters

The landed text seam identifies a target and named aspect:

```text
target: person
aspect: presence_description

target: packet
aspect: inspection_description

target: event
aspect: narrative

target: speaker
aspect: dialog_line
```

Other adapter families retain their own typed contracts rather than converging
on an untyped universal request or result:

```python
render_text_as(...) -> str
JOURNAL handlers -> list[BaseFragment]
media projection/adaptation -> MediaSpec
media provisioning -> MediaRIT
JOURNAL media handler -> MediaFragment
```

An author-facing `render_as(...)` may provide pleasant common vocabulary, but it
delegates to the appropriate typed adapter.

Adapters share namespace access, referents, recursion, and provenance. They do
not need to share a template language, traversal algorithm, intermediate
representation, or output type.

## Scaling authored content

Any adapter may support several levels of pre-baking:

1. Use a complete authored realization.
2. Select among available authored realizations.
3. Fill a template from the current namespace.
4. Compose templates or content products recursively.
5. Generate or transform content procedurally.
6. Fall back to a simpler realization.

A whole authored description can replace an assembled description, while
lower-level overrides remain possible when assembly is desired.

## Rejinja as a humane narrative default

Rejinja is a simple textual implementation of this pattern. It recursively
evaluates returned templates in the same rendering environment until the
content bottoms out.

A room description can invoke its atmosphere, space, and occupants. Each
occupant can select a known or anonymous nominal and delegate appearance to
their look, outfit, expression, and visible markings.

```jinja
{{ room.feel() }}

{% for person in room.people %}
    {{ person | render_as("presence_description") }}
{% endfor %}
```

The text adapter may maintain a mutable `DiscourseContext` within the namespace
for:

- the most recently mentioned subject;
- bare pronoun resolution;
- narrator familiarity;
- discourse focus;
- tense, point of view, and locale;
- state carried between consecutively rendered segments.

That is renderer-session state, not mechanic state. Persistent narrator
knowledge can be promoted explicitly when required.

Rejinja is a friendly authoring tool, not the blessed representation for all
content. A different runtime may use another template engine or no template
engine at all. Portability should be defined by behavioral fixtures, not exact
Jinja internals.

## Other valid adapters

The same rendering contract supports fundamentally different implementations:

- A graph visitor selects content nodes and assembles ordered syuzhet fragments.
- An NLP adapter operates on a parsed document tree, replacing referents and
  changing point of view, tense, or conjugation before relinearizing prose.
- A media adapter assembles a structured `MediaSpec`.
- A voice adapter selects recorded lines or produces a TTS specification.
- An animation adapter emits a timeline, scene graph, or backend-specific plan.

Outputs can feed later adapters:

```text
story state
    -> visual description
    -> image specification
    -> selected/generated RIT
    -> MediaFragment
```

```text
dialog intent
    -> realized line
    -> voice-line requirement
    -> recording or TTS result
    -> audio fragment
```

Media adapters should independently visit the same semantic objects; they
should not parse flattened narrative prose to reconstruct them.

## Mechanics versus presentation

Mechanics supply semantic truth:

- facts and traits;
- durable identities and references;
- component relationships;
- visible or discoverable state;
- optional authored content hooks.

Adapters decide presentation:

- grammar and syntax;
- familiarity and nominal selection;
- point of view and pronouns;
- visibility and suppression;
- templates, styles, and output formats.

For credentials, subject UUIDs determine holder identity. A narrative renderer
may describe the bearer and visible photograph, but it must not infer or reveal
`wrong holder`, `invalid`, or the expected disposition. Those remain mechanic
interpretations exposed only through the appropriate interaction.

## Credentials as a recursive-rendering proof

The entire encounter can begin with two small block fragments:

```jinja
A {{ person | render_as("presence_description") }} steps up to the window.
```

```jinja
They lay their documents out for inspection:
{{ packet | render_as("inspection_description") }}
```

The adapter recursively follows:

```text
packet
  -> documents
    -> visible document parts
      -> portrait
        -> referenced bearer
          -> look
            -> hair
            -> outfit
            -> expression
            -> visible markings
```

Authors can replace the whole encounter text, the packet description, one
document, one document part, or one appearance component without changing the
block structure or mechanics.

## Static and dynamic materialization

Content availability is an independent axis:

| Class | Build or authoring work | Runtime work |
| --- | --- | --- |
| Static | Finished artifact already exists | Return it |
| Static-selected | Several finished alternatives exist | Select one |
| Generated-static-selected | Procedural space is populated during compilation or curation | Select one |
| Generated-dynamic | Content depends on this playthrough's live namespace | Reuse or create it |

A finite dynamic space can be converted into a selectable space by enumerating
its parameter cross-product:

```text
gender x glasses x hair x skin x reference face
    -> synthetic namespaces
    -> adapted portrait specifications
    -> generated and reviewed artifacts
    -> tagged RIT inventory
```

A world can substitute another compatible inventory—ink-punk, paper-doll,
illustrated, photographic—to reskin the entire experience. Catalog
compatibility depends on stable semantic selector dimensions, not filenames or
prompt text.

The caller still asks only for the appropriate RIT. The resolver decides
whether to return a direct artifact, select an existing one, reuse a non-stale
cached result, invoke a forge, or return a pending or fallback result.

## Current boundary and next proofs

The current framework deliberately stops short of blessing one universal
content IR. Text presentation, JOURNAL composition, and media provisioning use
different typed products while sharing the gathered namespace, stable
referents, dispatch authorities, provenance, and final fragment stream.

Generic dispatch ``PIPE`` remains a separate deferred pruning question. This
contract neither blesses nor removes it: the landed rendering path uses named
namespace enrichment and an explicit ordered fragment fold, while other
consumers may still justify pipe-style aggregation independently.

Future work should be driven by a concrete second consumer:

1. A structural syuzhet adapter may prove graph or slot-based composition beside
   recursive text without replacing ``compose_journal``.
2. Observation/vantage may graduate when a world needs disclosure policy that
   cannot be expressed by current scoped namespace and presentation adapters.
3. Revoicing may graduate when exact replay, localization, or point-of-view
   conversion supplies behavioral fixtures.
4. Richer media selection and composition remain media concerns; they consume
   semantic projections rather than becoming story truth.

The north star remains a flexible episode-to-syuzhet transformation space.
Credentials and Presence are demanding examples of it, not owners of bespoke
presentation systems.

## Related contracts

- [Mechanics Families](MECHANICS_FAMILIES.md)
- [Journal Compose Contract](JOURNAL_COMPOSE_CONTRACT.md)
- [Presence/Prose Contract Spike](PRESENCE_PROSE_CONTRACT.md)
- [Generative Media Design](../GENERATIVE_MEDIA_DESIGN.md)
- [Fragment Stream Contract](../service/FRAGMENT_STREAM_CONTRACT.md)
- [Service Architecture](../service/SERVICE_DESIGN.md)
