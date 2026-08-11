# Media Subsystem Design

> **Status:** Current public entry point
> **Canonical package contract:**
> ``engine/src/tangl/media/MEDIA_DESIGN.md``

This page records media's place in the episode-to-syuzhet and delivery pipeline.
The code-adjacent package note is the single authority for media types,
provisioners, creator lifecycle, scoped inventories, and implementation status.
The former long version of this page duplicated that contract while preserving
retired names such as ``MediaRequirement``, ``MediaDependency``, and
``MediaForge``. Git history retains that roadmap material.

## Contract Summary

Media is resource indirection and provisioning for non-textual content. It does
not own story truth, narrative policy, journal ordering, transport URLs, or
client layout.

```text
semantic story or mechanic state
    -> presentation-safe projection
    -> renderer-neutral MediaSpec
    -> optional backend-specific adapted spec
    -> provisioned content-addressed MediaRIT
    -> MediaFragment in the JOURNAL stream
    -> service dereference
    -> client presentation
```

Those stages are intentionally distinct:

- A **semantic projection** exposes only the story facts appropriate for
  presentation. It remains owned by Story, a mechanic, or world domain logic.
- A **``MediaSpec``** states what resource should be selected or created without
  becoming semantic authority.
- **Adaptation and creation** are media/backend concerns. A proof backend such
  as DiceBear is replaceable and should not leak into Story, Presence, or
  Credentials.
- A **``MediaRIT``** is the graph-owned, content-addressed resource reference.
- A **``MediaFragment``** places that resource in the sole narrative output
  stream, with role and presentation hints but without client-specific URLs.
- **Service** dereferences the RIT into a transport-safe resolved, pending,
  failed, fallback, URL, path, or inline representation according to the
  request and deployment policy.
- **Clients** decide layout and medium-specific treatment. They must retain a
  readable fragment fallback when richer media is unavailable.

## Landed Proofs

The current package supports static inventory, inline data, synchronous and
asynchronous creator lifecycle, renderer-neutral spec adaptation,
content-addressed reuse, and service-layer dereferencing. The bounded
composition proof adds one-level SVG composition from already resolved child
RITs. Presence supplies renderer-neutral portrait requests; Credentials proves
portrait and printable-text children composing into an ID-card RIT and entering
the ordinary JOURNAL/service path.

That proof is deliberately not a universal media DAG, recursive dependency
provisioner, credential forge, or general catalog strategy.

## Ownership Boundaries

- Story and mechanics may request media and emit ``MediaFragment`` values.
- VM provisioning resolves media dependencies during the ordinary lifecycle.
- Media owns inventories, specifications, adaptation, creation, and resource
  identity.
- Journal owns the reusable fragment vocabulary.
- Service owns transport-safe dereferencing and capability-sensitive delivery.
- Clients own visual, audio, animation, and accessibility realization.

No layer reconstructs semantic truth from flattened prose or generated media.
Media may independently visit the same semantic projection used by a text
adapter, but it does not parse narrative output to recover that projection.

## Related Contracts

- ``engine/src/tangl/media/MEDIA_DESIGN.md`` — canonical package architecture
- [Generative Media Design](GENERATIVE_MEDIA_DESIGN.md) — creator and worker
  lifecycle
- [Episode-to-Syuzhet Rendering](story/EPISODE_SYUZHET_RENDERING.md) — shared
  rendering namespace and adapter model
- [Journal Compose Contract](story/JOURNAL_COMPOSE_CONTRACT.md) — ordered
  fragment composition
- [Fragment Stream Contract](service/FRAGMENT_STREAM_CONTRACT.md) — typed
  service boundary
- [Response Type Decision Matrix](service/RESPONSE_TYPES.md) — delivery shapes
