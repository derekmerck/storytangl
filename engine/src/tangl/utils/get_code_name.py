"""
Generates a random password-like 'code name'.

>>> get_code_name()
Fulsome Dost0y3vsky

I'm not going to calculate out the size of the range, but it's pretty big.
Empirical testing suggests that with default settings, it will generate less
than 1 duplicate per thousand generations.

Unit test is set to confirm less than 5 repeats in 5000.

The engine can also pass namebanks to the function, which could be updated
by each world, for example.
"""

import random
import re

MORPH_SWAP_PROBABILITY = 0.35
MIN_SUBS = 2
MAX_SUBS = 4

# default namebanks
ADJECTIVES = ('adamant', 'adroit', 'amatory', 'animistic', 'antic', 'arcadian', 'baleful', 'bellicose', 'bilious', 'boorish', 'calamitous', 'caustic', 'cerulean', 'comely', 'concomitant', 'contumacious', 'corpulent', 'crapulous', 'defamatory', 'didactic', 'dilatory', 'dowdy', 'efficacious', 'effulgent', 'egregious', 'endemic', 'equanimous', 'execrable', 'fastidious', 'feckless', 'fecund', 'friable', 'fulsome', 'garrulous', 'guileless', 'gustatory', 'heuristic', 'histrionic', 'hubristic', 'incendiary', 'insidious', 'insolent', 'intransigent', 'inveterate', 'invidious', 'irksome', 'jejune', 'jocular', 'judicious', 'lachrymose', 'limpid', 'loquacious', 'luminous', 'mannered', 'mendacious', 'meretricious', 'minatory', 'mordant', 'munificent', 'nefarious', 'noxious', 'obtuse', 'parsimonious', 'pendulous', 'pernicious', 'pervasive', 'petulant', 'platitudinous', 'precipitate', 'propitious', 'puckish', 'querulous', 'quiescent', 'rebarbative', 'recalcitrant', 'redolent', 'rhadamanthine', 'risible', 'ruminative', 'sagacious', 'salubrious', 'sartorial', 'sclerotic', 'serpentine', 'spasmodic', 'strident', 'taciturn', 'tenacious', 'tremulous', 'trenchant', 'turbulent', 'turgid', 'ubiquitous', 'uxorious', 'verdant', 'voluble', 'voracious', 'wheedling', 'withering', 'zealous')

NOUNS = ('Anderson', 'Austen', 'Balzac', 'Barrie', 'Baum', 'Beckett', 'Bierce', 'Bradbury', 'Brontë', 'Burroughs', 'Byron', 'Carroll', 'Cazotte', 'Cervantes', 'Chekhov', 'Christie', 'Conrad', 'Dahl', 'Dante', 'Defoe', 'Dickens', 'Doré', 'Dostoyevsky', 'Doyle', 'Dumas', 'Eliot', 'Faulkner', 'Fielding', 'Fitzgerald', 'Gaiman', 'Goethe', 'Grimm', 'Hardy', 'Hawthorne', 'Hugo', 'Ibsen', 'James', 'Joyce', 'Kafka', 'Kant', 'King', 'Kipling', 'Lewis', 'Lovecraft', 'Márquez', 'Machiavelli', 'Melville', 'Milne', 'Nabokov', 'Nietzsche', 'Orwell', 'Poe', 'Pope', 'Potter', 'Scott', 'Shakespeare', 'Shaw', 'Shelley', 'Smollett', 'Stevenson', 'Stoker', 'Swift', 'Thoreau', 'Tolkien', 'Tolstoy', 'Twain', 'Verne', 'Vonnegut', 'Wagner', 'Wells', 'Wharton', 'Wilde', 'Wodehouse', 'Woolf')

############################
# MORPHEME SWAPS modified from 'leetit'
############################

MORPHEME_SWAPS = (
    (re.compile(r"\B(ckers|kers)\b"), ["xxorz", "xzorz", "zzorz"]),
    (re.compile(r"(?=[^k])(ers|ors)\b"), ["xorz", "zorz"]),
    (re.compile(r"\B([ck]?ker)\b"), ["xxor", "xzor", "zzor"]),
    (re.compile(r"(?=[^k])(er|or)\b"), ["xor", "zor"]),
    (re.compile(r"\B(cks)\b"), ["xx"]),
    (re.compile(r"(and|end|anned|ant)"), ["&"]),
    (re.compile(r"(ait|ate)"), ["8"]),
    (re.compile(r"(star)"), ["*"]),
    (re.compile(r"\B(ent)\b"), ["wnt"]),
    (re.compile(r"\B(ist)\b"), ["izd"]),
    (re.compile(r"\B(ian)\b"), ["yan"]),
    (re.compile(r"\B(ism)\b"), ["izm"]),
    (re.compile(r"\B(es+)\b"), ["ez"]),
    (re.compile(r"\B(s+)\b"), ["z"]),
    (re.compile(r"\B(th)\b"), ["z"]),
    (re.compile(r"\B(ed)\b"), ["t", "et"]),
    (re.compile(r"(?=[^q])(o?u)(?=[^eu])"), ["oo"]),
    (re.compile(r"(w)"), ["uu", "2u"]),
)

def morphology(text: str, morph_prob = MORPH_SWAP_PROBABILITY) -> str:
    text = text.lower()
    for m in MORPHEME_SWAPS:
        flag = False
        regexp = m[0]
        subs = m[1]
        fragments = regexp.split(text)
        if len(fragments) > 1:
            text = ""
            fragment_pairs = list(zip( fragments[::2], fragments[1::2]))
            for fragment, match in fragment_pairs:
                text += fragment
                r = random.random()
                swap = r < morph_prob
                if swap and not flag:
                    text += random.choice(subs)
                    flag = True  # only use the same morph once in a string
                else:
                    text += match
            text += fragments[-1]

    return text

ALPHABET_MAP = {
    "i": ['!'],
    "l": ['1', "|"],
    "z": ['2'],
    "e": ['3'],
    "h": ['#'],
    "a": ['4', '@'],
    "s": ['5', '$'],
    "b": ['6'],
    "t": ['7'],
    "g": ['9'],
    "o": ['0'],
    "y": ['j'],
    "w": ['uu', '2u']
}

def substitutions(text: str, min_subs=MIN_SUBS, max_subs=MAX_SUBS):

    def _make_swap(char):
        if char == " ":
            return random.choice(["+", "_", "-", "^", "/"])
        if char in ALPHABET_MAP:
            return random.choice(ALPHABET_MAP[char])
        if char.isupper():
            return char.lower()
        return char.upper()

    text = text.title()
    num_swaps = random.randint(min_subs, max_subs+1)
    indices = range(0, len(text)-1)
    swaps = random.choices(indices, k=num_swaps)
    for i in swaps:
        char = text[i]
        repl = _make_swap(char)
        text = text[:i] + repl + text[i+1:]

    return text

def get_code_name(adjectives: list[str] = None, nouns: list[str] = None, morph=True, sub=True):
    adjectives = adjectives or ADJECTIVES
    nouns = nouns or NOUNS
    adj = random.choice( adjectives ).lower()
    noun = random.choice( nouns ).lower()
    text = f"{adj} {noun}"
    if morph:
        text = morphology( text )
    if sub:
        text = substitutions( text )
    if not (morph or sub):
        text = text.title()
    return text
