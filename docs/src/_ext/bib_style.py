"""Bibliography styles for the project library.

Two departures from the stock pybtex styles:

- ``@standard`` is formatted. It is a BibLaTeX type, which Zotero exports for
  standards and specifications; classic BibTeX styles refuse it.
- Each entry carries one link: its DOI if it has one, otherwise its URL.
- JSTOR eprint ids link to JSTOR, not arXiv.
- Each entry is labelled with its cite key (``aarseth_cybertext_1997``) rather
  than a generated label (``Aar97``), so the label a reader sees is the key an
  author types.
"""
from __future__ import annotations

from pybtex.plugin import register_plugin
from pybtex.style.formatting import unsrt
from pybtex.style.formatting.unsrt import date, toplevel
from pybtex.style.labels import BaseLabelStyle
from pybtex.style.template import field, href, join, optional, optional_field, sentence


class CiteKeyLabelStyle(BaseLabelStyle):

    def format_labels(self, sorted_entries):
        for entry in sorted_entries:
            yield entry.key


class StandardEntryMixin:

    def format_web_refs(self, e):
        # One link per entry: the DOI where there is one, otherwise the URL.
        if "doi" in e.fields:
            return sentence[self.format_doi(e)]
        return sentence[optional[self.format_url(e)], optional[self.format_eprint(e)]]

    def format_eprint(self, e):
        # pybtex links every eprint to arXiv; Zotero also exports JSTOR ids.
        if e.fields.get("eprinttype", "").lower() != "jstor":
            return super().format_eprint(e)
        eprint = field("eprint", raw=True)
        return href(join["https://www.jstor.org/stable/", eprint])[join["JSTOR:", eprint]]

    def get_standard_template(self, e):
        return toplevel[
            optional[sentence[self.format_names("author")]],
            self.format_title(e, "title"),
            sentence[
                optional_field("edition"),
                optional_field("publisher"),
                optional_field("howpublished"),
                optional[date],
            ],
            self.format_web_refs(e),
        ]


class CiteKeyStyle(StandardEntryMixin, unsrt.Style):
    """Style for the Sphinx bibliography page, labelled by cite key."""

    default_label_style = "citekey"
    default_sorting_style = "author_year_title"


class UnsrtStyle(StandardEntryMixin, unsrt.Style):
    """Unlabelled style for pasted Markdown reference lists."""


def setup(app):
    register_plugin("pybtex.style.labels", "citekey", CiteKeyLabelStyle)
    register_plugin("pybtex.style.formatting", "storytangl", CiteKeyStyle)
    return {"parallel_read_safe": True}
