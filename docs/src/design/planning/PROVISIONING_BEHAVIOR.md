# Provisioning Behavior for Authors

## Why it Matters
When you reference actors or locations from scripts, the VM has to decide whether to reuse an
existing entity or create a new one. Understanding that decision helps you predict narrative
outcomes, especially when multiple templates could satisfy the same role.

## Quick Rules

1. **Existing always wins** – Reusing an existing node costs between `10` and `30` depending on
   proximity. Creating a new node costs `200`, so reuse wins unless you explicitly set
   `requirement_policy: CREATE`.
2. **Scope still applies** – Templates tagged with `scope` (scene, block, ancestor selectors) are only
   considered if the requesting node is in scope. See :doc:`TEMPLATE_SCOPE` for YAML examples.
3. **Template references (`*_template_ref`) short-circuit GraphProvisioner** – Those requirements go
   straight to TemplateProvisioner. Inline templates (`*_template`) continue to work.
4. **Everything is audited** – Planning receipts now include `selection_audit`, making it easy to see
   which offers were considered and why a specific one won.

## Author Controls

| Need                           | How to express it |
|--------------------------------|-------------------|
| Force a fresh instance         | Set `requirement_policy: CREATE` on the role/setting. |
| Prefer scene-local reuse       | Declare the affordance or template inside the scene/block so it is
                                   in scope and has low proximity cost. |
| Share a template everywhere    | Add `scope: null` to the template to mark it global. |
| Diagnose unexpected selections | Inspect planning logs or use the debugger snippet below. |

## Debugging Example

```python
from tangl.vm.debug import PlanningDebugger

# After running a frame
receipt = next(r for r in frame.records if isinstance(r, PlanningReceipt)
PlanningDebugger.print_receipt(receipt)
```

The report lists every requirement, the offers considered, their cost/proximity, and the winning
provider. Use it to confirm that your template scopes and requirement policies line up with your
intent.

## Best Practices

- Declare generic NPCs/locations at the world or scene level so they can be reused cheaply.
- Override `requirement_policy` only when you truly need bespoke instances.
- Keep template names descriptive—receipts log `template_ref`, which shows up in debugging tools.
- When troubleshooting, check `selection_audit` before changing YAML; the audit often reveals that the
  desired template was out of scope or more expensive than an existing option.
