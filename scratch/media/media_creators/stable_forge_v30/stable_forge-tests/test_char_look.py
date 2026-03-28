from tangl.story.actor.look import Look
from tangl.media.illustrated.stableforge.adapters import CharacterLook

def test_char_look():
    look = Look(outfit_type="formal_gown",
                outfit_palette="pink",
                hair_color="pink")
    ch_look = CharacterLook.from_look(look)
    print( ch_look )

