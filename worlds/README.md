# Worlds bundle layout

World bundles package story scripts and related assets for discovery by the engine. Each bundle lives in a directory whose name **must** match the ``uid`` declared in its manifest. For the MVP loader, the engine expects the following structure:

```
<world_uid>/
  world.yaml    # Manifest describing the bundle
  story.yaml    # At least one story script (additional scripts allowed)
  media/        # Default directory for media assets referenced by scripts
```

## Manifest (`world.yaml`)
- ``uid``: Unique identifier for the bundle; must be filesystem-safe and equal to the bundle directory name.
- ``label``: Display name for the bundle.
- ``scripts``: Path or list of paths to story scripts relative to the bundle root. The loader normalizes a single string into a list.
- ``media_dir``: Directory containing media assets (defaults to ``media``).
- Additional optional metadata: ``version``, ``author``, ``description``, ``tags``, and placeholders for ``python_packages``/``plugins``.

## Media references in scripts
Story blocks can attach media by providing file paths relative to the bundle root:

```yaml
blocks:
  - id: tavern_entrance
    content: "You enter the dimly lit tavern."
    media:
      - media_path: tavern.svg
        media_role: narrative_im
        media_type: IMAGE  # optional; inferred from extension when omitted
```

## Reference bundle
A minimal test bundle lives at ``engine/tests/resources/worlds/media_mvp``. It includes a manifest, a simple story script, and an SVG placeholder asset under ``media/``.
