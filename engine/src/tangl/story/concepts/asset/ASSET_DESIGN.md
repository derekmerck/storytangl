# tangl.story.concepts.asset - Design Notes

> Status: Graph-owned discrete and singleton-keyed countable holder integration is
> implemented; assembly convergence remains planned under #652.

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
- `HasFungibleAssets` and `HasDiscreteAssets`: independent holder capabilities.
- `HasAssets`: the combined facade over those capabilities.
- `AssetTransactionManager`: a small preflight-and-mutate service for transfers
  between `HasAssets` holders.

Discrete members may be ordinary graph nodes or `Token[AssetTypeSubclass]` objects.
A token refers to its singleton definition and carries graph-local state.

## Holder Model

`HasAssets` is the current holder surface. It publishes:

- `asset_holder`: the holder itself;
- `asset_wallet` and `wallet`: the fungible wallet;
- `assets` and `inv`: resolved views of graph-owned discrete members;
- `asset_sources`: live member objects available for typed contribution discovery.

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

Discrete holders persist the wallet UID and any holder-local aliases; `assets` is
a resolved view, not a second stored inventory. Embedded holders bind to an
explicit graph owner, while graph-node holders use their own graph. Source views
expose distinct live objects without flattening their namespaces or recursively
exposing the contents of containers.

## Approved Membership Model and Migration

A `DiscreteAssetWallet` is a non-hierarchical `Subgraph` owned by the graph.
Its host refers to the wallet by UID; the graph serializes wallet and items once
apiece. Membership is ordered and unique, references resolve to the actual graph
members, and missing references fail visibly. Groups express their own meanings:
an item can belong to both a possession group and an equipment group. They do
not reparent members or impose universal exclusive custody. Checks are pure;
create wallets at accepted setup or mutation boundaries, never during reads.

`HasAssets` composes the independent counted and discrete capabilities. A
singleton definition selects counted holdings; graph items, including tokens,
select discrete holdings. String pool keys remain explicit counted-wallet usage.
The sandbox binds its player holder to the scope and portable containers to their
owning tokens. Assembly still needs to build its graph-backed slot membership on
this same primitive, retaining slot policy and owner binding.

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
or discrete wallet membership. It remains the story-level convenience for the current
holder surface. The cross-family `tangl.mechanics.transaction` helper now carries
the shared spec/offer/commitment/receipt shape for broader shops, services,
assembly assignment, holder-local asset movement, catalog-backed token creation,
and mixed writeback.

The existing transaction mechanism coordinates preflight and mutations of the
discrete and countable wallets, preserving holder and counterpart policy.

A higher-level trade manager can later compare aggregate values and actor
biases before delegating to the transaction manager.

See `../../../mechanics/TRANSACTION_OFFER_DESIGN.md` for the shared
spec/offer/commitment/receipt vocabulary that generalizes this manager across
provisioning, shops, services, assembly assignment, and future relationship
writeback.

## Known Limitations

Graph-backed holder integration now supports the Grotto custody witness. It is
not a complete inventory system:

- Assembly slot membership still uses its existing owner-bound assignment maps;
  convergence with the shared discrete wallet is a separate slice.
- Sandbox `SandboxScope.player_assets` remains the ready-at-hand player stand-in.
- Ambiguous matching and nested-container exposure remain consumer policy rather
  than a universal namespace-flattening rule.
- Isolated JSON Patch member-event restoration remains tracked separately in #655.
