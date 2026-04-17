from __future__ import annotations

"""Sphinx directive for invisible StoryTangl developer-topic annotations."""

from docutils import nodes
from docutils.parsers.rst import Directive, directives


class StoryTanglTopicDirective(Directive):
    """Register a doc-local developer-topic annotation without rendering output."""

    has_content = False
    option_spec = {
        "topics": directives.unchanged_required,
        "facets": directives.unchanged,
        "relation": directives.unchanged_required,
        "related": directives.unchanged,
    }

    def run(self) -> list[nodes.Node]:
        node = nodes.comment()
        node["storytangl_topic"] = {
            key: value for key, value in self.options.items()
        }
        return [node]


def setup(app) -> dict[str, bool]:
    """Register the ``storytangl-topic`` directive for RST and MyST docs."""

    app.add_directive("storytangl-topic", StoryTanglTopicDirective)
    return {
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
