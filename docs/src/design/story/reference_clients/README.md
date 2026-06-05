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

The matching CLI/Rich guide has not been checked in yet in this worktree. If it
resurfaces, place it beside the Vue guide under this directory so reference
client implementation notes stay together.
