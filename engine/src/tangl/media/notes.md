Media Lifecycle
===============

1. **media script item**: concrete ref (path, id), criteria (tags), actual data, or template/spec to realize, creates -> media node at graph creation
3. **media node**: edge-like object in a story graph that links a concept or structure node to a unique media record via ref, criteria, or template/spec, media nodes with template/specs can 'realize' them based on their current context when rendered
2. **media resource**: data blob on disk/in mem, pre-existing or dynamically created by media forges
4. **media record**: pointer to a media resource findable by aliases, mediates node/fragment -> resource
5. **media registry**: searchable domain registry of media records
6. **media journal fragment**: holds a copy of the record provided by the generating node
7. **media forge**: Singletons that can handle various types of specs (e.g., paperdolls, gen ai), takes spec, returns media and possibly revised spec (e.g., with random parameters noted, etc.)

- As media journal fragments are _created_, media records are validated or media specs are realized and transformed into records, if necessary
- As media journal fragments are _queried_, the response handler converts media records into client-relative urls or data in the final response item

Media Registry: Holds media records
Media Creator: Various "forges" that can create different sorts of media from specifications
