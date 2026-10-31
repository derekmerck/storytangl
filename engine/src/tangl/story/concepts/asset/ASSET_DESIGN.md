# tangl.story.concepts.asset - Design Notes

> Status: Discrete wallet foundation and singleton-keyed countable holdings implemented;
> holder integration and assembly convergence remain planned under #652.

## Position

Assets are story concepts layered over core tokens and graph relationships.
They are not a separate inventory engine.

This package currently defines:

- `AssetType`: a singleton definition for tokenizable, lightly stateful assets.
  It includes a small `traits` set for story/mechanics layers that need
  semantic acceptance checks.
  Optional `icon: str | None` nominates a presentation token, inherited through
  the existing singleton/type and token delegation mechanisms. It is advisory,
  not a filename or media reference; a provider may copy it to section hints.
- `CountableAsset`: a fungible asset definition tracked by quantity.
- `AssetWallet`: a counter for singleton definitions and explicit named game pools.
- `DiscreteAssetWallet`: a graph-owned, ordered UUID group of discrete graph members.
- `HasAssets`: a story-level facet for nodes that hold wallet counts and
  nominate discrete asset tokens into namespaces.
- `AssetTransactionManager`: a small preflight-and-mutate service for transfers
  between `HasAssets` holders.

Discrete members may be ordinary graph nodes or `Token[AssetTypeSubclass]` objects.
A token refers to its singleton definition and carries graph-local state.

## Holder Model

`HasAssets` is the current holder surface. It publishes:

- `asset_holder`: the holder itself;
- `asset_wallet` and `wallet`: the fungible wallet;
- `assets` and `inv`: the holder's nominated discrete asset tokens.

Those symbols are intentionally ordinary namespace contributions, so roles,
settings, sandbox scopes, and other story machinery can prefix or inspect them
without learning a separate inventory engine.

`AssetWallet` is an embedded constructor-form value. Its owning fields opt into
recursive unstructuring and in-place mutation retention. It persists a canonical
ordered list of entries: singleton keys use their normal `(kind, label)`
references, while explicit string keys remain distinct named pools. World/catalog
bootstrap must establish live singleton definitions before graph restoration.
The sequence is a JSON representation of an unordered mapping, not acquisition
order. Named game pools retain their explicit local definition maps.

The deferred discrete `assets` map remains explicitly excluded from persistence:
it is not yet the graph-backed ownership model.

## Approved Membership Model and Migration

A `DiscreteAssetWallet` is a non-hierarchical `Subgraph` owned by the graph.
Its host refers to the wallet by UID; the graph serializes wallet and items once
apiece. Membership is ordered and unique, references resolve to the actual graph
members, and missing references fail visibly. Groups express their own meanings:
an item can belong to both a possession group and an equipment group. They do
not reparent members or impose universal exclusive custody. Checks are pure;
create wallets at accepted setup or mutation boundaries, never during reads.

The next slices migrate the existing `HasAssets` surface to compose independent
discrete and countable capabilities, resolving the graph anchors for embedded
sandbox holders. The current excluded holder map remains a pre-migration
implementation, not a second permanent source of truth.
Assembly must then build graph-backed slot membership on this same primitive,
while retaining slot policy and owner binding. Transactions coordinate checked
exchanges across holders; they do not define another membership store.

### ContainerFacet Validation Criteria

Keep `ContainerFacet` as an experimental mechanics-level holder until it proves
the following against sandbox examples:

- fixture containers and portable asset containers both use the same
  `AssetTransactionManager` preflight path;
- closed or locked containers reject receive/release attempts without partial
  mutation;
- count capacity, trait acceptance, and the current no-nested-containers rule
  are expressible without special-case action code;
- generated affordances can explain source, target, and rejection through
  ordinary action availability and `ui_hints`;
- the Adventure cage/chest pressure tests remain deterministic under replay.

## Transaction Model

`AssetTransactionManager` validates a complete transfer before mutating wallets
or holder asset maps. It remains the story-level convenience for the current
holder surface. The cross-family `tangl.mechanics.transaction` helper now carries
the shared spec/offer/commitment/receipt shape for broader shops, services,
assembly assignment, holder-local asset movement, catalog-backed token creation,
and mixed writeback.

The holder migration should use that existing transaction mechanism to coordinate
preflight and mutations of the discrete and countable wallets, preserving holder
and counterpart policy and rollback behavior.

A higher-level trade manager can later compare aggregate values and actor
biases before delegating to the transaction manager.

See `../../../mechanics/TRANSACTION_OFFER_DESIGN.md` for the shared
spec/offer/commitment/receipt vocabulary that generalizes this manager across
provisioning, shops, services, assembly assignment, and future relationship
writeback.

## Known Limitations

The current slice is intentionally sufficient for sandbox affordance
experiments, not a complete inventory system.

- `HasAssets.assets` is a holder-local map, not yet a graph-backed ownership
  subgraph. It is good enough for "player has key" checks and first-slice
  sandbox containers, but not enough for full persistence of room inventories
  or ownership history.
- Discrete transfers currently move tokens between holder maps. Slice 2 should
  migrate this to the graph-owned discrete wallet, with one authoritative
  membership representation.
- Transaction preflight asks holder policy methods (`can_give_*` and
  `can_receive_*`) directly; preserve these policies during holder migration.
- Existing holder-map asset moves and catalog-backed token creation can now be
  expressed with `AssetMoveCommitment` and `CatalogAssetCommitment`. The
  remaining work is to use wallet membership with equivalent commitments.
- `HasAssets` nominates `inv` and `assets` into local namespaces, but there is
  no story-level `Player`/avatar concept yet. Sandbox currently uses
  `SandboxScope.player_assets` as the explicit player stand-in; promote a real
  player/avatar concept once the namespace policy is clearer.
- Ambiguity is deferred. Multiple matching keys, multiple lockable objects,
  quantities, and parser-style disambiguation should remain UI/compiler
  concerns until a concrete sandbox example demands them.
- Sandbox integration now has a first narrow affordance set: location-held
  tokens project take/read choices, player-held tokens project drop choices, and
  held key tokens satisfy generated unlock actions. The next asset slice should
  replace holder-local maps with the graph-owned discrete wallet.
