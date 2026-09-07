# Presentation boundary

`tangl.presentation` owns small, domain-neutral syntax that a client may
render, arrange, or solicit: interaction intent, styling and staging hints,
and key/value display records. It depends only on Pydantic, Core value
machinery, and shared type hints.

It is not a widget library, renderer, authority source, transport surface, or
alternate journal. Journal fragments retain their identity, provenance,
persistence, replay, grouping, update, and deletion semantics; they may carry
presentation values. Service envelopes likewise carry values without owning
them. Backend state remains authoritative for every action.

## Status

Current — Slice 1 owns interaction intent, display values, and rendering or
staging hints. It has no presentation dispatch, projected-state types, UX
events, widget classes, client bindings, or transport policy; those remain
outside this slice.
