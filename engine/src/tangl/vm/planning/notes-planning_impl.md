Minimal planning data path
--------------------------

Flow (one frame, one cursor):

1.	**Collect**: Planning handlers publish offers (potential updates) for unsatisfied Dependency / Affordance edges visible in Context.scope.

2.	**Select**: A single “selector” handler merges and de-duplicates offers, applies policy (hard/soft, priority), and decides which to accept.

3.	**Apply**: For each accepted offer, call ``offer.accept(ctx)`` to compute a provider.
	    The selector binds the provider and records receipts.

      - If Frame.event_sourced=True, your WatchedRegistry captures mutations → Events → a Patch is added in FINALIZE (already implemented).

      - If not event-sourced, we still mutate the live graph.

4.	**Receipt**: The selector returns a summarized PlanningReceipt (counts + unresolved hard requirements). That goes into the PLANNING phase outcome and into ctx.call_receipts.

Offer resolution policy
-----------------------

- **Unit of arbitration**: one Requirement → many offers → choose one.

- **Default rule**: choose lowest priority; break ties by earlier emission order.

- **Hard/soft**: if no accepted offer for a hard requirement, mark it unresolved in the PlanningReceipt.unresolved_hard_requirements. (Selector does that automatically via the BuildReceipt(accepted=False, reason='unresolvable') return path.)

- **Conflicts** (future): if two offers touch the same attribute of the same entity, use the same arbitration map: (entity_uid, attr) key → pick lowest priority. You can add that once you encounter the need.

