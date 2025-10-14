# Changelog

## v3.7.1 (Unreleased)

### Breaking Changes
- Removed the legacy `tangl.story.story_controller` module in favor of the
  orchestrated `RuntimeController` surface.

### Deprecations
- Accessing `tangl.story.story_controller` now routes to `RuntimeController`
  and emits a `DeprecationWarning`. Update imports to
  `tangl.service.controllers` for forward compatibility.

### Documentation
- Expanded the contributor guide to describe the orchestrator workflow and
  updated legacy inventory notes to reference the runtime controller.

### Maintenance
- Bumped the project version to `3.7.1` to capture the service layer cleanup.
