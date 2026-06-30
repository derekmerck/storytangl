# Transaction Offers and Commitments

```{storytangl-topic}
:topics: association, transaction, provision
:facets: design, notes
:relation: defines
:related: assembly, assets, provisioning, credentials
```

**Status:** FIRST HELPER LANDED — `tangl.mechanics.transaction` provides an
ephemeral `TransactionOffer`, ordered rollback-capable commitments, plain
preflight/receipt data, and a neutral vehicle garage proof. This is still not a
full shop engine or global transaction arbiter.
**Scope:** the common offer/accept/writeback shape shared by provisioning,
association, shops, trades, services, component install flows, and future
credential/chopshop compliance.
**Prior art:** VM `Requirement` / `ProvisionOffer`, story asset
`AssetTransactionManager`, assembly `ComponentManager` and connector association,
legacy `scratch/legacy/core/core-30/graph_handlers/associating.py`, and the
CarWars garage/shop proof.

---

## The Unifying Claim

Provisioning and transactions are the same family of operation:

```text
request/spec + current context
  -> validated offers
  -> accept an offer or batch
  -> apply commitments
  -> record durable state and receipt metadata
```

Provisioning is the phase-local version: a requirement needs a provider, handlers
return offers, the resolver accepts one, and the requirement is bound to the
provider. A shop/trade/service is the durable update-phase version: a move
payload asks for an exchange or association, handlers return validated offers, an
accepted offer commits wallet debits, token creation/movement, slot assignments,
stat mutations, or other writeback.

The useful abstraction is not "shop." It is a validated promise to perform one
or more commitments.

---

## Vocabulary

### Spec

A **spec** is plain request data. It says what is being asked for, without
callbacks and without hidden mutation.

Examples:

- a VM `Requirement`;
- "buy these catalog items";
- "install this component in this slot";
- "pay 10 gp for 10 hp of healing";
- "confiscate this credential token";
- "connect this plug to that socket."

Specs may be serialized or logged when useful. They are not themselves proof that
the operation is currently legal.

### Offer

An **offer** is an ephemeral, validated promise produced from a spec and current
context. It may carry callbacks, bound objects, priorities, policies, previews,
and commit functions. Because of those callbacks and object references, offers
are not durable persistence objects.

Existing `ProvisionOffer` already follows this rule: it is a ranked candidate
with a callback and `guard_unstructure = True`. A transaction offer should follow
the same durable/ephemeral split.

### Commitment

A **commitment** is one source/target/effect leg inside an offer. Its core shape
is bilateral:

```text
source can provide/send/debit X
target can receive/accept/credit X
```

For a trade, both directions are checked:

```text
A can send X
B can receive X
B can send Y
A can receive Y
```

`X` and `Y` are not necessarily tokens. They may be fungible wallet counts, stat
deltas, service capacity, catalog materialization, time, ownership changes, slot
associations, connector pairings, or graph links.

### Accept

**Accepting** an offer rechecks preflight, then applies all commitments as one
logical writeback. If any commitment fails, no durable partial mutation should
survive. A first implementation may use simple reverse-order rollback; later
graph/runtime integration may provide a richer transaction journal.

### Receipt

A **receipt** is plain result data. It records what happened, what was paid,
what was created or moved, what service was performed, and what changed. Receipts
are suitable for round notes, replay diagnostics, journal fragments, or audit
metadata. Receipts do not carry callbacks.

---

## Provisioning In This Vocabulary

| Current Provisioning Term | Unified Vocabulary |
| --- | --- |
| `Requirement` | spec: a request for a provider matching selector/policy |
| `ProvisionOffer` | offer: a ranked promise to satisfy the requirement |
| `EXISTING` | commitment provides an already-present entity |
| `CREATE` | commitment materializes from a template/catalog recipe |
| `TOKEN` | commitment provides a graph-local token over a singleton/catalog entry |
| `UPDATE` | commitment applies a delta to an existing provider |
| `CLONE` | commitment copies an existing provider and applies a delta |
| offer callback | accept/provide callback |
| `provider_id` | accepted binding |
| resolution metadata | receipt/audit of selected policy, step, cursor, reason |

This does not require rewriting provisioning. It gives us common language for
why provisioning callbacks are ephemeral, why requirements and resolution
metadata are durable, and why catalog-backed shops look more like provisioners
than like static inventories.

---

## Association In This Vocabulary

The legacy `Associating` handler had the right symmetry:

```text
can_associate_with(A, B)
  = all A.on_can_associate(B)
  + all B.on_can_associate(A)

associate_with(A, B)
  = recheck
  -> A.on_associate(B)
  -> B.on_associate(A)
  -> mutate relationship
```

The new vocabulary preserves that idea without requiring every participant to be
an `Associating` node. The symmetry moves into the commitment layer:

- `can_*` checks are pure and may run many times during planning and UI
  projection.
- source and target both validate capacity, consent, legality, or policy.
- commit happens only after every commitment passes.
- post-commit hooks/receipts happen after durable mutation.

Component assignment, connector pairing, asset transfer, shop purchase, healing,
credential confiscation, and service use are all association-shaped when viewed
as commitments.

---

## Parameter-Bound Moves

The normal UI rule still stands: do not offer invalid choices. Transaction
offers cover the narrower case where the move envelope is valid but the submitted
payload may not be.

Example:

```text
available move: buy things
payload: {items: [foo, bar, baz]}
```

The move kind is valid because the current shop can transact. The payload may be
invalid because `foo` is not available, the player cannot afford the aggregate
cost, the target holder cannot receive one of the items, or a chosen install slot
cannot accept a component. The handler should bind the payload into a concrete
spec, ask for a validated offer, and reject before writeback if no offer can be
accepted.

This is the same server-side authority rule used by typed widget accepts: UI
constraints help, but update logic validates the submitted payload.

---

## Source Modes

Sellers and service providers do not always hold the exact thing the player will
receive.

### Held Token

The provider owns a discrete token. Accepting the offer moves that token.

### Catalog Provision

The provider owns a catalog/provisioner and can create a token on demand.
Accepting the offer materializes a fresh token, possibly decrementing stock,
daily capacity, or another provider ledger.

### Fungible Or Service Capacity

No token moves. Accepting the offer mutates ledgers or state:

```text
buyer.cash -= 10
healer.healing_capacity -= 10
buyer.hp += 10
```

The same bilateral checks apply: the buyer can pay, the seller can receive
payment, the healer can provide the service, and the patient can receive the
state change under current rules.

---

## First Implementation Slice

The first implementation is deliberately smaller than a general shop engine.

Landed proof:

1. `TransactionOffer` stays ephemeral and `guard_unstructure = True`, matching
   the same callback/live-object boundary as `ProvisionOffer`.
2. `TransactionCheck` and `TransactionReceipt` are plain data.
3. `CountableTransferCommitment` proves bilateral wallet debit/credit checks.
4. `RegistryAddCommitment` proves explicit shape change during accepted
   writeback: a prepared graph item can enter the registry only when the offer
   commits.
5. `ComponentAssignmentCommitment` proves owner-bound component manager
   assignment, replacement, post-assignment validation, and rollback.
6. The neutral vehicle garage test buys and installs a component, then proves
   the resulting graph/loadout state survives `Graph.unstructure()` /
   `Graph.structure()`.
7. Rejection before mutation and mid-commit rollback are both covered.

Still recommended for the next consumer-facing slice:

1. Add a neutral shop/garage example module or world-facing fixture over the
   existing vehicle component manager.
2. Add commitment legs only when a real consumer forces them:
   - discrete token move between holders;
   - catalog-backed token creation with stock/capacity;
   - replacement return to inventory;
   - service/stat mutation;
   - graph link/unlink.
3. Test aggregate insufficient funds, unavailable catalog/provider capacity,
   incompatible install targets, and multi-offer/batch selection.
4. Keep transaction offers ephemeral; persist only resulting state and receipts.

Out of scope for the first slice:

- generic global trade arbitration;
- author-facing `on_associate` dispatch hooks;
- graph relationship-backed ownership migration;
- multi-turn pending offers;
- a full shop game UI;
- all possible commitment leg types.

---

## Why This Helps

The same vocabulary covers:

- VM provisioning offers;
- asset transactions and future holding relations;
- assembly slot assignment and connector association;
- CarWars garage/shop install and repair flows;
- credentials confiscation, return, planting, or bribery;
- robot/chopshop parts plus permits/compliance;
- pure service transactions such as healing for money or time.

That common shape should make future issue grooming simpler: when a feature asks
"can X move from here to there?", "can this service be provided?", or "can this
association commit?", it should be framed as a spec producing validated offers,
whose accepted commitments mutate durable state and emit a receipt.
