# Specialized Projections of a Semantic World

> **Status:** Architectural design principle, with distinct existing examples
> and explicitly proposed consumers. This is **not** a new shared adapter API,
> codec registry, phase, or claim that all the examples below already work.
>
> **Related:** [Narrative control](NARRATIVE_CONTROL.md),
> [episode-to-syuzhet rendering](EPISODE_SYUZHET_RENDERING.md),
> [generative media](../GENERATIVE_MEDIA_DESIGN.md), and
> [World Designs](../../world-designs/index.rst).

## Principle

**A StoryTangl world can be projected into specialized representations for
different purposes without making those representations its ontology.**
The world owns its modeled entities, relationships, state, and consequences.
The projection selects task-relevant semantics and supplements them with
target-specific annotations where needed. Its consumer may be a reader, an
author, a validator, a renderer, a generator, or a specialized tool.

This is not limited to formal solvers, and it does not require the world to
be expressed initially in StoryTangl classes. Foreign source can be
*lowered into* the supported world vocabulary; a world can be *exported to*
another language for a specific computation; generated artifacts and diagnostics
can inform revisions to the same authored world.

For example, annotating a world for a passage-based presentation target might
permit a Twee/Twine projection. Annotating its actors and dialogue for speech
could permit generation through a TTS backend such as Chatterbox. Annotating
the relevant operators, resources, goals, and analysis scope might permit an
ASP/Clingo projection for satisfiability or plan search. These are related
in **semantic intent and provenance**, not necessarily identical interfaces.

## Different targets, different questions

| Target / use | What is projected | Consumer and present status |
| --- | --- | --- |
| Twee/Twine | A bounded passage/link representation | **Implemented subset:** the [Twine codec](https://github.com/derekmerck/storytangl/blob/main/engine/src/tangl/loaders/codecs/twine.py) decodes supported Twee source and strictly exports a limited zero-loss subset. Not a general SugarCube runtime or full round-trip for arbitrary macros. |
| Client presentation (CLI, pygame, Ren'Py) | Ordinary choices, JOURNAL fragments, supported staging and interaction hints | **Existing client/adaptation paths** with differing presentation floors; none acquires authority over story causality by rendering it. |
| Chatterbox or another TTS system | Annotated utterances, speaker identity, voice/style guidance, timing or resource requests | **Potential generation consumer.** StoryTangl's media/resource lifecycle provides related precedent, but this note does not claim a shipped Chatterbox adapter or universal spoken-dialogue exporter. |
| ASP/Clingo | A supported abstraction of state, actions, resources, triggers, and goals | **Partial precedent:** the archived [apartment POC](../../notes/research/formal_solver_poc/index.md) is hand-authored ASP; [One Red Paperclip](https://github.com/derekmerck/storytangl/blob/main/worlds/red_paperclip/README.md) emits compatible ASP and validates a solver plan through an ordinary Ledger. A general generated analysis contract remains [#396](https://github.com/derekmerck/storytangl/issues/396) work. |
| Diagrams and structural reports | Topology, dependencies, provenance, or analysis results | **Representation-dependent** authoring/inspection artifacts, not independent state authority. |

The author-facing versus reader-facing distinction describes **who uses the
result**, not a fundamental split in the projection model. One target might
support either audience, and a single world can support several targets.

## Fidelity and return paths

A projection need only preserve the semantics relevant to its task, but must
state **what it preserved and what it did not**. A solver may legitimately omit
dialogue and images while modeling resource and event dependencies accurately.
A voice generator may preserve words and speaker attribution while making no
claim about whether a questline is achievable.

Preserve, as appropriate to the target:

- source and stable referent provenance, including the modeled events,
  utterances, actions, or constraints;
- annotation/profile and analysis scope, with explicit unknown or
  unrepresented semantics;
- a result artifact, witness, counterexample, diagnostic, or generated media
  resource attributable to that source;
- a validation path proportionate to the claim (for example, checking a
  solver-produced action trace against normal Ledger transitions).

**Export is not automatically invertible.** A source codec may decode and
encode a defined subset. A media generator may return an audio resource.
A solver may return a witness path or a reason a proposed path cannot be
established. Bringing those results *back* is an authoring or presentation
workflow, not proof that the foreign representation reconstructs the entire
world.

In particular, solver conclusions are sound only for the represented
transition subset and declared horizon/completeness scope. The settled
StoryTangl runtime remains the semantic oracle for actual play. A failed
model search does not automatically revoke a choice, and a generated voice
does not change who spoke or what happened.

## Bidirectional authoring without a parallel world

The same idea supports a creative loop:

```text
authored text or canonical world
  -> annotated symbolic / presentation projection
  -> external solver, editor, renderer, or generator
  -> provenance-linked findings or artifacts
  -> revise world or authored material
  -> validate / realize again
```

For example, an author might recover a causal spine from a short linear
story, export a constrained model, find where new scenes can safely rejoin
or where an inserted choice requires downstream consequences, and revise
the story accordingly. Or they might ask which tenant questlines remain
achievable in a cozy commune, use the diagnostic to repair an accidental
soft lock, and then generate dialogue voice-over for the revised scenes.

Those are separate *uses* of specialized projection. They do not require a
generic solver VM, an ASP source language for the whole engine, or a shared
Chatterbox/Twine/Clingo plugin superclass. Introduce common code only after
multiple concrete consumers expose the same necessary contract.

See {ref}`the Apartment Commune <wd-apartment-commune>`
and {ref}`Causal Spine and Narrative Grafting <wd-causal-spine>`
for the narrative research examples, and
[#210](https://github.com/derekmerck/storytangl/issues/210) for the
bounded, human-assisted reconstruction experiment.
