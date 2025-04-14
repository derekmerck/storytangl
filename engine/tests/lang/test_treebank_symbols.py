
from tangl.narrative.lang.pos import TreeBankSymbols

def test_treebank_helper_funcs():

    for symbol in TreeBankSymbols.__members__.values():

        print( symbol.desc() )
        print( symbol.is_verb() )
        print( symbol.is_noun() )
        print( symbol.is_adj() )

def test_treebank_alias():

    assert TreeBankSymbols('PRP$') == TreeBankSymbols.PRP5
