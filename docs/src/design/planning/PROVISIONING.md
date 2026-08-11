# Provisioning Pipeline

```{storytangl-topic}
:topics: provisioning
:facets: overview, design
:relation: defines
:related: open_link, template, token, phase_ctx
```

> **Status:** Current runtime contract.
> **Authority:** `tangl.vm.provision`, `tangl.vm.dispatch.do_provision`, and
> `tangl.vm.runtime.frame.Frame._run_planning_phase` define the executable
> behavior. [AFFORDANCE_MODEL.md](AFFORDANCE_MODEL.md) defines the broader
> open-link vocabulary.

Provisioning binds unresolved requirements on graph edges to providers. It is
the VM operation that turns a partially specified frontier into traversable
runtime topology without requiring authored code to choose concrete providers
in advance.

## Runtime shape

- `Requirement` is a serializable `Selector` plus provisioning policy and
  resolution metadata.
- `Dependency`, `Affordance`, and `Fanout` are graph edges that carry the open
  relationship into planning.
- `ProvisionOffer` is an ephemeral, ranked proposal. Its callback may return an
  existing provider or materialize one; offers are not persistence records.
- `Resolver` gathers, filters, ranks, accepts, and binds offers.
- Provisioners donate candidates from existing graph members, authored
  templates, token catalogs, inline templates, update/clone formulas, media
  inventories, and dispatch extensions.

## Lifecycle

Player input begins a VM cycle. After traversing the selected edge, PLANNING
prepares both the current node and its immediate successor frontier:

```text
selected edge
  -> move cursor
  -> provision current node
  -> provision each immediate successor
  -> PREREQS / UPDATE / JOURNAL / FINALIZE / POSTREQS
  -> present the next live choices
```

This one-step-ahead rule is what makes the next choices inspectable before they
are presented. Normal interactive traversal should not wait until a choice is
selected to discover what that choice points to. JIT entry at PLANNING is kept
for startup, debugging, and explicit out-of-order entry.

`do_provision(...)` is side-effect-only. Provisioning handlers mutate graph
bindings in place and must return `None`; there is no phase-level
`PlanningReceipt` result stream. Accepted-offer summaries live on the
`Requirement` as resolution metadata for diagnostics.

## Matching and ranking

`Resolver.gather_offers(...)` produces one deterministic ordered set.
`tangl.vm.provision.matching.offer_sort_key()` is the canonical ranking
contract and prefers, in order:

1. provisioning policy tier (`EXISTING`, `UPDATE`, `CLONE`, `CREATE`, then
   debug stubs);
2. scope distance;
3. distance from the caller;
4. exact kind matches;
5. selector specificity;
6. explicit offer priority;
7. creation sequence.

This is not the retired fixed-cost model described in the historical
[COST_MODEL.md](COST_MODEL.md). Code and authoring guidance should name the
fields above rather than promise numeric costs that the live resolver does not
use.

## Materialization and persistence

Templates become graph entities through the normal `EntityTemplate` and graph
factory materialization path. Provider identity is stored on the requirement by
UUID, and graph round trips restore that reference through the owning registry.
Offer callbacks, transient candidate objects, and unaccepted preview offers are
not durable graph state. When an explicitly allowed STUB offer is accepted, its
provider is added to the graph and linked like any other accepted provider; the
link therefore survives graph persistence.

Planning reads may preview whether a requirement is viable, but ordinary setup
and rendering must not accidentally materialize lazy candidates. Provider and
template materialization normally belongs at the PLANNING boundary. The bounded
exception is an explicitly episode-latent destination: if a presented action
still carries a deferred destination plan, selecting it may provision that
destination before traversal. Entities created as consequences, and other
committed non-topological state changes, belong in UPDATE.

## Related contracts

- [Open Links](AFFORDANCE_MODEL.md) — the requirement-bearing edge model.
- [Template Scope](TEMPLATE_SCOPE.md) — authored admission and scope rules.
- [Provisioning Behavior](PROVISIONING_BEHAVIOR.md) — historical author-facing
  guidance retained for provenance; its cost examples are not current.
- `engine/src/tangl/vm/VM_DESIGN.md` — VM phase and authority contract.
