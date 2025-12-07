import pydantic
import pytest

from tangl.type_hints import StyleClasses, StyleDict
from tangl.graph import Node, Graph
from tangl.entity.mixins import Renderable, HasNamespace
# from tangl.story.story import StoryNode, Story
from tangl.media import MediaNode as MediaReference
from tangl.discourse.creators.dialog import HasDialogStyles, DialogMuBlock, DialogHandler, HasDialog
from tangl.entity import StyledJournalItem
from tangl.utils.response_models import StyleHints


DialogNode = pydantic.create_model(
    'DialogNode',
    __base__=(HasDialog, Renderable, HasNamespace, Node) )

# Mocking the HasDialogStyles protocol and root and actors object
class Actor(Node):

    name: str

    def goes_by(self, name):
        return name == self.name

    def get_dialog_style(self, dialog_class: str) -> StyleDict:
        return {"font-color": f"{self.name}-color"}

    def get_dialog_image(self, dialog_class: str):
        return MediaReference(name=f"{self.name}-avatar", media_role="avatar_im")


class MockStory(Graph):

    def find_nodes(self, node_cls, filt = None):

        mc = Actor(name="Main Character")
        npc = Actor(name="A NPC")
        res = list( filter( filt, [ mc, npc ] ) )
        print( 'mock found:', res )
        return res

    def add_node(self, *args, **kwargs):
        return


@pytest.fixture
def dialog_text() -> str:
    text = (
        "This is the narrator speaking.\n"
        "\n"
        "> [!POV] Main Character\n"
        "> This is the mc speaking.\n"
        "\n"
        "> [!NPC.happy ] A NPC\n"
        "> This is a npc speaking.  I'm happy!"
    )
    return text

def test_dialog_node(dialog_text):
    node = DialogNode(
        text=dialog_text,
        graph=MockStory())
    print( node )
    print( isinstance(node, HasNamespace) )
    print( node.get_namespace() )

@pytest.fixture
def dialog_node(dialog_text):
    return DialogNode(
        text=dialog_text,
        graph=MockStory())

def test_get_mu_blocks(dialog_node):
    dialog_blocks = DialogHandler.get_mu_blocks(dialog_node)
    print( dialog_blocks )

    assert len(dialog_blocks) == 3

    assert dialog_blocks[0].label_ is None
    assert dialog_blocks[0].style_cls == "narrator"
    assert dialog_blocks[0].style_dict is None
    assert dialog_blocks[0].text == "This is the narrator speaking."

    assert dialog_blocks[1].label == "Main Character"
    assert dialog_blocks[1].style_cls == "POV", 'cls should be pov'
    assert dialog_blocks[1].style_dict == {'color': 'rgb(var(--v-theme-primary))'}
    assert dialog_blocks[1].text == "This is the mc speaking."

    assert dialog_blocks[2].label == "A NPC"
    assert dialog_blocks[2].style_dict == {'font-color': 'A NPC-color'}
    assert dialog_blocks[2].style_cls == "NPC.happy", 'cls should be npc.happy'
    assert dialog_blocks[2].text == "This is a npc speaking.  I'm happy!"

@pytest.fixture
def dialog_blocks(dialog_node) -> list[DialogMuBlock]:
    return DialogHandler.get_mu_blocks(dialog_node)

def test_find_speaker(dialog_blocks):

    print( dialog_blocks )
    assert not dialog_blocks[0].find_speaker()
    assert isinstance(dialog_blocks[1].find_speaker(), Actor)
    assert isinstance(dialog_blocks[2].find_speaker(), Actor)

def test_parse_text(dialog_text):

    output = DialogHandler.parse_text(dialog_text)
    print( output )
    assert len(output) == 3
    assert output[0]["label"] is None
    assert output[0]["dialog_class"] == "narration"
    assert output[0]["text"] == "This is the narrator speaking."
    assert output[1]["label"] == "Main Character"
    assert output[1]["dialog_class"] == "POV"
    assert output[1]["text"] == "This is the mc speaking."
    assert output[2]["label"] == "A NPC"
    assert output[2]["dialog_class"] == "NPC.happy"
    assert output[2]["text"] == "This is a npc speaking.  I'm happy!"

def test_from_node(dialog_blocks):
    assert len(dialog_blocks) == 3
    assert dialog_blocks[1].label == "Main Character"
    assert dialog_blocks[1].dialog_class == "POV"
    assert dialog_blocks[1].text == "This is the mc speaking."

def test_render(dialog_blocks):

    rendered = [ bl.render() for bl in dialog_blocks ]
    from pprint import pprint
    pprint( rendered )
    output = [ StyledJournalItem(**r) for r in rendered ]
    print( output )

    assert len(output) == 3
    assert output[0].label is None
    assert output[0].style_cls is "narrator"
    assert output[0].text == "This is the narrator speaking."
    assert output[1].label == "Main Character"
    assert output[1].style_cls == "POV"
    assert output[1].text == "This is the mc speaking."
    assert output[2].label == "A NPC"
    assert output[2].style_cls == "NPC.happy"
    assert output[2].text == "This is a npc speaking.  I'm happy!"

def test_render_node(dialog_text):

    node = DialogNode(
        text=dialog_text,
        graph=MockStory())

    output = node.render()
    print( output )
