# ScriptManager query facade migration (v3.7)

## Overview

Direct access to `ScriptManager.template_registry` is deprecated in favor of the
query facade methods :meth:`find_template` and :meth:`find_templates`. The
facade introduces anchored identifier resolution for unqualified names and keeps
provisioners decoupled from registry internals.

## Identifier resolution changes

- **Unqualified identifiers** (for example, `"guard"`) now search the selector's
  scope chain from most specific to global. A request from `village.store` walks:
  `village.store.guard` → `village.guard` → `guard`.
- **Qualified identifiers** (for example, `"countryside.guard"`) bypass scope
  filtering and match exactly, enabling intentional cross-scope references.

## Migration steps

1. Replace registry lookups with the facade:
   ```python
   # Before
   template = world.script_manager.template_registry.find_one(label="guard")

   # After
   template = world.script_manager.find_template(identifier="guard")
   ```
2. Provide a selector when you need scope-aware lookup:
   ```python
   template = world.script_manager.find_template(
       identifier="guard",
       selector=store_block,
   )
   ```
3. Use plural queries for collections:
   ```python
   guards = world.script_manager.find_templates(archetype="guard")
   ```

## Deprecation timeline

- v3.7: Facade available; registry access emits `DeprecationWarning`.
- v3.8: Warnings may be promoted to errors in strict environments.
- v4.0: Direct registry access removed.

## Provisioning behavior

Provisioners now rely on :class:`ScriptManager` for template resolution and only
fall back to raw registries for legacy contexts. Anchored lookups ensure that
unqualified identifiers used in roles or requirements materialize templates from
the correct scope without pre-provisioning every scene.
