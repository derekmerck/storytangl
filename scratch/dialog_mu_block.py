from __future__ import annotations
from typing import Protocol
import re
import logging

import pydantic

from tangl.type_hints import StyleDict, StyleClasses
from tangl.graph import Node
from tangl.entity.mixins import Renderable, RenderHandler
from tangl.story.actor import Actor
from tangl.story.scene import MuBlock, MuBlockHandler
from tangl.media.enums import MediaRole
from tangl.media import MediaNode, HasMedia
from tangl.utils.response_models import StyleHints

logger = logging.getLogger("tangl.narrative")

class HasDialogStyles(Protocol):
    # Actor should implement these to be styled in dialog

    name: str
    def goes_by(self, name: str) -> bool: ...
    def get_dialog_style(self, dialog_class: str = None) -> StyleDict: ...
    def get_dialog_image(self, dialog_class: str = None) -> MediaNode: ...


class DialogHandler(MuBlockHandler):

    @classmethod
    def has_mu_blocks(cls, node: Node):
        return len( re.findall( f"^>\s+\[!", node.text, flags=re.MULTILINE ) ) > 0

    @staticmethod
    def parse_text(text: str) -> list[dict]:
        # Split content by paragraphs (double /n)
        paras = re.split("\n{2,}", text.strip())
        output = []
        # Iterate through paragraphs
        for para in paras:
            # If block starts with '>', it's a dialog
            if para.startswith(">"):
                lines = para.split("\n")
                m = re.match(r">\s*\[!([\w\.-]+)\s*]\s*(\w.*)?", lines[0])
                if not m:
                    raise ValueError(f"Unable to parse dialog-block starting with {lines[0]}")
                dialog_class = m.group(1).strip()
                logger.debug( [ str(g) for g in m.groups() ] )
                # group(1) is class, group(2) is label if it exists
                if len(m.groups()) > 1 and m.group(2):
                    label = m.group(2).strip()
                else:
                    label = None
                text = " ".join([re.sub(r"^>\s*", "", line) for line in lines[1:]])  # Extract text
            else:
                # It's a narration block
                label = None
                text = para
                dialog_class = "narration"

            output.append({'label': label,
                           'text': text,
                           'dialog_class': dialog_class})
            # Have to convert dialog class -> class/style hints
        return output

    @classmethod
    def get_mu_blocks(cls, node: Renderable) -> list[DialogMuBlock]:
        text = RenderHandler.render_str(node.text, node.get_namespace())
        try:
            parsed = cls.parse_text(text)
        except ValueError:
            logger.error( f'value error raised parsing dialog in {node.path}' )
            raise
        res = [ DialogMuBlock( **data, graph=node.graph ) for data in parsed ]
        return res

    @classmethod
    def render_mu_blocks(cls, node: HasDialog) -> list[dict]:
        res = super().render_mu_blocks(node)  # type: list[dict]
        # 2nd pass to remove duplicate images
        current_images = {}
        for d in res:
            speaker = d.get('label')
            # todo: I'm pretty sure this isn't right given the current impl for node media
            # if d.get('media'):
            #     image = d.get('media').get(MediaRole.DIALOG)
            #     if current_images.get(speaker) != image:
            #         # it's new, leave it be
            #         current_images[speaker] = image
            #     elif image:
            #         # it's the same, throw it out
            #         del d.media[MediaRole.DIALOG]
        return res


class DialogMuBlock(HasMedia, MuBlock):
    """
    DialogMuBlocks are narrative units smaller than a Block that split
    a Block up into dialog chunks, each carrying additional metadata about
    the speaker, the mood, style, and a relevant avatar/dialog image if
    one exists.

    The default dialog-block parser splits a Block's text field using
    Obsidian's block-quote admonition format for markdown.  The renderer
    then tries to dereference any classes to Actor instances and injects
    `style` and `media.dialog` hints.  In a second pass, any `media.dialog`
    items that have not changed from one mu-block to the next are discarded
    from the result.

    ```markdown
    This is the narrator speaking.

    > [!POV] Main Character
    > This is the mc speaking.

    > [!NPC.happy ] A NPC
    > This is a npc speaking.  I'm happy!
    ```

    Splits into micro-blocks (as yaml):

    ```yaml
    - text: This is the narrator speaking
    - label: Main Character
      text: This is the MC speaking.
      style_class: .pov
      style:
        font-color: blue
      media:
        dialog: mc-avatar
    - label: NPC
      style_class: .npc.happy
      text: This is the MC speaking.  I'm happy!
      style:
        font-color: green
        font-style: bold
      media:
        dialog: npc-avatar-happy
    ```
    """

    dialog_class: str = None

    # attribute meanings:
    #   label: str                  # Speaker (actor) name
    #   style_cls: list[str]        # Style class hint (narrator, pov, npc.happy, etc.)
    #   style_dict: dict[str, str]  # Style dict hint

    @pydantic.model_validator(mode='after')
    def _infer_speaker_and_styles(self):

        if self.dialog_class.lower().startswith('pov'):
            # it's from mc
            logger.debug('pov dialog block')
            self.style_cls = self.dialog_class
            self.style_dict = {'color': 'rgb(var(--v-theme-primary))'}
            # todo: better this is a global setting or something so it's not tied to client

        elif speaker := self.find_speaker():
            # it's an npc
            logger.debug('speaker dialog block')
            self.style_cls = self.dialog_class
            self.style_dict = speaker.get_dialog_style(dialog_class=self.dialog_class)
            im_ref = speaker.get_dialog_image(dialog_class=self.dialog_class)
            if im_ref:
                self.add_child( im_ref )

        else:
            # it's plain narrative
            logger.debug('narrator dialog block')
            self.style_cls = "narrator"

        return self

    def find_speaker(self) -> HasDialogStyles:
        if self.label:
            try:
                res = self.graph.find_nodes(node_cls = Actor,
                                            filt = lambda a: a.goes_by( self.label ))
                if res:
                    return res[0]
            except AttributeError as e:
                logger.error( e )
                pass

    @RenderHandler.strategy
    def _include_dialog_label(self):
        if self.label_:
            return {'label': self.label}


class HasDialog:
    """
    This is a block mixin class that adds the call to the dialog handler during render
    """

    @RenderHandler.strategy
    def _render_dialog(self: Node, **kwargs) -> dict:
        if DialogHandler.has_mu_blocks(self):
            return {'dialog': DialogHandler.render_mu_blocks(self)}

# language=Python
original_parser_reference = """
# Split content by blocks
blocks = re.split("\n{2,}", content.strip())

output = []

# Iterate through blocks
for block in blocks:
    # If block starts with '>', it's a dialog
    if block.startswith(">"):
        lines = block.split("\n")
        speaker = re.search(r"\] (.*)", lines[0]).group(1)  # Extract speaker name
        text = " ".join([re.sub(r"^> ", "", line) for line in lines[1:]])  # Extract text
    else:
        # It's a narration block
        speaker = "narrator"
        text = block

    # Append to output
    output.append({"speaker": speaker, "text": text})

# Print output
for item in output:
    print(item)
"""