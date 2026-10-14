"""Small Markdown code-region scanner shared by dialog parsing and name linking."""
from __future__ import annotations

from collections.abc import Iterator
import re


_DELIMITERS = re.compile(
    r"(?m)^ {0,3}(?:(?P<backticks>`{3,})(?!`)[^`\n]*(?:\n|$)"
    r"|(?P<tildes>~{3,})[^\n]*(?:\n|$))|(?P<ticks>`+)"
)


def code_regions(text: str) -> Iterator[tuple[int, int]]:
    """Yield literal fenced/inline code spans; an unclosed fence protects the rest."""
    offset = 0
    while match := _DELIMITERS.search(text, offset):
        start = match.start()
        slashes = len(text[:start]) - len(text[:start].rstrip("\\"))
        if slashes % 2:
            offset = match.end()
            continue
        if fence := match.group("backticks") or match.group("tildes"):
            closing = re.compile(
                rf"(?m)^ {{0,3}}{re.escape(fence[0])}{{{len(fence)},}}[ \t]*(?:\n|$)"
            ).search(text, match.end())
            end = closing.end() if closing else len(text)
        else:
            ticks = match.group("ticks")
            closing = re.compile(rf"(?<!`){re.escape(ticks)}(?!`)").search(text, match.end())
            if closing is None:
                offset = match.end()
                continue
            end = closing.end()
        yield start, end
        offset = end
