# Cost Model & Offer Selection

## Overview
Provisioning now uses a deterministic cost model so planners can justify every choice. Each offer
reports its **base cost** (operation type) and a **proximity modifier** derived from the graph
structure. Selection sorts by the sum of those two values and breaks ties with the provisioner id,
making replay stable and debuggable.

## Base Costs

| Operation | Base Cost | Description |
|-----------|-----------|-------------|
| `DIRECT`  | 10        | Reuse an existing node without modifications. |
| `LIGHT_INDIRECT` | 50 | Update an existing node in place. |
| `HEAVY_INDIRECT` | 100 | Clone and evolve an existing node. |
| `CREATE`  | 200       | Instantiate a new node from a template. |

These values map to :class:`~tangl.vm.provision.offer.ProvisionCost` and live on
:class:`~tangl.vm.provision.offer.ProvisionOffer.base_cost`.

## Proximity Modifiers

Graph distance influences the final score for EXISTING offers:

| Relationship  | Modifier | Example |
|---------------|----------|---------|
| Same block    | `+0`     | Node already attached to the requesting block. |
| Same scene    | `+5`     | Node and requester share the same immediate parent subgraph. |
| Same episode  | `+10`    | Node lives elsewhere in the current episode. |
| Elsewhere     | `+20`    | Node is outside the current episode hierarchy. |

These values are added on top of the base cost; the sum is stored on `offer.cost`. Template
provisioning does **not** apply a proximity modifier because it always creates a new instance.

## Selection Algorithm

1. Collect offers from all provisioners and attach metadata (provisioner id, layer, selection
   criteria).
2. Deduplicate EXISTING offers per provider so the cheapest proposal survives.
3. Sort the remaining offers by `(cost, proximity, registration order)`.
4. Record metadata (reason, all offers, selected provider) for the requirement.
5. Accept the winning offer and emit :class:`~tangl.vm.provision.offer.BuildReceipt` plus a
   `selection_audit` entry in :class:`~tangl.vm.provision.offer.PlanningReceipt`.

Because template creation costs `200` and distant reuse tops out at `10 + 20 = 30`, existing entities
will always win unless the requirement policy is explicitly `CREATE`.

## Debugging & Auditing

Use :class:`tangl.vm.debug.PlanningDebugger` to print audit data during development:

```python
from tangl.vm.debug import PlanningDebugger

receipt = frame.records[-1]  # last PlanningReceipt emitted by the frame
PlanningDebugger.print_receipt(receipt)
```

Each entry lists all offers, their costs, proximity descriptions, and which provisioner won.
Developers can also call ``PlanningDebugger.compare_offers(offers)`` to compare raw offers before the
planner runs.

## Troubleshooting

- **“Why did it reuse a distant node?”** – Existing nodes max out at `30`, so they beat template
  creation unless the requirement policy is `CREATE` or no existing offers qualify.
- **“Why was my template ignored?”** – Templates only run when the requirement includes
  `template_ref` or `template`. GraphProvisioner skips those requests.
- **“How do I force a fresh instance?”** – Set `requirement_policy: CREATE` in the script. The cost
  model still records the offer but GraphProvisioner will decline to compete.
- **“The audit trail is empty.”** – Ensure planning handlers returned a
  :class:`~tangl.vm.provision.offer.PlanningReceipt`. Off-main-thread tests may need to call
  :func:`tangl.vm.dispatch.planning.plan_collect_offers` / `plan_select_and_apply` to populate it.
