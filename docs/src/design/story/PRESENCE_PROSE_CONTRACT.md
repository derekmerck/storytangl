Presence/Prose Contract Spike
=============================

**Status:** 🟡 CONTRACT SPIKE / PARTIAL STORY-RUNTIME SCAFFOLD  
**Last Updated:** March 2026  
**Scope:** story concept scaffolding plus contract tests; active block rendering remains unchanged

## Why This Spike Exists

`presence/look` is not just an appearance mechanic. It sits near a larger
future contract for prose-facing concept presentation:

- how concepts are named or described in rendered text,
- how focalization changes those references over time,
- how character-specific speech resolves from intent,
- and how visual or audio presence enriches prose and media without making the
  data model own those rendering concerns.

This spike exists to name those contracts and prove them with toy tests before
changing the active story render path.

## Current v38 Baseline

The live engine already has some of the right seams, but not the full prose
subsystem yet.

- Story JOURNAL handlers receive a real `PhaseCtx`.
- `PhaseCtx` is ephemeral and primarily used for scoped namespace gathering via
  `ctx.get_ns(node)`.
- Persistent session state lives on `Ledger`.
- `render_block_content()` currently renders block text through namespace
  gathering plus `str.format_map`, not Jinja or concept-driven prose filters.
- There is no active `tangl.prose` package yet.

That split still matters, but the current direction is now more specific:
narrator-facing epistemic bookkeeping lives on the story concepts it is about,
while the render environment remains ephemeral and is rebuilt per pass.

## Target Contract

### 1. Presentable

The minimum prose-facing protocol should stay small:

```python
@runtime_checkable
class Presentable(Protocol):
    def get_label(self) -> str: ...
    def get_nominal(
        self,
        *,
        familiarity: Familiarity = Familiarity.ANONYMOUS,
        det: DeterminativeType = DeterminativeType.DEFINITE,
    ) -> str: ...
    def get_pronoun(self, pt: PT) -> str: ...
```

This is the prose participation floor. Anything richer remains optional.

### 2. Narrative State Placement

The current implementation direction is:

- `EntityKnowledge`
  - persistent with the graph
  - stored directly on the story concept it is knowledge of
  - flat and diff-friendly: `state`, `nominal_handle`,
    `first_description`, `identification_source`
- `HasNarratorKnowledge`
  - mixin applied to story concept carriers such as `Actor`, `Location`,
    `Role`, and `Setting`
  - stores `dict[str, EntityKnowledge]` keyed by narrator key
- `DiscourseContext`
  - ephemeral
  - built per render or projection pass
  - tracks focus and other transient discourse decisions
  - resolves narrator selection from `ctx.get_meta()["narrator_key"]`
    when available, otherwise `"_"`

This keeps `Ledger` unchanged. Narrator knowledge is treated as concept-level
episodic bookkeeping, while the render environment remains per-pass state.

### 3. Speaker Profiles and Speech Acts

Speech is treated as a sparse override layer on top of language banks.

- `SpeakerProfile` is derived from entity fields like `native_language`,
  `register`, and `vocabulary`.
- Intent resolution falls back in this order:
  - per-entity override,
  - language bank,
  - English bank,
  - literal intent key.

This keeps character-specific mannerism lightweight while still making speech
semantically addressable.

### 4. Presence as an Adapter Seam

Presence is an enrichment layer, not the prose engine itself.

- `Look`, `OutfitManager`, and `Ornamentation` remain data-facing mechanics
  surfaces.
- A future `HasPresence` facade delegates to prose and media adapters.
- `Look` should not own narrative policy, focalization, or media backend logic.
- Prose and media consume presence data through adapter seams such as
  `describe_presence()` and `from_presence()`.

This keeps imports one-way:

- `mechanics.presence` should not depend on `tangl.prose`,
- `mechanics.presence` should not depend on `tangl.media` internals,
- adapter layers consume presence data, not the other way around.

## Compatibility with Current Runtime

The migration path should stay parallel and opt-in first.

- `get_ns()` remains the compatibility bridge.
  Concepts and facets continue to publish symbols into render scope through the
  namespace system.
- Role and setting namespace publication remain backward-compatible.
  `villain` still resolves to the provider actor, while additive aliases such
  as `villain_role`, `place_setting`, `role_edges`, and `setting_edges`
  expose role/setting carriers for separate epistemic state.
- The current `format_map` path remains the live renderer.
- A future Jinja-based prose renderer should sit beside it first, prove itself,
  and only replace it once it is a clear superset.
- `PhaseCtx` metadata already provides the first-pass narrator selection bridge
  through `narrator_key`; no ledger schema change is required.

## Toy Spike Proof

This spike is backed by toy tests rather than active runtime scaffolding.

The proof should demonstrate:

- anonymous versus named reference via concept-local `EntityKnowledge` and
  `meet()`,
- discourse focus driving pronoun resolution,
- speech-intent fallback through `SpeakerProfile`,
- presence-aware prose and media adaptation without changing the base
  `Presentable` contract,
- narrator-key isolation via `ctx.get_meta()["narrator_key"]`,
- additive role/setting aliases preserving actor-versus-role knowledge
  distinction,
- and the current engine truth that live story rendering is still
  `PhaseCtx.get_ns()` plus `format_map`.

These tests are intentionally self-contained. They prove the contract shape
without claiming that the full prose subsystem already exists.

## Forward Integration

The current first pass now includes:

1. Story concept carriers expose `EntityKnowledge` through
   `HasNarratorKnowledge`.
2. Role and setting namespace publication exposes additive aliases for
   role-level and setting-level knowledge.
3. Contract tests prove narrator-key selection through context metadata, while
   active block rendering remains unchanged.

If this grows beyond concept-local bookkeeping later, the next phase should
add a real prose renderer entry point in parallel with the current block
content handler before considering broader session-level narrative state.

Until then, the engine should keep treating this as a design target proven by
tests, not as an active published runtime subsystem.
