# md2yaml

Filter a markdown formatted document into a data tree representation and _vice versa_.

- Headings generate a hierarchy of nodes
- Lists create a child per item at the current node
- Code blocks and inline code are parsed into metadata for the current node, document metadata block becomes metadata for the root element
- wikistyle links and embeds are converted to md links and embeds (b/c Pandoc doesn't like wikilinks)

Uses [pandoc](), [pypandoc](), and [panflute]().

Sample input:
````markdown
---
# front matter
key1: value1
...

Unsectioned content with a [[#link|Link label]]

# abcd
```yaml
key2: value
```
H1 content

## efgh

H2 content with inline meta: `key3: value3`

- List item1
- List item2
````

Expected output:
```yaml
meta:
  key1: value1
content: "Unsectioned content with a [Link Label](#link)"  # md payload
children:
  - meta:
      label: abc
      key2: value2
    content: "H1 content"
    children:
      - meta:
          label: efg
          key3: value3
        content: "H2 content"
        children:
          - content: List item 1
          - content: List item 2
```
