Design Plans
============

Architecture and rationale for the published StoryTangl subsystems. Current
contracts come first; notes kept for their history are listed separately at
the end.

Prospective narratives and the capabilities they would exercise live in
:doc:`../world-designs/index`; those briefs do not define implemented engine contracts.

See also
--------
- The practical design note for each package lives beside its code and is
  included in the API reference, for example :doc:`../api/vm/VM_DESIGN`,
  :doc:`../api/story/STORY_DESIGN` and :doc:`../api/service/SERVICE_DESIGN`.
  Pages here describe the models; those notes say how a package realizes them,
  and lead on to the package's API. :doc:`../notes/reference/code_adjacent_design_docs`
  lists them all.

.. toctree::
   :maxdepth: 4

   glossary

   story/philosophy
   story/NARRATIVE_CONTROL
   story/SEMANTIC_PROJECTIONS
   SIMPLIFICATION_SPEC
   CANON_AND_REALIZATION

   core/DEREF_DESIGN
   core/HOOK_REF

   story/MECHANICS_FAMILIES
   story/EPISODE_SYUZHET_RENDERING
   story/PROSE_AUTHORING
   story/CONCEPT_LINKED_PROSE
   story/STORYTANGL_WIDGET_VOCAB
   story/WIDGET_CONTRACT_RECONCILIATION
   story/WIDGET_WIREFRAMES
   story/brand/README
   story/brand/v1_0/USAGE
   story/GENRE_AUDIT_NOTES
   story/bundles/carwars/EXTENSIONS
   story/bundles/credentials/EXTENSIONS
   story/bundles/elefant_hunt/EXTENSIONS
   story/bundles/training/EXTENSIONS
   story/INTERACTION_VOCABULARY
   story/JOURNAL_COMPOSE_CONTRACT
   story/BEAT_COMPOSITION
   story/PRESENCE_PROSE_CONTRACT
   story/CONDITIONAL_NARR
   story/ASSET_TYPE_DESIGN
   story/HUB_FANOUT
   story/menu_block
   story/compilers
   story/notes-create_world

   planning/AFFORDANCE_MODEL
   planning/COST_MODEL
   planning/PROVISIONING
   planning/PROVISIONING_BEHAVIOR
   planning/TEMPLATE_SCOPE
   planning/TEMPLATES

   traversal/NAV_DESIGN
   traversal/ENTRY_RESOLUTION

   service/SERVICE_DESIGN
   service/BACKEND_FRAGMENT_RECONCILIATION
   service/RESPONSE_TYPES
   service/FRAGMENT_STREAM_CONTRACT

   MEDIA_DESIGN
   GENERATIVE_MEDIA_DESIGN

Earlier notes
-------------

Kept for context. Each says at its top whether it is historical or stale. The
two traversal notes use retired names but still describe the intended single
source and single sink form for containers, which the current code only partly
implements.

.. toctree::
   :maxdepth: 1

   planning/PLANNING_DESIGN
   story/CONCEPT_PROV_DESIGN
   core/CONTENT_ADDRESSABLE
   traversal/notes-canonical_form
   traversal/notes-sinks
