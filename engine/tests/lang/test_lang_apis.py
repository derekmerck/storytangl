from tangl.narrative.lang.apis import MeriamWebsterApi
from tangl.narrative.lang.apis import VerbixApi
from tangl.narrative.lang.apis import LanguageToolApi
from tangl.narrative.lang.apis import ReversoApi
from tangl.config import settings

import pytest

from tangl.narrative.lang.conjugates import Conjugates
from tangl.exceptions import RemoteApiUnavailable



@pytest.mark.skipif(condition=not settings.lang.apis.reverso.enabled, reason="remote api disabled")
@pytest.mark.xfail(raises=RemoteApiUnavailable, reasons="remote api unavailable")
def test_reverso():

    api = ReversoApi
    data = api.get_conjugates('dogmatize')
    print( data )
    assert data == Conjugates( **{'infinitive': 'to dogmatize', 'gerund': 'dogmatizing', 'participle': 'dogmatized', '_1s': 'dogmatize', '_2s': 'dogmatize', '_3s': 'dogmatizes', '_1p': 'dogmatize', '_3p': 'dogmatize', 'source': 'reverso'} )

    data = api.get_conjugates('to be')
    print( data )
    assert data == Conjugates( **{'infinitive': 'to be', 'gerund': 'being', 'participle': 'been', '_1s': 'am', '_2s': 'are', '_3s': 'is', '_1p': 'are', '_3p': 'are', 'source': 'reverso'})

def test_verbix_parser(verbix_sample_raw_html1, verbix_sample_raw_html2):

    res = VerbixApi.parse( verbix_sample_raw_html1 )
    print( res )

    res = VerbixApi.parse( verbix_sample_raw_html2 )
    print( res )

@pytest.mark.xfail(raises=RemoteApiUnavailable, reason="remote api unavailable")
@pytest.mark.skipif(not settings.lang.apis.verbix.enabled, reason="remote api disabled")
def test_verbix_get():

    # VerbixApi.clear_conjugates( "eat" )
    res = VerbixApi.get_conjugates( "eat" )
    assert res == Conjugates(infinitive=None,
               participle='eaten',
               gerund='eating',
               _1s='eat',
               _2s='eat',
               _3s='eats',
               _1p='eat',
               _2p=None,
               _3p='eat',
               source='verbix')


@pytest.mark.skip(reason="No ref-lex yet")
def test_lexref_conjugate():
    from tangl.narrative.lang.ref_lex import RefLex
    res = RefLex.conjugate( "eat", "_1s")
    print( res )
    assert res == "eat"

    res = RefLex.conjugate( "eat", "participle")
    print( res )
    assert res == "eaten"


def test_mw_synonym_parser(mw_sample_data):

    res = MeriamWebsterApi.distill_synonyms( mw_sample_data )


@pytest.mark.skipif(not settings.lang.apis.languagetool.enabled, reason="remote api disabled")
@pytest.mark.xfail(raises=RemoteApiUnavailable, reason="remote api unavailable")
def test_language_tool():

    res = LanguageToolApi.check( "hello this is a dog")

    print( res )
    assert len( res ) > 0

    res = LanguageToolApi.check( "hello this is a dog", disabled_rules=['UPPERCASE_SENTENCE_START'])

    print( res )
    assert not res
