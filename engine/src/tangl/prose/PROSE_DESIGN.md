# Optional prose extensions

Status: explicit concept naming/reference (#534 slice 1) and conservative exact
role/setting name/nominal/#intro linking (slice 2) implemented.

Rendering sessions and dialog micro-blocks are existing realization helpers.
`naming` is an optional Story extension adopted by world domains before
compilation through their existing class registry and authority chain. Story
does not import this module to activate it. It installs no alternate registry
or fragment hierarchy; its behaviors use normal Story/VM dispatch tasks.

`ConceptReference` is a small value describing a namespace referent, wording
intent, and introduction. `ProseSegment` pins order across body references and
speaker displays. These contain no live graph pointers; normal typed model
fields and constructor-form graph persistence suffice. Concepts store proper
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
is resolved under this bounded scope: use ProseSegment for label-before-body
ordering and once-only body evaluation. No spoken-name rewriting or narrator
inference is added.
Attributed dialog tone/avatar and presentation-class work remains #454/#457.

## Exact lexical frontend

World domains separately contribute `LinkedProseYamlCodec` through the existing
`get_story_codecs()` seam and select `codec: linked_prose_yaml` in their manifest.
Naming policy alone never opts text into lexical processing. `link_prose: true`
inherits from world to scene to block; `false` opts a nearer scope out.

The frontend runs a pure catalog compilation, then lowers opted-in narrative
strings to `ConceptReference`/`ProseSegment` data before the ordinary world
compilation. This costs a second compile pass, not graph provisioning. The
catalog's eligible entries are scoped Role/Setting declarations; Actor/Location
template prototypes supply only reference-cast spellings. Nearest declarations
shadow outer declarations, even when their runtime providers are unbound.

`BindingReference` records the declaration owner's authored runtime path, edge
label, and `role_edges`/`setting_edges` collection. Realization looks up that
actual edge in the current scoped namespace, checks its owner path, and then
reads its current provider. No provider name, UID, or template-lineage cache is
the link's identity. Paths come from the existing persisted graph hierarchy;
normal constructor/JSON structuring and patch replay need no new restoration
hook or serializer. Renaming/reparenting an owner does not silently retarget a
compiled reference: its scope check fails.

Exact proper spellings and role symbols use AUTO policy. The one declared full
anonymous nominal uses ANONYMOUS intent, including its determiner. Its
initial-capital variant records capitalization; other grammar is not inferred.
`link_forms: {host: {proper: Rin, anonymous: the blonde girl}}` supplies explicit
reference spellings when prototype wording is insufficient. Distinct roles
adopting the same spelling are ambiguous, even if their reference cast uses the
same Actor. Longest exact spelling wins; word boundaries prevent Rin/Ringo
matches. Ambiguity and unmatched introductions report source path, block,
segment, and eligible forms/bindings. Narrative `Rin #intro` or `Rin#intro`
lowers to an introduction at that position.

The grammar is deliberately limited to narrative `content` or ordered `prose`
segments whose `text` is a string. Speaker segments adopt only their label;
their entire body is literal, including names, Jinja-looking text, and #intro.
`raw: true` segments are likewise opaque. A backslash escapes one adopted
form (and its adjacent introduction marker), removing only that escape.
Explicit `template` segments are not scanned and execute through the existing
one-shot rendering path. Ordinary whole-block Jinja `content` bypasses lexical
linking and retains existing late binding/composition. Mixing templates with
linked narrative requires explicit segments, not a generic template parser.
Linked dialog callout `content` must be rewritten as explicit speaker segments;
the frontend rejects it rather than rewriting spoken text. Arbitrary Markdown
code regions, pronouns, aliases, and determiner transformations are not parsed:
use raw segments or explicit semantic references. Choice text remains raw;
explicit `choice_labels` remains the slice-1 naming surface.

Ordinary Blocks lower to ProseBlock. A world-specific block must already inherit
ProseBlock; the frontend refuses to discard another mechanic's block kind.
World-specific short kind aliases used by the catalog are supplied to the codec
constructor; there is no additional class-discovery or compiler-hook registry.
The downstream fixture is `worlds/concept_linking_demo`, with pure compile,
recast, scope, cold-restore, replay, and actual return-edge tests in
`engine/tests/prose/test_linking.py`. Compilation and reference previews never
write knowledge; #intro retains the existing successful-traversal/non-atomic
exception boundary described above.
