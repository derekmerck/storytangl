# Media fragment JSON contract

Story updates emit media fragments after media dependencies are bound to `MediaRIT` objects. Clients only need the flattened JSON payload; no registry identifiers leak over the wire.

## World-scoped media

```json
{
  "fragment_type": "media",
  "media_role": "narrative_im",
  "url": "/media/world/media_e2e/tavern.png",
  "media_type": "IMAGE",
  "text": "optional caption",
  "source_id": "block-uuid",
  "scope": "world"
}
```

## System-scoped media

Shared assets (UI chrome, logos, etc.) use the `sys` scope and resolve under `/media/sys`:

```json
{
  "fragment_type": "media",
  "media_role": "ui_logo",
  "url": "/media/sys/logo.png",
  "media_type": "IMAGE",
  "scope": "sys"
}
```

## Client rendering notes
- The `url` is already dereferenced and ready for `<img src="...">` or similar tag-specific renderers.
- `media_role` hints where to place the asset (background, inline image, avatar, etc.).
- `text` carries a caption when provided by the script.
- Unknown fragment types should fall back to the default fragment rendering path.
