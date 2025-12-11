# todo: are actions, media microblocks? assets for sale or interaction or game tokens?
#  maybe this should be 'card'?

from __future__ import annotations
import abc

from tangl.utils.response_models import StyleHints
from tangl.core.entity import Entity
from tangl.core.entity.handlers import Renderable


class MuBlockHandler(abc.ABC):
    """
    Defines the interface for a micro-block handler.
    """

    @classmethod
    @abc.abstractmethod
    def has_mu_blocks(cls, node: Renderable) -> bool:
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def get_mu_blocks(cls, node: Renderable) -> list[MuBlock]:
        raise NotImplementedError

    @classmethod
    def render_mu_blocks(cls, node: Renderable) -> list[dict]:
        if cls.has_ublocks(node):
            mu_blocks = cls.get_mu_blocks(node)
            res = [ mb.render() for mb in mu_blocks ]
            return res


class MuBlock(StyleHints, Renderable, Entity):
    """
    A MuBlock (ublock, micro-block) is a unit of content smaller than
    a block. They can be used to split up Blocks into annotated segments
    with style metadata.

    This can be useful for dialog (DialogMuBlock), game results, asset
    'cards', or any other passages that should contain multiple distinct
    styles. MuBlocks enable rendering such passages without splitting a
    single block into multiple chained blocks.

    MuBlocks carry _style hints_ that can be used to guide the client.

    **Note that respecting MuBlock content and style is _optional_ for
    a client.**

    If the API chooses to provide a MuBlock representation, it should
    be in _addition_ to the standard block text and media content.

    For example, the DialogHandler simply adds a "dialog" field with a list
    of DialogMuBlocks to the Block's journal item output, without altering
    the existing journal block text or any other fields.

    Clients that support dialog-format output should then just prefer that
    field, and only use the text field as a fallback.
    """
    ...
