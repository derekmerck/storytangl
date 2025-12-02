# Mechanics: Assembly

Composable slot-based containers for arranging components into loadouts. Slots use
`tangl.core.entity.Entity.matches()` to determine eligibility, enabling both declarative
criteria (tags, type checks) and custom predicates without duplicating selector logic.

Key pieces:

- `Slot` / `SlotGroup`: selection criteria and aggregate constraints.
- `SlottedContainer`: generic container that enforces slot rules and optional resource budgets.
- `HasSlottedContainer`: mixin for embedding a container on an entity (facet-style).
- `BudgetTracker`: helper for tracking resource usage (power, weight, etc.).

See `examples/vehicle.py` and `examples/outfit.py` for usage patterns.
