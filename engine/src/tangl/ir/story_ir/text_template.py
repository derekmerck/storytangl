"""Typed authored policy for the template language of Story text."""

from __future__ import annotations

from enum import Enum

from tangl.utils.enum_plus import EnumPlusMixin


class TextTemplate(EnumPlusMixin, Enum):
    """The template language a script's text is written in.

    ``FSTRING`` formats ``{name}`` placeholders. ``JINJA`` renders recursively
    through rejinja: template text a value produces is rendered again until it
    bottoms out.
    """

    FSTRING = "fstring"
    JINJA = "jinja"
