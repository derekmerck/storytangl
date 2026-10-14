# Optional prose extensions

Status: #555 naming behavior retained; the approved #534 mu-block projection
replacement's foundation, generic NamedConcept and bounded runtime scoped exact
adoption slices are implemented. #557's compile-time-only linker
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

Runtime adoption is limited to opted-in ProseBlock source as detailed below.
Binding-owned stable spellings, catalogs, NLP, hot reload and failure recovery
remain deferred. #557's lexical witnesses informed this bounded scanner, not its
compile-time catalog gate, separate segment type or persistence machinery.

## Generic named concepts (slice 2)

`NamedConcept` composes the existing `HasNarratorKnowledge` with a minimal name,
anonymous wording, explicit proper forms/aliases and a policy override. Compose
it with a graph-owned Entity/Node; it is not an embedded manager. `NamedActor` and
`NamedLocation` compose the same contract with Story's existing types. A named
sword/landmark needs no Actor/Location schema, Presence, demographics or person
parsing. `Selector(has_kind=NamedConcept)` identifies adopted graph members.
Ordinary Story types never import/adopt this optional package implicitly.

The public concept operations separate spelling, wording, and knowledge:

- `adopts()` returns detached, scalar parameter dictionaries for authored proper
  spellings. It performs no rendering or disclosure and returns no providers or
  callbacks. The display spelling wins generated duplicates, then the first
  declared form; explicit `proper_aliases` parameter overrides win last.
- `get_nominal(narrator_key, policy=..., intent=..., **params)` is a pure read.
  AUTO under concealed policy uses required anonymous wording until identified,
  then the requested proper form. Proper-display policy uses the requested form
  immediately. Requesting `form="proper"` or `form="formal"` does not force
  knowledge: AUTO still conceals. Forced `intent=PROPER` bypasses concealment but
  creates no record. Forced ANONYMOUS stays anonymous even after introduction.
  Undeclared form requests use the display-name floor, allowing later applicable
  world text handlers to realize them; forms are not a closed enum/dispatch gate.
- `introduce(narrator_key, policy=..., source=..., **params)` explicitly identifies
  once and returns authored proper wording; `off` retains the non-adopted floor.
  Normal authored calls use phase-aware `NamingOperations.introduce`, not ambient
  narrator state. Direct deliberate calls do not promise exception recovery.

`NamingOperations` is the single scoped policy/provider boundary for helpers,
explicit references, labels and named-text dispatch. Concept override precedes
nearest MRO kind default, then off. Role/Setting knowledge remains on the actual
provider. General named objects can be referenced/introduced, but are not
automatically speakers; the existing Actor/Location attribution boundary remains.
The ordinary Actor/Location floor in adopted worlds is retained, not another
concept contract. World subclasses may override `get_nominal` or normal
named-text handlers; identification does not prescribe their wording choice.

`ConceptReference.params` carries small serializable scalar realization data,
forwarded by both semantic parts and Python `reference`/`introduce` helpers.
No second linked-text IR is added. Generated wording is
output, never re-executed. Default adoption includes only explicit proper/display
names and deliberate proper forms/aliases; `anonymous_name` is not inferred as an
adoption phrase. Ordinary speech remains opaque; narration only links with the
separate scoped consent below.

`PersonalNamedActor` optionally embeds the existing `tangl.lang.PersonalName`.
Basic named actors, places and items do not need one. `PersonalName.forms()`
preserves the provenance that `akas()` flattens: proper, familiar, formal, full,
familiar_full, formal_full, given, family, nickname, then sorted explicit aliases.
This local order decides duplicate spelling precedence; explicit proper-form and
alias parameter overrides remain available. No universal form ranking or
relationship/formality simulation is implied. Lang imports no Story/prose code.
PersonalName uses ordinary `Unstructurable` constructor form, with the explicit
include/recursion markers on the owning actor field and include on mutable aliases.
Empty/aliases-only personal names discover only their available aliases; they do
not require given/family/nickname data or block the actor's display-name fallback.
MuBlock's existing marked text field retains reference parameters, including
in-place edits. Owner graph constructor/flat JSON and normally bootstrapped
fresh-process service witnesses retain declared types, state and knowledge with
no extra components, class registry, owner pointers or custom serializers.

The demo's domain explicitly materializes/nominates one `NamedSword` at the
existing story-ready/namespace boundaries through EntityTemplate. It does not
publish every graph entity. Its CLI path reads an anonymous object, explicitly
introduces its inscription, then remembers the object. Replay/rollback retain
knowledge and historical output. Stable binding-owned aliases and #558
destination-choice scope remain separate work; #534 is not automatically closed.

## Runtime scoped exact adoption (slice 3)

`link_prose` is a scoped namespace boolean, false by default and independent of
naming policy. World globals and nearer scene/block locals use existing namespace
precedence. Only `ProseBlock.prose` string text opts into this frontend; ordinary
`Block.content`, display/choice/media strings and non-adopted worlds are unchanged.
Explicit semantic parts/templates work with linking off.

`discover_adoptions(ns)` reads only current top-level NamedConcept bindings and
bound Role/Setting providers in the already gathered namespace. Ancestor and
world/mechanic contributions are eligible on equal terms. No graph/template scan
or provisioning authorizes names. Unbound wrappers contribute nothing. A provider
symbol corresponding to a wrapper with that label/current provider is one
candidate, retaining the usable wrapper symbol; aliases of that same wrapper
collapse deterministically. Distinct wrappers or independently nominated symbols
remain distinct even if they share an actor. Encountered ambiguity lists symbols
instead of choosing dictionary order. References contain only symbols and detached
scalar `adopts()` parameters, not provider IDs/pointers or callbacks.

`link_text` is pure lowering to the existing literal/ConceptReference parts;
`prepare_prose` makes ephemeral units for the same ordered DialogHandler renderer.
Neither discovery/preparation creates knowledge, changes graph/source, or stores
prepared units. Plain MuBlock raw strings may contain narration and the existing
callouts; DialogHandler.parse supplies that grammar and full mode/attitude. Its
`literal_code` option is enabled only here, preserving ordinary parser behavior.
Paragraph source spans retain original offsets for diagnostics; normal callout
body/paragraph normalization remains the existing parser's responsibility. Styles
and source provenance survive. Already-structured custom units retain their type
and preparation methods; custom raw callout syntax stays opaque rather than being
flattened or given a new parser.

The lexical contract is conservative:

- Exact case-sensitive proper spellings, longest eligible match at a position,
  escaped regex punctuation and complete word boundaries. Anonymous descriptions
  are literal unless a custom adopter deliberately supplies one. No automatic
  capitalization, pronouns or article handling.
- `NAME#intro` or `NAME` plus spaces/tabs and complete `#intro` lowers at that
  position to an AUTO reference with `introduce=True`. A requested form is never
  forced PROPER. `#introvert`/`#introduction` are literal suffixes; punctuation
  after a complete marker remains. Newlines/punctuation cannot attach a marker.
  An unescaped complete unmatched marker is an error, with owner/source, authored
  unit index and original character offset; unrelated ordinary words are literal.
- Odd backslash runs before a known name or complete marker escape it and emit
  its spelling/adjacent marker literally. Each preceding slash pair emits one
  slash; unrelated slash runs remain unchanged. For example `\Rin #intro` is
  literal `Rin #intro`; `\\Rin #intro` emits one slash plus an introduction.
- Matched Markdown backtick spans and backtick/tilde fences are literal, including
  their markers. An unclosed fence protects the remainder. This is a small shared
  scanner, not a Markdown AST/backend. Matches cannot cross a literal code region.
- Explicit templates and authored units containing `{{`, `{%` or `{#` are wholly
  opaque to lexical processing. Split mixed source/template authoring into ordered
  units. Generated nominal/template output is never rescanned or re-executed.
- Callout speech bodies/labels are not lexically linked. Labels still use strict,
  pure current-provider resolution before bodies; literal spoken names/markers
  do not disclose. Explicit semantic parts or templates can intentionally introduce
  inside structured speech, using the same existing operations.

Actual JOURNAL realization applies explicit introductions left-to-right. Later
references/labels and already-supported semantic choice labels see the resulting
state; historical fragments do not change. Read-only label realization rejects
introductions at the existing boundary. Constructor/flat JSON/cold bootstrap retain
raw source and knowledge, while later projections link again from current scope.
Patch replay and actual internal-return/rollback witnesses retain historical output
without duplicate restoration output or graph identities. No custom serializer,
new phase, second rendering path, index/cache or recovery contract is introduced.

Current-provider spellings are the only discovered vocabulary. Previously lowered
symbolic parts follow a recast binding, but rediscovery does not retain the old
actor's spelling as a stable role alias. Stable reference-cast/binding-owned
spellings, #558 destination labels, broader Block.content adoption, compile-time
authorization, NLP and failure-atomic recovery are still separate work. These
runtime decisions supersede #534's older compiler-only/adopt-anonymous wording.
