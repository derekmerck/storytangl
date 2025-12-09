from pprint import pprint

from scratch.md2yaml import tree2doc, doc2tree

import pytest

# language=Markdown
source = """---
frontmatter: I'm the frontmatter
long_frontmatter: >
  something something something this is content that goes on for
  multiple lines. something something something this is content that goes on for
  multiple lines.  something something something this is content that goes on for
  multiple lines.
...

# Heading 1

```yaml
h1_key: h1_value
```

#tag #tag/subtag

## Subheading 1A

#sh1a_tag

```yaml
sh1a_key: ah1a_value
```

![[sh1a image.jpg|sh1a image key]]

something something something this is content that goes on for
multiple lines. something something something this is content that goes on for
multiple lines.  something something something this is content that goes on for
multiple lines.

Paragraph 2.

> [!info]
> An admonition

> [!warn] Danger!
> A warning

- :icon: [[#heading 2|ref label1]]
- [[another doc|ref label2]]

# Heading 2

## Subheading 2A

Content for subheading 2a

"""

expected = {
 'meta': {'frontmatter': 'I’m the frontmatter',
          'long_frontmatter': 'something something something this is content '
                              'that goes on for multiple lines. something '
                              'something something this is content that goes '
                              'on for multiple lines. something something '
                              'something this is content that goes on for '
                              'multiple lines.'},
 'children': [{'meta': {'label': 'Heading 1',
                        'h1_key': 'h1_value',
                        'tags': ['tag', 'tag/subtag']},
               'children': [{'content': 'something something something this is '
                                        'content that goes on for multiple '
                                        'lines. something something something '
                                        'this is content that goes on for '
                                        'multiple lines. something something '
                                        'something this is content that goes '
                                        'on for multiple lines.\n'
                                        '\n'
                                        'Paragraph 2.\n'
                                        '\n'
                                        '::: info\n'
                                        '> An admonition\n'
                                        ':::\n'
                                        '\n'
                                        '::: {.warn label="Danger!"}\n'
                                        '> A warning\n'
                                        ':::',
                             'meta': {'label': 'Subheading 1A',
                                      'tags': ['sh1a_tag'],
                                      'sh1a_key': 'ah1a_value',
                                      'images': {'sh1a image key': 'sh1a '
                                                                   'image.jpg'}},
                             'children': [{'meta': {'untree_as': 'list',
                                                    'icon': 'icon',
                                                    'links': {'ref label1': '#heading '
                                                                            '2'}}},
                                          {'meta': {'untree_as': 'list',
                                                    'links': {'ref label2': 'another '
                                                                            'doc'}}}]}]},
              {'meta': {'label': 'Heading 2'},
               'children': [{'content': 'Content for subheading 2a',
                             'meta': {'label': 'Subheading 2A'}}]}]}

@pytest.mark.xfail(raises=TypeError, reason="probably wrong version of pandoc")
@pytest.mark.skip(reason="old md2yaml format")
def test_md2yaml():
    # treeify
    data = doc2tree( source )
    # print( data )
    pprint( data, width=80, sort_dicts=False )

    assert data == expected

    round_trip = tree2doc( data )

    print( round_trip )


if __name__ == "__main__":
    test_md2yaml()
