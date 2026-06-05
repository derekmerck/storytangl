# Reference Client Guides

This directory collects design-agent reference guides for client implementations.
They are implementation aids, not the canonical widget contract. The contract
remains `../STORYTANGL_WIDGET_VOCAB.md` plus the conformance fixtures under
`engine/contrib/conformance/`.

## Vue 3 + Vuetify 3

- [Vue 3 + Vuetify 3 component guide](vue_guide/vue-vuetify-component-guide.html)
- [Guide stylesheet](vue_guide/vue-guide.css)

The Vue guide targets the current reference web client stack and maps the v1.5
fragment vocabulary to component responsibilities, props, emits, payloads, and
theme constraints. Treat the component and store boundaries as more important
than the Vuetify-specific primitives: the guide is useful even if the web client
eventually moves toward a more headless component base.

## CLI / Rich

- [Rich CLI rendering guide](cli_guide/rich-cli-rendering-guide.html)
- [Guide stylesheet](cli_guide/rich-cli-guide.css)
- [World profiles design study](cli_guide/world_profiles/world-profiles.html)
- World profile study assets:
  [app](cli_guide/world_profiles/wp-app.jsx),
  [fixtures](cli_guide/world_profiles/wp-fixtures.js),
  [profiles](cli_guide/world_profiles/wp-profiles.js),
  [sections](cli_guide/world_profiles/wp-sections.jsx),
  [sections 2](cli_guide/world_profiles/wp-sections2.jsx),
  [theme](cli_guide/world_profiles/wp-theme.css)

The Rich guide maps the same v1.5 surfaces to terminal renderables and plain
fallbacks. The world-profiles study explores the related render negotiation
idea: client capability profiles, world preference profiles, and a degraded or
enriched render plan that never changes the underlying fragment vocabulary.
