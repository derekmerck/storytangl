# Mechanics: Assembly

Composable slot-based containers for arranging components into loadouts. Slots use
`tangl.core.entity.Entity.matches()` to determine eligibility, enabling both declarative
criteria (tags, type checks) and custom predicates without duplicating selector logic.

Key pieces:

- `Slot` / `SlotGroup`: selection criteria and aggregate constraints.
- `SlottedContainer`: generic container that enforces slot rules and optional resource budgets.
- `HasSlottedContainer`: mixin for embedding a container on an entity (facet-style).
- `BudgetTracker`: helper for tracking resource usage (power, weight, etc.).

See `examples/vehicle.py` for usage patterns.

Aggregate helpers operate over the container's current `all_components()`
result exactly as-is.

```python
defense_total = vehicle.vehicle_loadout.get_aggregate("defense_bonus")
carried_weight = vehicle.vehicle_loadout.get_aggregate_cost("weight")
capabilities = vehicle.vehicle_loadout.get_aggregate_tags("capabilities")
```

`OutfitManager` has been promoted out of `assembly.examples` into
`tangl.mechanics.presence.outfit` because active presence mechanics depend on it
as a real family surface rather than a demo.
