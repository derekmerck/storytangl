# World bundles

Story worlds are packaged as **bundles** containing a manifest, one or more story
scripts, and accompanying media assets. Bundles live in directories named after
their manifest `uid` and can be discovered by the engine via
`Settings.WORLD_DIRS`.

## Directory layout

```
worlds/
  <uid>/
    world.yaml      # Bundle manifest (required)
    story.yaml      # Script entrypoint(s)
    media/          # Static assets referenced by scripts
```

For tests and demos, bundles also live under
`engine/tests/resources/worlds/<uid>/` with the same layout.

## `world.yaml` manifest

`world.yaml` describes the bundle and where to find its resources.

```yaml
uid: media_mvp                  # MUST match directory name
label: "Media MVP Demo"          # Optional; falls back to metadata.title
version: "1.0"

scripts: story.yaml             # Or list: [intro.yaml, scenes.yaml]
media_dir: media                # Relative to bundle root

metadata:                       # Optional ScriptMetadata block
  title: "Media MVP Demo"
  author: "Derek"
  summary: "Simple world for testing static media."

# Optional launcher hints
tags: [demo, media, test]

# Future-proofing (not parsed in MVP)
python_packages: []
plugins: {}
```

### World manifest vs. script metadata

- `WorldManifest` captures bundle layout and optional story metadata.
- Individual story scripts may also include metadata blocks.
- World creation reconciles both sources, with **script metadata taking
  precedence** over manifest metadata.

### Effective labels

Launchers display `manifest.effective_label`, which resolves in priority order:

1. `manifest.label`
2. `manifest.metadata.title`
3. `manifest.uid`

## Story script media references

Story YAML files refer to media using the `name` field on `media` entries.
The compiler produces `MediaItemScript` objects with `name` and `media_role`
fields; static media resolves the `name` against the bundle's media directory.

```yaml
scenes:
  - label: intro
    blocks:
      - label: tavern_entrance
        text: "You enter the dimly lit tavern."
        media:
          - name: tavern.png
            media_role: narrative_im
```

## Authoring patterns

1. **Minimal manifest, rich scripts**: supply only `uid`, `scripts`, and
   `media_dir` in `world.yaml`, with full metadata in `story.yaml`.
2. **Explicit manifest, simple scripts**: embed metadata in `world.yaml` and
   keep scripts focused on scenes and blocks.
