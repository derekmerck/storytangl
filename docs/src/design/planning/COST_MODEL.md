# Cost Model & Offer Selection

> **Historical migration note.** StoryTangl formerly ranked provisioning
> offers through fixed numeric `ProvisionCost` values and emitted
> `PlanningReceipt` / `BuildReceipt` records for diagnostics. That model, its
> `PlanningDebugger`, and its numeric troubleshooting guidance have been
> retired.

The live resolver uses a deterministic structural ordering rather than summed
costs. See [PROVISIONING.md](PROVISIONING.md) for the current lifecycle,
`offer_sort_key()` ranking fields, persistence behavior, and diagnostics
contract. Historical investigations that mention cost totals or planning
receipts should not be used as implementation guidance.
