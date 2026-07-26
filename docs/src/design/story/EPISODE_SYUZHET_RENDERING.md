# Episode-to-Syuzhet Rendering

> **Status:** Active design reference
> **Scope:** The rendering phase that transforms an invoked episode and its
> current namespace into narrative, dialog, fragments, presentation hints, and
> downstream content requirements.

**Implementation status:** Phase 10.1 provides the text-only floor:
``TextRenderSession`` renders bounded recursive Jinja text against a
``PhaseCtx`` namespace and carries ephemeral discourse state. It is not yet a
general content request or JOURNAL adapter. Phase 11 adds the text-specific
``tangl.story.presentation.render_text_as(...)`` invocation seam: it selects a
``str`` source through ``story_dispatch``, exposes that resolver to recursive
text templates, and ships replaceable presence defaults. It remains separate
from fragment and media products.

## Purpose

The rendering phase transforms the currently invoked episode—its block, story
state, entities, mechanics, and relationships—into a realized syuzhet:
narrative, dialog, visual descriptions, journal fragments, media requirements,
and other presentation products.

The engine does not require one universal renderer. It supplies the bounded
namespace, stable referents, lifecycle timing, dispatch, and provenance that
specialized content adapters need.

```text
episode + phase-assembled namespace + presentation request
    -> content adapter
    -> typed content product
    -> journal or another downstream adapter
```

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

A request identifies a target and presentation role:

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

Different adapters should retain typed results rather than converge on an
untyped universal result:

```python
render_text(...) -> str
render_fragments(...) -> list[BaseFragment]
adapt_media_spec(...) -> MediaSpec
resolve_media(...) -> MediaRIT
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

## Near-term implementation implication

The next slice should remain narrative-focused:

1. Establish the smallest typed content-request and adapter-invocation seam
   using `PhaseCtx` and existing dispatch.
2. Exercise literal, templated, and recursively composed narrative.
3. Prove one structural journal/syuzhet adapter alongside Rejinja so Jinja does
   not become the universal contract.
4. Render a simple presence manager, then an assembled `HasLook`.
5. Render one credential document, then a multi-document packet.
6. Preserve source and entity attribution in final journal fragments.
7. Defer actual media selection, generation, SVG or raster concerns, and forge
   overhaul.

The north star is a flexible episode-to-syuzhet transformation space.
Credentials and presence are demanding examples of it, not owners of bespoke
presentation systems.

## Related contracts

- [Mechanics Families](MECHANICS_FAMILIES.md)
- [Journal Compose Contract](JOURNAL_COMPOSE_CONTRACT.md)
- [Presence/Prose Contract Spike](PRESENCE_PROSE_CONTRACT.md)
- [Generative Media Design](../GENERATIVE_MEDIA_DESIGN.md)
