import yaml
import re
from functools import partial

# Some neutrals noted when _not_ adopting the masc form
# Words with substrings
# - man/woman -> person, i.e., chairperson
# - son/daughter -> child, i.e., grandchild

gendered_nominals_ = """
- [ abbot, abbess ]
- [ actor, actress ]
- [ asshole, bitch ]
- [ bachelor, maiden ]
- [ barman, barmaid ]  # n: bartender
- [ baron, baroness ]
- [ boar, sow ]        # n: pig
- [ boy, girl ]        # n: child
- [ brother, sister ]  # n: sibling
- [ buck, doe ]        # n: deer
- [ bull, cow ]        # n: cow, heifer - young female before breeding
- [ chairman, chairwoman ]
- [ cock, hen ]        # n: bird
- [ colt, filly ]      # n: foal
- [ count, countess ]
- [ czar, czarina ]
- [ dad, mom ]       
- [ daddy, mommy ]
- [ dog, bitch ]
- [ drake, duck ]      # n: duck
- [ duke, duchess ]
- [ earl, countess ]
- [ emperor, empress ]
- [ enchanter, enchantress ]
- [ father, mother ]  # n: parent
- [ father general, mother superior ]
- [ gander, goose ]   # n: goose
- [ gentleman, lady ]
- [ giant, giantess ]
- [ god, goddess ]
- [ grandfather, grandmother ]
- [ grandson, granddaughter ]
- [ groom, bride ]
- [ guy, chick ]
- [ hart, hind ]      # n: deer
- [ headmaster, headmistress ]
- [ hero, heroine ]
- [ host, hostess ]
- [ hunter, huntress ]
- [ husband, wife ]
- [ incubus, succubus ]  # n: succubus
- [ jew, jewess ]
- [ king, queen ]
- [ landlord, landlady ]
- [ lion, lioness ]
- [ lord, lady ]
- [ male, female ]
- [ man, woman ]
- [ men, women ]
- [ marquis, marchioness ]
- [ masculine, feminine ]  # n: non-binary?
- [ master, mistress ]
- [ patriarch, matriarch ]
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
- [ satyr, nymph ]
- [ signor, signora ]
- [ sir, miss ]            # wanted to use ma'am, but the apostrophe confuses the system
- [ son, daughter ]
- [ stag, hind ]           # n: deer, alternate masculine form for hart/hind
- [ steward, maid ]
- [ sultan, sultana ]
- [ taikomochi, geisha ]   # n: geisha, masculine means 'jester'
- [ tempter, temptress ]
- [ tiger, tigress ]
- [ uncle, aunt ]
- [ viscount, viscountess ]
- [ waiter, waitress ]     # n: server
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

# Match longer phrases before their single-word prefixes (for example,
# "father general" before "father").
_ordered_nominals = sorted(xx_map, key=lambda word: (-len(word), word))
is_xx_patterns = r"(\b" + r"\b|\b".join(_ordered_nominals) + r"\b)"
is_xx_regex = re.compile(is_xx_patterns, re.IGNORECASE)

def normalize_gn(s: str, is_xx: bool = True):
    return is_xx_regex.sub(partial(gn, is_xx=is_xx), s)
