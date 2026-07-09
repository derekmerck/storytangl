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
existing disposition protocol. Factory/materialization, move facets, expression
narrative, contraband graph identity, and status decomposition remain future
slices.

**Dependency:** the owner-bound manager and wardrobe transaction substrate provides the
storage and offer semantics this retrofit relies on: `ComponentManager` stores
graph-member assignments by UUID, embedded managers serialize with their owner, and
component-manager slots can participate in transaction offers through a holder adapter.

**Related docs:**

- `engine/src/tangl/mechanics/credentials/CREDENTIAL_MECHANIC.md`
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
- `HasGame.game` asks hosted games to bind embedded component managers to the block
  when the game exposes `bind_component_managers(owner)`.

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

Change `build_valid()`, `degrade()`, and `render_narrative()` to operate on the packet
manager, while keeping compatibility shims for tests and worlds.

Important rule: generation remains "start correct, then degrade."

Acceptance:

- sampled offers still materialize to their target disposition;
- failure modes mutate credential components or packet membership, not parallel flat
  lists;
- narrative rendering reads packet/credential components through projection helpers.

### Phase 6: Adopt Component Facets For Contributions

Only after the VM phase-trigger/component-contribution shape is settled:

- model credential-provided inspection moves as component facets;
- model document media projection as a media facet or direct adapter;
- model score/disposition modifiers as game/credential channels;
- keep mutation in the existing game UPDATE path or transaction offers.

Acceptance:

- PLANNING can discover credential-provided moves without mutation;
- UPDATE commits selected credential actions atomically;
- JOURNAL can consume receipt/finding data for fragments;
- no credentials-only dispatch pipeline is introduced.

### Phase 7: Retire Compatibility Fields

Once `credential_gate`, factories, and tests all use the manager path:

- remove direct packet lists from `CredentialCase`;
- remove duplicated discovery methods from the case, or make them pure delegation;
- re-home game imports from `tangl.mechanics.games.credentials_enums` to
  `tangl.mechanics.credentials`.

Do this only after a release/PR where both paths were tested side by side.

---

## Test Plan

Core/global credentials tests:

- credential component constructor-form round-trip;
- packet manager graph round-trip with id, permit, and contraband components;
- manager owner rebound after structure;
- disposition derivation parity with current value-token fixtures;
- component facets gathered by channel and subject.

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
