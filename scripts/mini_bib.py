"""
Print a Markdown reference list drawn from the project bibliography.

For READMEs and other files the Sphinx docs do not index: run this, then paste
the output at the bottom of the file by hand.

Usage:
$ python scripts/mini_bib.py chatman_story_1978 genette_narrative_1980
$ python scripts/mini_bib.py -k credentials -k gamebook
$ python scripts/mini_bib.py --keys
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from pybtex.backends.markdown import Backend
from pybtex.database import BibliographyData, parse_file

DOCS_SRC = Path(__file__).parent.parent / "docs/src"
sys.path.insert(0, str(DOCS_SRC / "_ext"))

from bib_style import UnsrtStyle as Style  # noqa: E402

BIB_PATH = DOCS_SRC / "bibliography/storytangl.bib"


def keywords(entry) -> set[str]:
    """Entry keywords, with each ``devref:<topic>`` also matching a bare ``<topic>``."""
    tags = {k.strip() for k in entry.fields.get("keywords", "").split(",")}
    return tags | {t.removeprefix("devref:") for t in tags}


def mini_bib(keys: list[str], wanted_keywords: list[str]) -> str:
    library = parse_file(str(BIB_PATH))
    unknown = [key for key in keys if key not in library.entries]
    if unknown:
        raise SystemExit(f"Not in {BIB_PATH.name}: {', '.join(unknown)}")
    selected = set(keys) | {
        key
        for key, entry in library.entries.items()
        if keywords(entry) & set(wanted_keywords)
    }
    chosen = BibliographyData({key: library.entries[key] for key in selected})
    formatted = Style(sorting_style="author_year_title").format_bibliography(chosen)
    backend = Backend()
    lines = (entry.text.render(backend).replace("\n", " ") for entry in formatted)
    # pybtex escapes all punctuation; keep only the escapes Markdown needs.
    return "\n".join("- " + re.sub(r"\\([^*_\[\]`])", r"\1", line) for line in lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("keys", nargs="*", help="cite keys to include")
    parser.add_argument("-k", "--keyword", action="append", default=[],
                        help="include every entry carrying this keyword or devref topic")
    parser.add_argument("--keys", dest="list_keys", action="store_true",
                        help="list every cite key with its title, then exit")
    args = parser.parse_args()
    if args.list_keys:
        for key, entry in sorted(parse_file(str(BIB_PATH)).entries.items()):
            print(f"{key}\t{entry.fields['title'].strip('{}')}")
        return
    print(mini_bib(args.keys, args.keyword))


if __name__ == "__main__":
    main()
