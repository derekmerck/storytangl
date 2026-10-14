# Optional prose extensions

Status: #555 naming behavior retained; the approved #534 mu-block projection
replacement's foundation slice is implemented. Generic NamedConcept and runtime
scoped exact adoption are subsequent slices. #557's compile-time-only linker
remains an open, unmerged salvage reference, not the runtime authority.

Rendering sessions and dialog micro-blocks are existing realization helpers.
`naming` is an optional Story extension adopted by world domains before
compilation through their existing class registry and authority chain. Story
does not import this module to activate it. It installs no alternate registry
or fragment hierarchy; its behaviors use normal Story/VM dispatch tasks.

`ConceptReference` is a small value describing a namespace referent, wording
intent, and introduction. `MuBlock` and its existing `DialogMuBlock` specialization
are the shared authored vocabulary for ordered bodies and symbolic speakers.
The authoritative ownership boundary is
[Registry-owned entities and owner-local embedded values](../../../../ARCHITECTURE.md#registry-owned-entities-and-owner-local-embedded-values).
Mu-blocks are non-graph authored values, not Entities or graph children. They have
no UID; `source_id` names a donating entity. The block is their owner, not a
hierarchical parent. Render context supplies access without stored owner fields
or an additional manager. Reused embedded values do not promise shared identity
after restoration; actual entity references resolve through the registry.
They contain no live graph pointers. Embedded ownership opts into the existing
constructor-form field recursion; transient parsing uses the very same values.
Concepts store proper
and anonymous wording. Knowledge belongs to the current provider and narrator.

`NamingOperations.reference` is pure and uses existing named-text-aspect
dispatch; `introduce` writes concept-local knowledge in UPDATE/FINALIZE effects
or explicit committed JOURNAL realization. Explicit
Python Jinja templates invoke the same operations once. Display labels prohibit
introductions. Per-concept override/opt-out precedes the nearest world-supplied
kind default; absent policy means off. Literal text and graph identity are stable.

Successful save/restore, patch replay, and explicit rollback are the durability
contract. Unexpected exceptions propagate under existing non-atomic traversal
semantics; the #534 scope decision excludes general failure recovery. The
compiled-world FINALIZE probe and implications are recorded in
`docs/src/design/story/CONCEPT_LINKED_PROSE.md`.

The downstream witness is `worlds/concept_naming_demo`, exercised by
`engine/tests/prose/test_naming.py`, including JSON-backed ServiceManager flow.
Reopening a JSON manager in the same process retains live World/type/authority
registration. The true subprocess witness calls normal `open_world()` bootstrap
before opening the saved session. Soft reset/hot reload is separate work.

Ordinary raw/Jinja dialog retains whole-block evaluation before composition
parses and binds speakers. Adopted naming policies supply a non-disclosing
`reference_auto` text-aspect read through the injected label resolver at that
composition point, so labels see current/end-of-block knowledge. Absent a naming
adapter, vanilla fallback is unchanged. Explicit raw template calls remain
allowed, but they do not promise per-utterance pre-body labels. The checkpoint
is resolved under this bounded scope: use authored mu-blocks for label-before-body
ordering and once-only body evaluation. No spoken-name rewriting or narrator
inference is added.
Attributed dialog tone/avatar and presentation-class work remains #454/#457.

## Projection foundation and supported paths

The approved pipeline is authored content -> authored mu-blocks -> scoped
symbolic references -> ordered realization -> existing journal fragments ->
existing composition/transport. Parsing, optional preprocessing/linking, and
custom realization tools are separable. Compilation may lint or pre-parse; a
runtime tool may discover links from its current namespace. A compile-time
catalog does not authorize runtime references, and whole-catalog lint is separate.
Stages may be identity/no-op when no adapter is adopted. Later composition may
filter, combine, layer, or ignore output; there is no universal result union,
renderer registry, extra VM phase, or alternate fragment hierarchy.

`MuBlock` owns authored literal text or ordered literal/ConceptReference parts,
or an explicit template. Text and template are mutually exclusive, including
explicit empty text. `DialogMuBlock` adds the full callout class and symbolic
speaker `label`; mode and attitude are pure projections of that class. Existing
style fields and source provenance are preserved. `ProseBlock.prose` is only an
optional graph-owned container of these values, not another micro-block schema.
Naming defaults do not automatically migrate raw worlds to this adapter.

`DialogHandler.parse` uses the existing callout grammar and returns authored
structure only. It accepts no namespace and never fetches names, styles/media,
or knowledge. `DialogHandler.render` is the shared ordered path for parsed and
stored input. `prepare_fragment` prepares fresh metadata before the handler fills
the body; it is not complete realization. The naming adapter supplies its
speaker/name/part resolvers. Explicit symbolic speakers require an exact current
namespace binding; Role/Setting values dereference their current provider before
name, ID, style and media projection, per unit rather than frozen for a block.
The original symbolic key remains attribution, while all provider metadata belongs
to the actor/location. Missing or unbound semantic speakers fail before their
bodies run. Ordinary callout display-label fallback remains unchanged without
the strict resolver. Speaker metadata is projected before its body evaluates.
Explicit templates execute once, with generated wording treated as output.
Literal body names and #intro markers are never inferred disclosures.

There is no mutating bind on authored objects and no bound-output fields on them.
Names, IDs, styles, media, and final text live in fresh fragments; a value can be
rendered against another namespace without retaining a previous binding.
`prose` and authored mutable text/style fields use ordinary include/constructor-
recursion markers, not custom serializers. Constructor and actual JSON-backed
restore retain authored classes/parts and reproject bindings using the normally
bootstrapped world authorities. No new foundational persistence decision was
needed. #555 recast, replay, rollback, and cold-restore witnesses remain required.

Flat JSON recovery uses the concrete supported variants declared in the owning
field. A custom DialogMuBlock subtype is supported when the owner's `prose`
annotation explicitly includes it and retains `include=True` and
`unstructurable=True`. The former retains nondefault in-place edits; the latter
requests constructor-form recursion. The positive custom owner-graph JSON witness
retains the subtype, its authored fields, and its preparation behavior. No global
embedded-class registry, Entity-based embedding inference, broad coercion, or
pickle-style alias memoization is provided. Owner back-pointers/caches, if used
by other embedded types, stay excluded and are rebound normally; mu-blocks do
not need them.

Slice 1 deliberately does not implement NamedConcept, automatic runtime adoption,
inherited-name catalogs, binding-owned spelling aliases, lexical #intro parsing,
NLP, hot reload, or failure recovery. Slice 3 may salvage #557's exact-boundary,
complete-marker, escape, ambiguity, and one-way literal-description witnesses;
its compile-time catalog gate and separate authored segment model are replaced.
