Media Lifecycle
===============

1. **media script item**: concrete path or data, or spec to realize
2. **media resource**: blob on disk/in mem
3. **media node**: graph object that holds a spec or record
4. **media record**: pointer to a media resource findable by aliases, mediates node/fragment -> resource
5. **media journal fragment**: holds a copy of the record provided by the generating node

- As media journal fragments are _created_, media records are validated or media specs are realized and transformed into records, if necessary
- As media journal fragments are _queried_, the response handler converts media records into client-relative urls or data in the final response item

Media Registry: Holds media records
Media Creator: Various "forges" that can create different sorts of media from specifications
