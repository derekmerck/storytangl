import attr

from tangl.story import StoryNode, Narrated

def test_narrated():

    @attr.define(init=False)
    class NarratedNode(Narrated, StoryNode):
        pass

    r = NarratedNode( text="Hello {{player}}", locals={"player": "TanglDev"} )
    # print( r.vars )
    s = r.text()
    print( s )
    assert( s == "Hello TanglDev" )

    s = r.text( player="Foo" )
    print( s )
    assert( s == "Hello Foo" )


def test_narrator():

    from tangl.story.narrated import Narrated
    from tangl.world.narrator import Narrator

    @attr.define(init=False)
    class SelfNarratedNode( Narrated, StoryNode ):

        narrator: Narrator = attr.ib(factory=Narrator)

        def _render_str(self, s, **kwargs):
            ns = self.ns()
            return self.narrator._render_str(s, ns, **kwargs)

    n = SelfNarratedNode( label="test {{a}}", text="this is a desc {{a}}", locals={"a": "AAA"} )
    print( n.label() )
    assert n.label() == "test AAA"
    print( n.text() )
    assert n.text() == "this is a desc AAA"

    print( n.text( a="BBB") )
    assert n.text( a="BBB" ) == "this is a desc BBB"

    n1 = SelfNarratedNode( label="test {{c}}", locals={"c": "{{ d }}", "d": "DDD"} )
    print( "n1.label() =", n1.label() )
    assert n1.label() == "test DDD"
