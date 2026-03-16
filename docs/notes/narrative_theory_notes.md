# Legacy Narratology Reference

## Purpose

Capture the recurring theoretical framing that guided earlier iterations so we can translate those ideas into documentation and experiential goals without losing the technical focus of the new architecture.

## Key theoretical threads

- **Tangled feature space** – prior notes describe narrative design as exploring a superposition of interdependent features, with traversal collapsing the space into a stable measurement that becomes the playable lane.【F:scratch/overviews/notes_v34.md†L100-L176】
- **Cross-domain inspirations** – the same notes tie StoryTangl to Bayesian inference, constraint solving, package resolution, compiler IRs, and quantum collapse, highlighting how deterministic yet replayable execution should feel.【F:scratch/overviews/notes_v34.md†L108-L115】
- **Navigation as a separable role** – older notes repeatedly treat the
  "guide" or traversal-driving role as something that can be filled by a
  player, a script, a test harness, or another system, rather than something
  fused to authorship or presentation. That idea naturally generalizes to
  multiple concurrent lanes sharing one story world while exposing different
  perspectives or decision policies.

## Implications for the modern engine

- The VM phase bus reflects the "observation collapses possibility" framing: `ResolutionPhase` enumerates ordered, auditable passes that gather context, realize dependencies, and emit a journal, echoing the theoretical requirement for deterministic yet revisitable progression.【F:engine/src/tangl/vm/frame.py†L23-L140】
- `Context` and layered behavior registries provide the perspective shifts (global → system → local) discussed in the theory docs, ensuring that observation is always grounded in the correct namespace hierarchy.【F:scratch/overviews/notes_v34.md†L189-L196】【F:engine/src/tangl/vm/context.py†L1-L147】【F:engine/src/tangl/core/behavior/behavior_registry.py†L1-L189】
- The current creator / navigator / presenter split in the philosophy docs is
  the modern expression of that guide-role idea. It gives StoryTangl a clean
  place to talk about future multi-lane stories without conflating "who decides
  the next move" with "who sees the resulting syuzhet" or "who authored the
  fabula."
