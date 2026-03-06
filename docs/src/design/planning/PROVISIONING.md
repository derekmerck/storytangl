# Provisioning Pipeline

## Overview
Provisioning is the process the VM uses to satisfy :class:`~tangl.core.requirement.Requirement`
objects before the story advances. Each frontier node exposes requirements for actors,
locations, or resources. Provisioners compete to satisfy those requirements by producing
:class:`~tangl.vm.provision.offer.Offer` objects. The planner selects the best offer for each
requirement, applies it, and records a :class:`~tangl.vm.provision.receipt.BuildReceipt` for auditing.

## Provisioner Sequence

1. **GraphProvisioner** – Finds already-instantiated nodes that satisfy the requirement.
2. **TemplateProvisioner** – Instantiates templates (see below) if the requirement references one.
3. **Updating / Cloning Provisioners** – Modify or duplicate existing entities when requested.

Provisioners may return zero or more offers. The planner picks the lowest-cost viable offer, so
custom provisioners should surface clear cost semantics.

## TemplateProvisioner Flow

Template provisioning is the most common path for casting roles and populating settings:

1. **Requirement intake:** Requirements coming from story scripts now include `template_ref`
   when a `RoleScript` or `SettingScript` references a template label. Inline templates are still
   supported via the legacy `template` dict.
2. **Template lookup:** The provisioner pulls templates from `world.template_registry`. Templates
   are :class:`~tangl.ir.core_ir.base_script_model.BaseScriptItem` instances and already include a
   content-addressed hash (`content_hash`).
3. **Scope filtering:** Before an offer is created, `_is_in_scope` validates that the template’s
   `scope` allows it to be used for the current source node. See
   :doc:`../authoring/TEMPLATE_SCOPE` for examples of block, scene, and ancestor filtering.
4. **Offer creation:** Offers embed the template, its registry label, and a short content identifier
   (`template.get_content_identifier()`). No additional hashing is necessary because
   :class:`~tangl.core.content_addressable.ContentAddressable` handles it.
5. **Build step:** When selected, the offer is converted into a concrete entity. The provisioner
   resolves `obj_cls`, hydrates the payload from the template, applies requirement overrides, and
   writes a build receipt including the template reference and hash for provenance.

If any step fails—missing template, scope rejection, or unresolved class—the provisioner simply
returns no offers and logs a debug/warning message, allowing other provisioners or policies to
handle the requirement.

## Scope Semantics

Template scope determines *where* a template can be used:

- **Global templates** (`scope=None`) can satisfy any role/setting.
- **Scene templates** (inferred `parent_label`) are limited to blocks within that scene.
- **Block templates** (inferred `source_label`) can only fill roles/settings in the block where the
  template was declared.
- **Advanced selectors** like `ancestor_labels` and `ancestor_tags` enforce ancestry constraints.

Because scope enforcement runs inside the TemplateProvisioner, authors get immediate feedback in
planning logs when a template reference is out of scope. Refer to :doc:`../authoring/TEMPLATE_SCOPE`
for author-facing guidance and YAML examples.

## Debugging Provisioning

- Enable debug logging for `tangl.vm.provisioners.template_provisioner` to see why templates are
  rejected (missing source, parent mismatch, missing tags, etc.).
- Inspect build receipts in the ledger; each contains `template_ref` and `template_hash` so you can
  trace exactly which template was instantiated.
- Use `world.template_registry.find_all(content_hash=...)` to locate duplicate templates if you
  suspect multiple declarations share the same content.

## Cost Model & Auditing

Offer selection is now deterministic and proximity-aware:

- **Base costs** come from :class:`~tangl.vm.provision.offer.ProvisionCost` (e.g., `DIRECT=10`,
  `CREATE=200`).
- **Graph proximity** adds a modifier before the planner compares offers:

  | Scenario        | Modifier |
  |----------------|----------|
  | Same block     | `+0`
  | Same scene     | `+5`
  | Same episode   | `+10`
  | Elsewhere      | `+20`

- **Template offers** use the fixed create cost (`200`) so nearby existing providers almost always
  win unless the requirement policy is `CREATE`.

Every call to :func:`~tangl.vm.provision.resolver._select_best_offer` records audit metadata. The
final :class:`~tangl.vm.provision.offer.PlanningReceipt` includes `selection_audit`, a list of the
offers considered for each requirement plus the reason the winner was chosen. Developers can print
these decisions with :class:`tangl.vm.debug.PlanningDebugger`.

See :doc:`COST_MODEL` for an extended breakdown of the calculations and troubleshooting tips.
