import yaml
import re
from functools import partial

gendered_nominals_ = """
- [ abbot, abbess ]
- [ actor, actress ]
- [ asshole, bitch ]
- [ bachelor, maiden ]
- [ barman, barmaid ]
- [ baron, baroness ]
- [ boy, girl ]
- [ brother, sister ]
- [ bull, cow ]
- [ chairman, chairwoman ]
- [ cock, hen ]
- [ count, countess ]
- [ czar, czarina ]
- [ dad, mom ]
- [ daddy, mommy ]
- [ dog, bitch ]
- [ drake, duck ]
- [ duke, duchess ]
- [ earl, countess ]
- [ emperor, empress ]
- [ enchanter, enchantress ]
- [ father, mother ]
- [ father general, mother superior ]
- [ gander, goose ]
- [ gentleman, lady ]
- [ giant, giantess ]
- [ god, goddess ]
- [ grandfather, grandmother ]
- [ groom, bride ]
- [ guy, chick ]
- [ hart, roe ]
- [ headmaster, headmistress ]
- [ hero, heroine ]
- [ host, hostess ]
- [ hunter, huntress ]
- [ husband, wife ]
- [ incubus, succubus ]
- [ jew, jewess ]
- [ king, queen ]
- [ landlord, landlady ]
- [ lion, lioness ]
- [ lord, lady ]
- [ male, female ]
- [ man, woman ]
- [ men, women ]
- [ marquis, marchioness ]
- [ masculine, feminine ]
- [ master, mistress ]
- [ mister, miss ]
- [ monk, nun ]
- [ moor, moura ]
- [ mr, ms ]               # period confuses the system
- [ negro, negress ]
- [ nephew, niece ]
- [ pants, skirt ]
- [ peacock, peahen ]
- [ policeman, policewoman ]
- [ priest, priestess ]
- [ prince, princess ]
- [ samurai, onna-musha ]
- [ signor, signora ]
- [ sir, miss ]            # wanted to use ma'am, but the apostrophe confuses the system
- [ son, daughter ]
- [ stag, hind ]
- [ steward, maid ]
- [ sultan, sultana ]
- [ taikomochi, geisha ]    # masculine is 'jester'
- [ tempter, temptress ]
- [ tiger, tigress ]
- [ uncle, aunt ]
- [ viscount, viscountess ]
- [ waiter, waitress ]
- [ wallet, purse ]
- [ widower, widow ]
- [ wizard, witch ]
"""

gendered_nominals = yaml.safe_load( gendered_nominals_ )
xx_map = { m: (m, f) for m, f in gendered_nominals }
xx_map.update( { f: (m, f) for m, f in gendered_nominals } )

def gn(word: str, is_xx: bool = True):
    """
    Input: a gendered nominal, is_xx
    Output: the corrected form gendered nominal
    """
    if isinstance(word, re.Match):
        word = word.group(0)
    key = word.lower()
    if key in xx_map:
        new_word = xx_map[key][ int( is_xx ) ]
        if word.istitle():
            new_word = new_word.title()
        return new_word
    return word

is_xx_patterns = r"(\b" + r"\b|\b".join(list(xx_map)) + r"\b)"
is_xx_regex = re.compile(is_xx_patterns, re.IGNORECASE)

def normalize_gn(s: str, is_xx: bool = True):
    return is_xx_regex.sub(partial(gn, is_xx=is_xx), s)

# <ignore>

# The legacy code for this is interesting.  It programmatically injected properties for each term into the 'Actor' class, so they could be referenced by Jinja templates "A {{ my_actor.guy }} is here." and it would automatically render the code to reflect the actor's current gender.  The code goes into some detail regarding capitalization and the use of the leading or trailing underscore to distinguish possessive from objective pronouns (her_ dog, the dog's owner is _her).  That has been entirely factored out in the pronoun module, so it simplified handling the words significantly.  It also dynamically wrote out a pyi stub file, so the Actor class would not be type-flagged for using such expressions.

# language=Python
"""
def add_desc_helpers(cls, test, **kwargs):

    def fget_wrapper(test, ok, nok):
        def fget(self) -> str:
            return test(self) and ok or nok

        return fget

    pyi_hints = f"class {cls.__name__}:\n"

    def handle_underscores(s):  # ss out and SS in
        if s.startswith("_"):
            r = s[1:]
            R = r.capitalize()
            _r = s
            _R = "_" + R

        elif k.endswith("_"):
            r = s[:-1]
            R = r.capitalize()
            _r = s
            _R = R + "_"

        else:
            r = s
            R = r.capitalize()
            _r = s
            _R = R

        return _r, _R, r, R

    for k, v in kwargs.items():
        _k, _K, kk, KK = handle_underscores(k)
        _v, _V, vv, VV = handle_underscores(v)

        prop = property(fget_wrapper(test, kk, vv))
        setattr(cls, _k, prop)
        setattr(cls, _v, prop)

        prop = property(fget_wrapper(test, KK, VV))
        setattr(cls, _K, prop)
        setattr(cls, _V, prop)

        pyi_hints += f"\t{_k}: str\n\t{_v}: str\n\t{_K}: str\n\t{_V}: str\n"

    return pyi_hints


kwargs = {

    "_her": "him",   # obj, gave to her
    "her_": "his_",  # possessive, her dog
    "hers": "_his",  # possessive passive, dog was hers

    "she": "he",
    "herself": "himself", 
    ...  # etc as with 'gendered_nominals' var
}

test = lambda self: self.gens == G.XX
add_desc_helpers(ActorDescMixin, test, **kwargs)
"""
# </ignore>
