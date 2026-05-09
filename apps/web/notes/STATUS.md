# StoryTangl Web Client Status

**Date:** April 2026
**Current State:** v38-era stabilization

---

## Current Reality

The web client is a useful development interface, but the old v3.7-era
"production ready" and "MVP complete" language was stale. The engine and
service contracts have continued to evolve, and the client is now oriented
toward canonical v38 `RuntimeEnvelope` and `ProjectedState` response shapes.

This stabilization pass repairs the current Vitest/MSW harness while preserving
the existing `happy-dom` setup. Issue #224 now tracks the direct-fragment
renderer and contract coverage work around canonical `RuntimeEnvelope` fixtures.

## Working Areas

- Vue 3.5, TypeScript, Vite, Vuetify, Pinia, and Vue Test Utils remain the
  active stack.
- Core story-flow components, status/sidebar display, dialogs, and global
  client utilities are present and maintained.
- MSW remains the local mock mechanism for client-side tests and development.
- The current test harness now installs a memory `localStorage` surface before
  MSW is loaded, which keeps `happy-dom` viable for this pass.
- Story flow now renders `RuntimeEnvelope.fragments` directly through a fragment
  registry, scene shells, and small fragment widgets. The old
  `JournalStoryUpdate[]` path remains only as a narrow compatibility adapter.
- `zone` and `token` fragments now have real generic widgets, which gives
  token-selection choices a visible surface to bind to.
- The next interaction direction is payload-first: support text, quantity, and
  token inputs as explicit `choice.accepts` payloads before adding command-bar
  affordances.
- `ChoiceInputView` handles current text, quantity, and token payload widgets,
  with canonical quantity and sandbox fixtures in
  `apps/web/tests/fixtures/payloadInteractions.ts`.
- Raw command choices now submit `{text}` through reserved backend
  interpretation edges, with optional `metadata.grammar` hints used only as UI
  affordances.

## Open Work

- Add `interpretation` rendering once the backend response shape exists; until
  then, fallback text is acceptable.
- Add richer command preview/autocomplete once backend grammar hints settle
  beyond examples, verbs, and nouns.
- Recheck world/system/user metadata assumptions against backend response
  models.
- Audit loading states, error display, mobile layout, and accessibility.
- Add browser E2E only after payload widgets and command feedback settle enough
  that tests will not cement a transitional shape.

## Guidance

Treat the client as a live development surface rather than a finished release.
Version metadata in package files and footer defaults is intentionally unchanged
by this pass; the status docs now explain the drift instead of inventing a
release bump.

**Documentation references:**
- `apps/web/notes/ARCHITECTURE.md` - System design
- `apps/web/AGENTS.md` - Coding conventions
- `apps/web/notes/TESTING_PATTERNS.md` - Test recipes
- `apps/web/notes/SETUP_GUIDE.md` - Installation details
