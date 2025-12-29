import yaml

from tangl.lang.antlrnlpy import tokenize, parse
from tangl.lang.rephrase.rephrase import rephrase
from tangl.lang.rephrase.voice import Voice

from tangl.config import settings
settings.dev.lexref_apis_enabled = True

with open("sample_context.yaml") as f:
    context_spec_ = yaml.safe_load(f)
context = { k: Voice(**v) for k, v in context_spec_.items() }

sample_phrases_ = """
- She opens her mouth so he can put his sandwich into her.
- He begins to carefully put his sandwich into her.
- She greedily enjoys his sandwich.
- Saliva and crumbs run down her chin as she eats.
- He stops feeding her and she moans with disappointment:xx.
- She pretends to not want his sandwich.
- He forces her mouth open and feeds his sandwich to her.
- With a lusty moan:xx, she finishes eating his sandwich.
- He tenderly cleans her mouth for her.
"""

sample_phrases = yaml.safe_load( sample_phrases_ )

sample_tokens = ['She_PRP opens_VBZ her_PRP$ mouth_NN so_RB he_PRP can_MD put_VB his_PRP$ sandwich_NN into_IN her_PRP .', 'He_PRP begins_VBZ to_TO carefully_RB put_VB his_PRP$ sandwich_NN into_IN her_PRP .', 'She_PRP greedily_RB enjoys_VBZ his_PRP$ sandwich_NN .', 'Saliva_NN and_CC crumbs_NNS run_VBP down_RP her_PRP$ chin_NN as_IN she_PRP eats_VBZ .', 'He_PRP stops_VBZ feeding_VBG her_PRP and_CC she_PRP moans_VBZ with_IN disappointment_NN:xx .', 'She_PRP pretends_VBZ to_TO not_RB want_VB his_PRP$ sandwich_NN .', 'He_PRP forces_VBZ her_PRP$ mouth_NN open_JJ and_CC feeds_VBZ his_PRP$ sandwich_NN to_IN her_PRP .', 'With_IN a_DT lusty_JJ moan_NN:xx , she_PRP finishes_VBZ eating_VBG his_PRP$ sandwich_NN .', 'He_PRP tenderly_RB cleans_VBZ her_PRP$ mouth_NN for_IN her_PRP .']

sample_renders = ['She opens her mouth so he can put his sandwich into her.']

sample_exprs = ["{{ her.as_subject() }} {{ her.conjugate('opens') }} {{ her.as_possessive() }} {{ her.assets.mouth.as_object() }} {{ her.get_adverb() }} {{ him.as_subject() }} can put {{ him.as_possessive() }} {{ him.assets.sandwich.as_object() }} into {{ her.as_object() }} ."]

def _test_tokenize(sample=0):
    s = sample_phrases[sample]
    t = tokenize( s )[0]
    print( t )
    assert t == sample_tokens[sample]

def _test_parse(sample=0):
    t = sample_tokens[sample]
    d = parse( t )
    r = d.render()
    print( r )
    assert( r == sample_renders[sample] )

def _test_mermaid(sample=0):
    t = sample_tokens[sample]
    d = parse( t )
    r = d.render()
    print( r )
    mm = d.as_mermaid()
    print( mm )

def _test_rephrase_templ(sample=0):
    t = sample_tokens[sample]
    d = parse( t )
    p = rephrase( d )
    x = p.render_expr()
    print( x )
    assert( x == sample_exprs[sample] )

def _test_rephrase_sub():
    pass

def generate_mermaid_graphs():

    buf = ""
    for t in sample_tokens:
        print( t )
        d = parse( t, verbose=False )
        rephrased = rephrase( d )
        m = rephrased.as_linked_mermaid(render='markdown')
        buf += m + '\n'
        print( rephrased.render_expr() )

    with open("../../../StoryTangl-wiki/mermaid.md", "w") as f:
        f.write(buf)


if __name__ == '__main__':
    # _test_tokenize()
    # _test_parse()
    _test_mermaid()
    # _test_rephrase_templ()
    # _test_rephrase_sub()
    # generate_mermaid_graphs()



voice_cues = """
confident
resolute
stern
forceful
skillful
assertive
diligent
persistent

eager
enthusiastic
affable
generous
affectionate
benevolent
amical
kind

reluctant
hesitating

compliant
obedient

merciless
rough
brutal
violent
"""
