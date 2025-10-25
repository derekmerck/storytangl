Terms:
-----
- *MediaResource*: binary or text data representing an actual media object (e.g., png file, svg string)

- *ResourceInventoryTag*: a proxy object for a media resource that can be dereferenced to find the location of a media file on the backend server and create the final MediaFragment

- *ResourceRegistry*: a handler that maps MediaRef properties and aliases to ResourceInventoryTags

- *MediaItemScript*: a description in the story script for media filling a given media role, specifically a name, a spec, a url, vector text, or encoded binary data.  The role is _not_ part of the media script's fingerprint.

- *MediaRole*: enum'ed hint for how the client should use this media object (narrative image, dialog voice over, etc.)

- *MediaSpecification*: a _recipe_ for a creatable media object given in the script, implementable by the media handler

- *MediaNode*: a node reference to a media script, role, and rit, once it's prepared (similar to how actors can be created when cast)

- *MediaHandler*: specialized ResourceHandler, orchestrator for managing lookups, conversions, translations between story nodes and resource registries tracking their media.

- *JournalMediaItem*: the role and data or URL for a media object for consumption by a frontend client

Example paths:
--------------
`MediaScript w/data -> MediaFragment`

The very simplest example.  The data for the media is directly embedded in the script.  On rendering, this is copied into the journal media item when the rendered data is formatted.  No registry is required.

`MediaScript w/name -> Registry -> RIT -> MediaFragment`

Another simple example.  In the _script_ we create a media node with a name, that name is found in the file registry on 'render', and the url for the journal media item is created when the rendered data is formatted.

```
MediaScript w/MediaSpec (-> Registry?, MediaForge?) -> RIT -> MediaFragment`
```

A complicated example.  A _specification_ is embedded in the script.  On rendering the handler checks whether the resource already exists or not, if it has already been created, that RIT is returned, otherwise it is created, registered, and the new RIT is returned to create the final journal media item.

Each World manages its own media resource registry, and the MediaHandler will query the proper world to convert media nodes into RITS as nodes are rendered.

Finally RITs are translated into JournalMediaItems by the ServiceLayer as a formatting job.
