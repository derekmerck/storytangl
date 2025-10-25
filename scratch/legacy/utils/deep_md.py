"""
This functionality has been moved into the service.response_handler module.

It was originally written to use "markdown" as a dependency, but migrated
to common-mark and use 'markdown-it'.
"""

import typing as typ
from markdown_it import MarkdownIt
markdown = MarkdownIt()

def deep_md(data: typ.Union[typ.Dict, typ.List]) -> typ.Union[typ.List, typ.Dict]:
    """
    Convert any string value in nested collections from markdown to html

    `label` keys are treated as inline, `text` and other keys are wrapped in <p>
    """

    if isinstance(data, list):
        # print(f"descending list {k}")
        for i, v in enumerate(data):
            data[i] = deep_md(v)
        return data

    elif isinstance(data, dict):
        for k, v in data.items():
            if k == "text":
                try:
                    html = markdown.render(v)
                    data[k] = html
                except AttributeError:  # pragma: no cover
                    data[k] = v

            elif k == "label":
                try:
                    html = markdown.renderInline(v)
                    data[k] = html
                except (AttributeError, TypeError):
                    data[k] = v

            elif isinstance(v, list) or isinstance(v, dict):
                data[k] = deep_md(v)
        return data

    return data
