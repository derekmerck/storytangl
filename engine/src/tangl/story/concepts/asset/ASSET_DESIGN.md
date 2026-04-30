# tangl.story.concepts.asset - Design Notes

> Status: Implemented vocabulary, holder, transaction, and sandbox integration slice.

## Position

Assets are story concepts layered over core tokens and graph relationships.
They are not a separate inventory engine.

This package currently defines:

- `AssetType`: a singleton definition for tokenizable, lightly stateful assets.
- `CountableAsset`: a fungible asset definition tracked by quantity.
- `AssetWallet`: a compact counter for fungible assets.
- `HasAssets`: a story-level facet for nodes that hold wallet counts and
  nominate discrete asset tokens into namespaces.
- `AssetTransactionManager`: a small preflight-and-mutate service for transfers
  between `HasAssets` holders.

Discrete assets should be represented as `Token[AssetTypeSubclass]`. The
singleton describes the platonic item, while the token holds graph-local state.

## Holder Model

`HasAssets` is the current holder surface. It publishes:

- `asset_holder`: the holder itself;
- `asset_wallet` and `wallet`: the fungible wallet;
- `assets` and `inv`: the holder's nominated discrete asset tokens.

Those symbols are intentionally ordinary namespace contributions, so roles,
settings, sandbox scopes, and other story machinery can prefix or inspect them
without learning a separate inventory engine.

## Deferred Relationship Model

The current `HasAssets.assets` map is a lightweight staging surface. The later
relationship-backed shape is:

- locations, actors, players, containers, and other story nodes may opt in as
  asset holders; the sandbox package now uses this directly by making
  `SandboxLocation` a holder and `SandboxScope.player_assets` a lightweight
  ready-at-hand holder;
- fungible assets live in a wallet on the holder;
- discrete assets are graph nodes linked by an ownership or holding relation;
- inventory affordances are projected from the current cursor namespace plus
  ready-at-hand holders such as the player avatar.

The holding relation should be built as a general relationship mechanism, not
as asset-only code. The old `Associating` and `Connection` scratch designs are
better prior art for relationship preflight and acceptance than for inventory
storage itself.

## Transaction Model

`AssetTransactionManager` validates a complete transfer before mutating wallets
or holder asset maps. Once the graph relationship model exists, the same manager
can:

- move discrete asset tokens by updating holding/ownership links;
- debit and credit `AssetWallet` counts;
- use existing `on_link` and `on_unlink` hooks for registration and cleanup.

A higher-level trade manager can later compare aggregate values and actor
biases before delegating to the transaction manager.

## Future Core Hooks

Core currently observes link changes with `on_link` and `on_unlink`. Asset
holding will eventually want preflight hooks shaped like `on_can_link` and
`on_can_unlink`, but those should be introduced as general graph relationship
hooks when a concrete relationship slice needs them.

## Known Limitations And TODO

The current slice is intentionally sufficient for sandbox affordance
experiments, not a complete inventory system.

- `HasAssets.assets` is a holder-local map, not yet a graph-backed ownership
  subgraph. It is good enough for "player has key" checks, but not enough for
  full persistence of container membership, room inventories, or ownership
  history.
- Discrete transfers currently move tokens between holder maps. Slice 2 should
  replace or back this with a first-class holding relation so graph topology is
  the source of truth.
- Transaction preflight asks holder policy methods (`can_give_*` and
  `can_receive_*`) directly. A later relationship framework should generalize
  this into preflight/acceptance rules that assets, connections, attachments,
  and other mutable associations can share.
- `AssetTransactionManager` does not yet batch mixed discrete and fungible
  changes atomically. The trade manager should build on a batched transaction
  plan that validates every leg before mutating anything.
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
  replace holder-local maps with a relationship-backed holding subgraph.
