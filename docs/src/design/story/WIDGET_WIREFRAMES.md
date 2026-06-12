# StoryTangl Widget Wireframes

The canonical wireframe bundle for the current widget vocabulary is archived
under `docs/src/design/story/wireframes/v1_5/`.

Brand-direction references from the same design pass are archived separately in
the [brand reference note](brand/README.md). They are visual and tone references
only; they are not deployed app/docs assets.

- [`StoryTangl-Wireframes-v1.5.html`](wireframes/v1_5/StoryTangl-Wireframes-v1.5.html)
  is the rendered reference artifact.
- The adjacent `v15-*.jsx`, `v15-*.js`, and `v15-*.css` files are retained as
  the design agent's source package. Treat them as visual references, not
  implementation code.
- Source package:
  [`styles.css`](wireframes/v1_5/styles.css),
  [`v2-styles.css`](wireframes/v1_5/v2-styles.css),
  [`v15-styles.css`](wireframes/v1_5/v15-styles.css),
  [`v15-fixtures-core.js`](wireframes/v1_5/v15-fixtures-core.js),
  [`v15-fixtures-genres.js`](wireframes/v1_5/v15-fixtures-genres.js),
  [`v15-widgets.jsx`](wireframes/v1_5/v15-widgets.jsx),
  [`v15-shells.jsx`](wireframes/v1_5/v15-shells.jsx),
  [`v15-sections-core.jsx`](wireframes/v1_5/v15-sections-core.jsx),
  [`v15-sections-genres.jsx`](wireframes/v1_5/v15-sections-genres.jsx),
  [`v15-app.jsx`](wireframes/v1_5/v15-app.jsx).
- The v1.5 package intentionally splits core fixtures from genre fixtures:
  `v15-fixtures-core.js` covers Tier S/P1/P2 pressure cases, while
  `v15-fixtures-genres.js` covers Tier P3 extension treatments for
  credentials, training, and elefant_hunt.
- The wireframe fixtures use readable symbolic ids such as `g-scene` and
  `pc-permit`. Engine conformance fixtures still require UUID-shaped
  `cursor_id` and fragment `uid` values, so promote wireframe examples into
  `engine/contrib/conformance/` only after translating ids and preserving
  reference links.
- One command-feedback example has been translated to the current envelope
  event contract as a non-gating proposal fixture:
  `engine/contrib/conformance/proposals/wireframe_v15_ux_event_samples.json`.

The previous v1.3 bundle remains archived under
`docs/src/design/story/wireframes/v1_3/`.

- [`StoryTangl-Wireframes-v1.3.html`](wireframes/v1_3/StoryTangl-Wireframes-v1.3.html)
  is retained as historical visual precedent.
- The adjacent `v12-*.jsx` and `v12-*.css` files are retained as the design
  agent's source package. Treat them as visual references, not implementation
  code.

The source of truth for contracts remains
[`STORYTANGL_WIDGET_VOCAB.md`](STORYTANGL_WIDGET_VOCAB.md), with implementation
status tracked in
[`WIDGET_CONTRACT_RECONCILIATION.md`](WIDGET_CONTRACT_RECONCILIATION.md).
