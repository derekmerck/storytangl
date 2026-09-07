# Presentation boundary

`tangl.presentation` owns small, domain-neutral syntax that a client may
render, arrange, or solicit: interaction intent, styling and staging hints,
transient guidance, command grammar, and disclosed projected state. It depends
only on Pydantic, Core value machinery, and shared type hints.

It is not a widget library, renderer, authority source, transport surface, or
alternate journal. Journal fragments retain their identity, provenance,
persistence, replay, grouping, update, and deletion semantics; they may carry
presentation values. Service envelopes likewise carry values without owning
them. Backend state remains authoritative for every action.

## Status

Current — Slice 2 also owns `UxEvent`, advisory grammar, `ProjectedState`,
`ProjectedSection`, section value variants, info affordances/state, and the
opaque `ProjectionRequest` descriptor that lower-layer providers consume.
`presentation_dispatch` is the application-level contributor registry for
presentation tasks; its decorators are the registration vocabulary for generic
mechanics. Service retains operations, outer dispatch, response
envelopes, and remote hydration; its fold includes this registry with story,
world, and runtime-local authorities. There is no widget class, client binding,
or transport policy here.
