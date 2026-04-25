# StoryTangl Web Client Status

**Date:** April 2026
**Current State:** v38-era stabilization

---

## Current Reality

The web client is a useful development interface, but the old v3.7-era
"production ready" and "MVP complete" language was stale. The engine and
service contracts have continued to evolve, and the client fixtures lag behind
the canonical v38 response shapes.

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

## Open Work

- Continue splitting the first direct-fragment renderer into smaller widgets.
- Recheck story update, projected status, media, world info, and system info
  assumptions against backend response models.
- Expand integration coverage after fixture data is trustworthy.
- Audit loading states, error display, mobile layout, and accessibility.
- Refresh component and fixture documentation as the contract settles.

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
