# Credentials Phase 6b: Facet-Backed `request_document`

## Implementation prompt

Implement the first credentials game consumer of the Phase 6a facet bridge on current
`main`. Keep the change bounded to `request_document` availability and preserve its
live behavior.

Read `ARCHITECTURE.md`, `agents.md`,
`mechanics/assembly/COMPONENT_DESIGN.md`, this file,
`PHASE_6A_FACET_BRIDGE_CONTRACT.md`, and the Phase B.1 section of
`mechanics/games/CREDENTIALS_LOOP_DESIGN.md` before editing.

Use this exact semantic contribution:

```python
ComponentFacet(
    channel="choice",
    facet_type="giver",
    payload="request_document",
)
```

Add it to generated default credential definitions whose `document_kind` is
`"document"`; bearer-id definitions do not contribute it. In
`CredentialsGameHandler`, gather that facet from the active assembly-backed packet and
translate each contributing visible credential into the existing
`CredentialsMove(kind="request_document", target=<indication>)`. The facet is only the
semantic offer. The handler continues to own stage gating, once-per-case gating,
labels, accepts, time cost, selected-move safety, outcome resolution, finding state,
round notes, and journal prose.

Retain the flat `CredentialCase` path as a temporary compatibility fallback only when
the case has no assembly packet manager. When a manager exists, its facets are
authoritative: a visible credential without this facet must not contribute the move.
Do not add a generic VM facet consumer, a credentials dispatch path, a new action
factory, a new serializer, or a new move type. Do not change the current
`request_document` label, `PickAccepts`, time cost, finding outcomes, or journal text in
this slice.

Prove:

1. Standard assembly-backed permits still expose the same move targets, labels, and
   accepts as the compatibility representation.
2. Facetless assembly-backed credentials do not expose `request_document`.
3. Valid, mitigatably invalid, and forged instances of the same visible credential
   expose identical pre-commit menus.
4. Repeated availability/provisioning reads are pure and leave graph constructor form,
   packet assignments, game state, and findings unchanged.
5. Selecting the provisioned action through the existing HasGame UPDATE path records
   exactly one round/finding/time charge and retains the existing cleared/verified/
   confirmed outcome behavior.
6. A graph round-trip still restores owner binding, token identity, definition facets,
   and the same move availability after the definition catalogue is loaded before
   `Graph.structure()`.

Run the focused credential packet, mediation, game-handler/integration, and docs tests;
then run the full engine suite if the focused set passes. Update this document and
`CREDENTIAL_ASSEMBLY_RETROFIT.md` to record what actually landed.

## Capability and canonical chokepoint

The capability is small: an installed credential document may semantically offer the
existing `request_document` operation. `CredentialsGameHandler.get_available_moves()`
is the canonical adoption point because it already owns the complete move policy and
is already called by the normal HasGame PLANNING path.

```text
CredentialDefinition
  choice/giver/request_document
        |
        v
CredentialComponentToken.component_facets()
  source_id = token uid
        |
        v
CredentialPacketManager.component_facets()
  subject_id = credentials slot
        |
        v
CredentialsGameHandler.get_available_moves()
  semantic facet -> existing CredentialsMove
        |
        v
HasGame PLANNING -> Action -> ChoiceFragment
        |
        v
HasGame UPDATE -> existing resolution/finding/history path
        |
        v
HasGame JOURNAL -> existing credentials prose
```

The generic HasGame handlers remain unaware of facets. They provision and execute the
moves returned by the game handler exactly as they do today.

## Why `request_document` is the first consumer

It is the cleanest parity proof:

- the operation, move, resolution, and prose already exist;
- its parameter is derived from a document the player can already see;
- its availability must not reveal hidden validity;
- the same operation has distinct committed outcomes for valid, mitigatable, and
  criminal states;
- it exercises the complete semantic-to-syntactic path without requiring a new UI or
  mutation model.

This is deliberately an adoption test, not a redesign of the credentials loop.

## Facet contract

The two facet discriminators retain their shared mechanics meanings:

- `channel="choice"` says which consumer may adopt the contribution;
- `facet_type="giver"` says it adds an offer;
- `payload="request_document"` names the semantic operation.

Do not encode `request_document` as `facet_type`. That would replace the shared
giver/changer/hider vocabulary with a credentials-specific discriminator. Do not put a
`CredentialsMove`, label, accepts object, time cost, finding result, status predicate,
or prose in the payload. Those are syntactic realization and game policy, not a
credential capability.

The facet is authored on `CredentialDefinition`, copied with the token UID as
`source_id`, and gathered with the packet slot as `subject_id`. Discovery may use the
source UID to locate the contributing token and read its visible definition data such
as `indication`. It must not read `status` or `holder_matches` while constructing the
menu.

### Default and authored definitions

`ensure_default_credential_definitions()` should attach this facet to all generated
non-id document definitions. That preserves behavior for sampled/default packets after
they move to the authoritative assembly path.

An explicitly authored definition opts in by declaring the same facet. A manager-backed
credential whose definition omits it intentionally contributes no request move. Do not
silently fall back to `document_credentials()` when a manager is present; that would
make the facet decorative rather than authoritative.

The flat case representation has nowhere to author facets. Its current
`document_credentials()` discovery remains the compatibility path until Phase 7 removes
the flat fields.

## Adoption and policy rules

The handler should derive request targets as follows:

1. If the active case has an assembly packet manager, gather
   `channel="choice", facet_type="giver"` and retain payload
   `"request_document"`.
2. Resolve each facet's `source_id` against the public packet/component surface and
   derive the existing indication target from that component.
3. If the case has no manager, use the current flat document-token loop.
4. Apply the existing packet-stage and `finding_status` gates in the handler.
5. Emit the existing `CredentialsMove` values and let ordinary provisioning create
   actions.

Treat contributed targets as a set-union in packet order: the first contribution for
an indication wins and later contributions for that same semantic target add no second
identical action. Facets do not override one another in this slice. Distinguishing two
same-indication documents would require a document-identity move contract and is a
separate design change.

Selected-move safety must use the same current semantic availability rule. A forged or
expired credential is eligible because it has the same visible contribution; a missing,
removed, or facetless credential is not. Preserve the current non-applicable result for
an off-menu request rather than adding a second validation or exception path.

## Semantic versus syntactic ownership

This split is the mechanics-convergence point:

| Semantic document contribution | Credentials-game realization |
| --- | --- |
| `choice / giver / request_document` | `CredentialsMove(kind="request_document", target=indication)` |
| contributing token and packet slot provenance | current indication-based move target |
| visible existence of the credential | packet-stage and once-per-case gating |
| no claim about validity or result | cleared / verified / confirmed on commit |
| no presentation text | current label, accepts, round notes, and journal prose |

The same semantic operation can later be realized as “request a corrected hall pass,”
“call the issuing school office,” or “reissue a work permit” without changing the
credential capability. Conversely, a different game may consume the same document
facet through a different syntactic surface.

## Compatibility decisions for this slice

- **Labels and accepts:** preserve live behavior. The current handler returns
  `"Request reissue of {target} permit"` and `PickAccepts`. The credentials widget
  design note describes a future piece-selecting realization, but changing that while
  proving facet adoption would mix two contracts.
- **Provenance:** source and subject provenance prove and drive discovery, but the
  existing indication-based `PickingMove`, `RoundRecord`, and journal payload remain
  unchanged. Carrying a document UID through generic game actions is deferred until a
  concrete consumer needs document-identity receipts.
- **Transactions:** none. The current move records a finding and time/round history; it
  does not replace or move a credential component. A future literal reissue that creates
  a new component belongs in UPDATE and may require a `TransactionOffer`.
- **Persistence:** no new state is introduced. Definitions are catalogue singletons,
  facets are derived copies, packet membership remains UUID-backed, and graph
  round-tripping stays on `unstructure()` / `structure()`.
- **Materialization:** availability may not prepare a case or create components.
  Existing setup/case-advance boundaries remain authoritative.

## Expected edit surface

- `tangl/mechanics/credentials/assembly.py`
  - add the default semantic facet to non-id definitions;
  - keep authored templates immutable and catalogue-driven.
- `tangl/mechanics/games/credentials_game.py`
  - replace only the manager-backed `request_document` discovery source;
  - retain the flat compatibility branch and all existing move policy/writeback.
- credential packet and credentials game/integration tests
  - add parity, secrecy, purity, UPDATE, and round-trip proofs.
- these two retrofit notes
  - record the final implementation status and any deliberately deferred discrepancy.

Avoid touching generic assembly, VM dispatch, HasGame provisioning, journal fragment
types, service DTOs, or persistence code unless a failing proof exposes a genuine
contract defect. Surface that defect before adding a bridge or shim.

## Acceptance matrix

| Concern | Required evidence |
| --- | --- |
| Shared vocabulary | exact `choice / giver / request_document` facet; no credentials-specific facet behavior type |
| Authority | manager-backed availability comes only from facets; flat fallback only without a manager |
| Secrecy | same menu for identical visible definitions across valid, invalid, and forged token state |
| Purity | repeated availability and provisioning leave graph and game constructor form unchanged |
| Lifecycle | ordinary PLANNING creates actions; one ordinary UPDATE applies the selected move |
| Parity | standard manager-backed and flat cases expose the same semantic targets and live UI contract |
| Persistence | fresh-catalogue graph structure restores tokens, slots, facets, owner, and menu |
| Scope | no new dispatch, action factory, serializer, move type, UI contract, or transaction |

## Deferred next moves

After this proves one real choice consumer, the next design step is not “convert every
credentials action.” Compare the result against a second semantic operation with a
different realization pressure—most likely `verify_id` or an assembly capability used
by sandbox/challenge progression. That comparison should determine whether the payload
string remains sufficient or whether a small shared parameterized-operation value is
actually justified.

Only then should broader choice-facet lowering, document-identity selection,
piece-based request widgets, receipt provenance, or general facet promotion be
considered.
