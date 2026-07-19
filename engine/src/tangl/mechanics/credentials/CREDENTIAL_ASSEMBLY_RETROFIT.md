# Credential Packet Assembly Retrofit

```{storytangl-topic}
:topics: credentials, assembly, transaction, games
:facets: design, planning
:relation: proposes
:related: component, provision, vm, media
```

**Status:** PARTIALLY IMPLEMENTED. The first retrofit slice landed the global
credentials domain import surface, graph-backed credential components, an
owner-bound assembly packet manager, and a `CredentialCase` bridge behind the
existing disposition protocol. Phase 5 now materializes sampled offers into an
authoritative packet manager at setup and case-advance boundaries, and persists
the hosted game through the normal constructor-form graph path. Phase 6a landed the
pure credential-token facet bridge, and Phase 6b landed its first consumer:
`CredentialsGameHandler` derives the existing `request_document` move from the exact
`choice / giver / request_document` facet on a manager-backed document. The handler
remains the choice and resolution authority; flat cases remain a temporary fallback.
Phase 6c landed the corrected catalog authority: generic authored definitions and open
origin/indication ids compile into named, bounded token catalogs exposed by the bound
world. A scenario type selects one world-local catalog, and packet materialization
searches only that catalog rather than a game-owned world namespace or the global
Singleton population. Qualified definition labels remain an internal persistence detail.
Phase 6d is planned as the real Hall Monitor conformance vertical: a bespoke scenario
type selects the school catalog, a script-configured shift narrows it to one scenario
instance, and generated plus pinned student encounters reuse the same logical packet,
disposition, handler, and persistence path under a school-specific projection.
Expression narrative beyond that first skin seam, contraband graph identity,
document-identity receipts, and status decomposition remain future slices.

**Dependency:** the owner-bound manager and wardrobe transaction substrate provides the
storage and offer semantics this retrofit relies on: `ComponentManager` stores
graph-member assignments by UUID, embedded managers serialize with their owner, and
component-manager slots can participate in transaction offers through a holder adapter.

**Related docs:**

- `engine/src/tangl/mechanics/credentials/CREDENTIAL_MECHANIC.md`
- `engine/src/tangl/mechanics/credentials/PHASE_6A_FACET_BRIDGE_CONTRACT.md`
- `engine/src/tangl/mechanics/credentials/PHASE_6B_REQUEST_DOCUMENT_HANDOFF.md`
- `engine/src/tangl/mechanics/credentials/PHASE_6C_AUTHORED_CATALOG_HANDOFF.md`
- `engine/src/tangl/mechanics/credentials/PHASE_6D_HALL_MONITOR_SCENARIO_HANDOFF.md`
- `engine/src/tangl/mechanics/games/CREDENTIALS_LOOP_DESIGN.md`
- `engine/src/tangl/mechanics/assembly/COMPONENT_DESIGN.md`
- `engine/src/tangl/mechanics/TRANSACTION_OFFER_DESIGN.md`

---

## Why Retrofit

The live credentials implementation already split the *game loop* from a packet
discovery protocol. `CredentialCase` still owns compatibility fields and narrative
strings, while `CredentialPacketManager` projects the structured packet shape used by
`derive_disposition()`.

That bridge solved the immediate layering problem, but it remains parallel to the
newer assembly pattern:

- outfit: active body loadout manager over wearable graph tokens;
- wardrobe: inactive storage manager over wearable graph tokens;
- vehicle: loadout manager over vehicle-part graph tokens;
- credentials today: packet-shaped value object over embedded `CredentialToken`
  values.

The retrofit makes credentials another assembly specialization without losing the
existing game semantics: credential instances are tokens, the packet is an
owner-bound manager, and disposition derivation reads the packet through the same
small protocol it already uses.

Current implementation checkpoint:

- `tangl.mechanics.credentials.domain` owns the credential enums/value types, while
  `tangl.mechanics.games.credentials_enums` remains a compatibility re-export.
- `CredentialDefinition` / `CredentialComponent` provide graph credential tokens
  that project to the legacy `CredentialToken` value shape.
- `tangl.mechanics.credentials.CredentialPacketManager` is the assembly-backed
  manager. The older `tangl.mechanics.games.CredentialPacketManager` remains the
  value-object adapter for flat legacy cases.
- `CredentialCase.packet_manager` is optional; when present, case discovery methods
  delegate to it. Otherwise the legacy flat fields remain authoritative.
- `HasGame.game_state` embeds the hosted `Game` through constructor-form recursion;
  `HasGame.game` binds embedded component managers to the block on access.
- Generated packets currently use finite default `CredentialDefinition` instances loaded
  by `tangl.mechanics.credentials`; the Phase 6c revision must expose any retained stock
  definitions through a bounded catalog while still ensuring their labels resolve before
  a restored graph structures its credential components.

## Resolved Review Constraints

The first retrofit slice deliberately stops before graph-backed packets drive the
game loop. Later slices must preserve these constraints:

- **Disclosure discipline:** contribute moves from visible document existence, never
  hidden validity; disclose validity only when a committed move resolves.
- **Packet authority:** a case either owns an assembly packet manager as its write
  target or projects a fresh compatibility adapter from authoritative flat fields.
  A cached projection must not silently become authoritative.
- **Phase purity:** graph-backed case materialization and registry writes happen at
  setup or an UPDATE boundary, not on the first PLANNING read.
- **State scope:** durable document facts belong on credential components;
  encounter-scoped findings remain on the game and reset with the case.
- **Facet adoption:** components contribute data and the credentials game handler
  remains the choice factory, responsible for availability, time cost, off-menu
  validation, and committed resolution. Components do not register dispatch behavior.
- **Replay and provenance:** moving mutable facts outside the game model requires an
  explicit graph/replay test. Prefer one document identity across the component,
  projected piece, receipt, and journal provenance when that projection is adopted.
- **Narrative projection:** authored `presented_documents` and `hidden_facts` remain
  compatibility narrative until the expression/projection system can derive them from
  component state without losing world-specific prose.

---

## Target Vocabulary

### Credential Component

A **credential component** is a graph member token representing one presented
document, permit, id, ticket, waiver, or badge.

Recommended shape:

```text
CredentialType / CredentialDefinition
  issuer, document kind, indication/purpose, default media projection

CredentialComponent
  token over the definition
  status / holder binding / dates / visible fields / errors
  facets for packet, game, media, and VM contribution channels
```

This should probably become a `Component` subclass (or token wrapper that exposes the
same `component_facets()` shape), because credentials need to contribute both:

- packet-local facts: indication, id binding, status, issuer, media payload;
- broader mechanics signals: grants, restrictions, inspection moves, warnings, or
  phase-triggered effects.

### Credential Packet Manager

A **credential packet manager** is an embedded, owner-bound `ComponentManager` that
groups credential components by role.

Candidate slots:

```text
id
purpose_permit
supporting_credentials
declared_goods
contraband
```

The exact slot names can remain domain-specific, but the public protocol should
remain the current stable surface:

```python
get_region() -> Region
get_purpose() -> Indication
id_status() -> CredentialStatus | None
credential_for(indication: Indication) -> CredentialComponent | None
get_contraband() -> list[ContrabandItem | CredentialComponent]
all_credentials() -> list[CredentialComponent]
```

`derive_disposition()` should keep reading this protocol rather than concrete fields.
That is the seam that lets `CredentialCase`, the compatibility adapter, and the future
manager coexist during migration.

### Credential Case

`CredentialCase` remains the game-facing encounter envelope:

- candidate name and narrative strings for the v1 inspect loop;
- whitelist / blacklist / bribe / context overlays;
- generated or authored packet data;
- compatibility projection to a packet protocol object.

After retrofit, the case should hold either:

- a `CredentialPacketManager` directly; or
- a legacy flat packet that can be converted by `to_packet_manager()` until the old
  fields are retired.

Do not make `CredentialCase` itself the component manager. The case is an encounter
record; the packet is the assembly.

---

## Identity And Serialization

The intended split mirrors outfit and wardrobe:

- credential components are graph members when they need independent identity,
  movement, media, history, or inspection state;
- the packet manager is embedded on the owning case/candidate/block and persists by
  constructor-form recursion;
- packet membership is id-backed, not inline deep copies;
- the owner pointer is excluded and rebound on structure.

This gives credentials the same invariants as the other assembly consumers:

```text
Graph.unstructure()
  -> case/block contains packet manager constructor form
  -> packet manager contains slot -> credential UUIDs
  -> credential components live once in graph members
```

The current `CredentialToken` value objects can stay during the bridge, but they should
not be the final persistence contract for graph-addressable documents.

---

## Slot And Validation Rules

Credential packet validation is a stronger fit for a specialized manager than for a
generic slot list. The manager should own:

- required id rules;
- purpose permit rules;
- `requires_id` / `holder_matches` checks;
- document status aggregation;
- credentialed contraband requirements;
- declared vs concealed item rules;
- owner/candidate-property checks, such as purpose, region, and current restriction map.

The current `derive_disposition()` logic should remain the source of truth during the
migration. The manager can add convenience methods:

```python
packet.validate_against(restrictions, finding_status=None) -> list[CredentialFinding]
packet.derive_disposition(restrictions, finding_status=None) -> CredentialDisposition
packet.component_facets(channel="choice" | "journal" | "media" | ...)
```

But those should delegate to the same protocol-level assessment logic, not fork a
second derivation engine.

---

## Facets And VM Phase Contributions

This is the main integration question for the active VM phase-trigger/component
contribution work.

Credentials are a natural component/facet forcing case because one credential can:

- **give** a capability: valid work permit grants "can work";
- **hide** or block a disposition: forged id forces arrest, missing permit blocks pass;
- **change** a score or phase result: whitelist, bribe, or cleared finding modifies the
  normal penalty/disposition path;
- **produce media**: document card / id photo projection;
- **produce inspect moves**: "inspect seal", "verify id", "request replacement";
- **participate in phase triggers**: an expired permit may trigger warnings during
  PLANNING, an accepted bribe may mutate state during UPDATE, a forged document may
  add journal content during JOURNAL.

The retrofit should not invent a credentials-only phase bus. Instead:

1. Credential components carry facets as data.
2. The packet manager gathers active credential facets.
3. VM/game handlers adopt only the channels they understand.
4. `can_*` checks stay pure; mutation remains in UPDATE through game handlers or
   transaction offers.

Open review question for the phase-trigger work:

> Should phase-triggering component contributions be represented as
> `ComponentFacet(channel="vm_phase", payload={phase, trigger, ...})`, or should
> they lower into existing dispatch/on_phase handlers at compile/materialization time?

For credentials, the important constraint is that inspection/provisioning may ask
many times whether a component contributes a move or restriction. Those reads must be
pure. Journal notes, state mutation, confiscation, reissue, bribe acceptance, and
penalty updates happen only in committed update/journal phases.

---

## Transactions And Association

Credentials also exercise the transaction vocabulary:

- confiscate a forged credential;
- request a replacement document;
- surrender forbidden goods;
- pay a bribe;
- accept a service that clears an expired permit;
- move a credential from a packet into evidence storage.

Those are not packet validation; they are update-phase writebacks. Use
`TransactionOffer` and commitments where more than one state change must commit
together.

Examples:

```text
request replacement permit:
  debit time
  mark finding cleared
  create/reissue credential component
  assign it into packet slot

confiscate forged id:
  move credential component from packet -> evidence holder
  record packet finding
  add penalty/journal receipt

surrender contraband:
  move declared item -> checkpoint storage
  mark relinquish finding yielded
  recalculate disposition
```

The packet manager owns legality. Transaction offers own multi-leg atomicity and
receipt data.

---

## Migration Plan

### Phase 0: Characterize Current Contracts

Status: landed. Tests confirm the current protocol:

- `derive_disposition()` accepts both `CredentialCase` and `CredentialPacketManager`;
- `CredentialCase.to_packet_manager()` preserves region, purpose, id status,
  credentials, and contraband;
- generated cases still derive to their sampled target disposition;
- `credential_gate` widget flow remains unchanged.

The credentials derivation characterization suite, including the six disposition
families and hazard ordering pinned for #276, is the parity oracle for later migration
slices. A manager-path behavior difference is a retrofit regression unless the game
contract is changed explicitly.

No gameplay model changes were required.

### Phase 1: Move Domain Types To Global Credentials Package

Status: landed as the global import surface under `tangl.mechanics.credentials`, with
game-layer compatibility re-exports during the transition:

- `Region`, `Indication`, `RestrictionLevel`, `Restrictions`;
- `CredentialStatus`, `FailureMode`, `FailureClass`;
- `CredentialToken` compatibility type, if still needed;
- `CredentialPacketProtocol` remains game-local until the game loop is no longer the
  only protocol consumer.

Goal: break the assumption that credentials are a game-only vocabulary.

### Phase 2: Add Graph Credential Components

Status: landed without changing the game loop:

- `CredentialDefinition` definition singleton;
- `CredentialComponent` graph token wrapper;
- fields equivalent to current `CredentialToken` for indication, status,
  `requires_id`, and holder-match compatibility.

Presence snapshots and derived holder matching are intentionally not implemented in
this slice. `holder_matches` remains compatibility state until the presence binding
surface exists.

Acceptance:

- graph round-trip preserves credential components once by UUID;
- media/prose labels match current generated narrative;
- value-token compatibility tests still pass.

### Phase 3: Add Owner-Bound Credential Packet Manager

Status: landed as `tangl.mechanics.credentials.CredentialPacketManager`, distinct from
the legacy value-object adapter exported by `tangl.mechanics.games`.

The manager should:

- store credential component ids by slot;
- expose the existing `CredentialPacketProtocol`;
- aggregate status, holder-match, required-id, and contraband checks;
- bind to its owner and round-trip through constructor-form recursion.

Acceptance:

- `derive_disposition(packet_manager, restrictions)` matches the current case-derived
  behavior for the existing credential test matrix;
- graph round-trip restores packet owner and dereferences restored credential graph
  members;
- no inline duplicate credential components appear in graph structure.

### Phase 4: Bridge `CredentialCase`

Status: landed. `CredentialCase` can carry the new manager while retaining flat fields
as compatibility inputs.

Recommended temporary shape:

```python
packet_manager: CredentialPacketManager | None = Field(
    default=None,
    json_schema_extra={"include": True, "unstructurable": True},
)
```

`to_packet_manager()` should return the existing manager when present, otherwise build
the compatibility manager from flat fields. Avoid rebuilding a fresh manager every time
once a case owns one; cached/owned manager state matters once components carry mutable
inspection/media state.

Acceptance:

- current tests remain green;
- packet-manager identity is stable across repeated property/protocol access;
- no behavior change in `credential_gate`;
- graph round-trip is proven for normal graph owners with embedded packet managers;
- `HasGame` binds roster/materialized packet managers to the live block owner on game
  access, without changing the broader `HasGame` private-game persistence path.

### Phase 5: Retrofit Factory And Roster Materialization

Status: landed for sampled offers. Factory generation remains value-based and
deterministic. A hosted game materializes its arriving offer into graph credential
components and an owner-bound packet manager during setup or case advance; planning
only reads that prepared manager. The source case clears its flat packet fields once
the manager becomes authoritative. `HasGame.game_state` now persists through the
normal `unstructure()` / `structure()` path, so the embedded manager and its component
references survive graph restore.

Keep `build_valid()` and `degrade()` value-based initially. Convert their output into
an owned packet manager at the committed case-arrival boundary, then migrate game-loop
reads from flat case fields to packet/component projection helpers. Rework factory
mutation only when generation must set graph identity such as media or holder bindings.

Important rule: generation remains "start correct, then degrade."

Acceptance:

- sampled offers still materialize to their target disposition;
- graph components are created and registered during setup or UPDATE, never on the
  first PLANNING read;
- failure modes mutate credential components or packet membership, not parallel flat
  lists once the owned manager becomes authoritative;
- narrative rendering reads packet/credential components through projection helpers.

### Phase 6: Adopt Component Facets For Contributions

Status: Phase 6a and the bounded 6b `request_document` adoption are landed. Phase 6a
added pure token-to-packet facet discovery with constructor-form persistence proof.
Phase 6b adds the generated non-id document `choice / giver / request_document`
contribution and lets `CredentialsGameHandler` lower it into the existing
indication-based move only when an assembly packet manager is present. It preserves
the flat compatibility case path, existing labels, accepts, time cost, outcomes, and
journal prose. A facetless manager document contributes no move, and the selected
move path uses the same availability rule.

Phase 6c is the catalog-authority continuation of this adoption. The corrected contract
requires a world to expose named token catalogs with explicit members. A scenario type
selects a world-local catalog reference, while a scenario instance configures roster and
encounter composition. Packet materialization resolves only within the selected catalog;
it must not search the process-global Singleton population or carry a world label as game
state. Phase 6d applies that hierarchy in the real Hall Monitor conformance world; see
`PHASE_6D_HALL_MONITOR_SCENARIO_HANDOFF.md`.

Later slices may:

- model further credential-provided inspection moves as component facets;
- model document media projection as a media facet or direct adapter;
- model score/disposition modifiers as game/credential channels;
- keep mutation in the existing game UPDATE path or transaction offers.
- let the game handler adopt facets into moves and apply time costs and off-menu
  validation centrally;
- gate move contribution on visible document existence, not hidden credential status.

Acceptance:

- PLANNING can discover credential-provided moves without mutation;
- repeated move discovery exposes the same menu for visibly equivalent valid and
  invalid documents;
- UPDATE commits selected credential actions atomically;
- JOURNAL can consume receipt/finding data for fragments;
- no credentials-only dispatch pipeline is introduced.

### Phase 7: Retire Compatibility Fields

Once manager-backed Credential Gate and Hall Monitor paths have run side by side and
their scenario-specific projections are covered:

- remove direct packet lists from `CredentialCase`;
- remove duplicated discovery methods from the case, or make them pure delegation;
- re-home game imports from `tangl.mechanics.games.credentials_enums` to
  `tangl.mechanics.credentials`.

Retire authored packet narrative only after expression/projection helpers can preserve
world-specific visible descriptions and committed hidden-fact disclosure.

Do this only after a release/PR where both paths were tested side by side.

---

## Test Plan

Core/global credentials tests:

- credential component constructor-form round-trip;
- packet manager graph round-trip with id, permit, and contraband components;
- manager owner rebound after structure;
- disposition derivation parity with current value-token fixtures;
- component facets gathered by channel and subject;
- one world may expose and select two credential catalogs independently;
- separately loaded worlds may reuse local catalog/item ids without visibility leakage.

Game compatibility tests:

- existing `engine/tests/mechanics/games/test_credentials_*`;
- `engine/tests/integration/test_credentials_widget_flow.py`;
- `engine/tests/loaders/test_credential_gate_world.py`;
- generated roster target-disposition verification.

Serialization tests:

- sample graph containing a credentials block/case with populated packet manager;
- `Graph.unstructure()` / `Graph.structure()` preserves one graph member per
  credential component;
- no raw `model_dump()` is used as a persistence proof.

Replay/provenance tests for the authoritative manager path:

- a transaction mutates a credential component outside the game model;
- receipts and journal fragments identify the mutated component;
- replay restores the same component state even when the game's local value hash does
  not encode the component payload.

VM/facet tests after phase-trigger work:

- PLANNING gathers credential-provided moves purely;
- UPDATE applies chosen credential action once;
- JOURNAL receives committed finding/receipt context;
- repeated planning does not add findings, spend resources, or mutate packet state.

---

## Non-Goals

- Do not rewrite the credentials game loop while migrating packet identity.
- Do not move media composition into the packet retrofit; media projection can consume
  credential components later.
- Do not make all credential values graph members at once if compatibility fixtures
  still need flat data.
- Do not decompose `CredentialStatus` while packet identity is migrating.
- Do not give contraband graph identity until transactions need goods to move between
  durable holders; contraband is not a credential component.
- Do not create a credentials-only dispatch or phase-trigger framework.
- Do not make facets durable derived state. Store credential facts and findings; derive
  contributions during phase handling.

---

## Review Questions

For the original credentials implementation agent:

1. Which existing `CredentialToken` fields should become credential component state,
   and which should move to a `CredentialType` definition?
2. Should contraband remain separate `ContrabandItem` values, or become packet
   components sharing the same manager path?
3. Can `CredentialCase.to_packet_manager()` become stable/cached without surprising
   any current tests or generated-case flows?
4. Which current tests best prove derivation parity when packet storage changes?
5. Does `CredentialPacketProtocol` need more methods before becoming the global
   packet interface?

For the VM phase-trigger/component-contribution agent:

1. What is the intended representation for a component contribution that wants to
   affect a specific VM phase?
2. Can the contribution read path be pure and repeatable during PLANNING?
3. Where should a credential contribution lower into existing handlers: component
   facet gather, game move provisioning, or dispatch registration?
4. How should provenance flow from credential component -> packet slot -> candidate
   case -> journal fragment?
5. Are component contributions allowed to create parameterized choices, or should
   they only annotate choices generated by the game handler?

---

## Suggested First PR

The first implementation PR should be small:

1. Move or alias the credentials domain vocabulary into
   `tangl.mechanics.credentials`.
2. Add `CredentialComponent` and `CredentialPacketManager` behind the existing
   protocol.
3. Add parity tests showing `derive_disposition()` returns the same result for a
   current `CredentialCase`, current compatibility `CredentialPacketManager`, and new
   assembly packet manager.
4. Do not change `CredentialsGameHandler`, widgets, media, or phase-trigger
   behavior yet.

That gives the implementation agent a concrete target and leaves the active
VM/component-contribution work room to define the phase facet surface before
credentials adopts it.
