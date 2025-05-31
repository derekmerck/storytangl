import importlib.resources

from enum import Enum
from pathlib import Path
import csv

treebank_symbols = {}
with open( importlib.resources.files("tangl.narrative.lang.pos") / "treebank-symbols.csv" ) as f:
    reader = csv.DictReader(f, fieldnames=['id', 'tag', 'desc'])
    for row in reader:
        treebank_symbols[row['tag']] = row['id'], row['desc']

TreeBankSymbols = Enum( "TreeBankSymbols",
                        { k: v[0] for k, v in treebank_symbols.items() } |
                        { k.replace('$', '5'): v[0] for k, v in treebank_symbols.items() if "$" in k }
                        )

def desc(self: TreeBankSymbols):
    return treebank_symbols[self.name][1]

def _missing_(cls: TreeBankSymbols, value):
    if isinstance(value, str) and '$' in value:
        value = value.replace('$', '5')
        return cls( value )
    for k, v in cls.__members__.items():
        if value == k:
            return v

def is_verb(self: TreeBankSymbols):
    if self in [self.VBD, self.VBP, self.VBZ]:
        return True
    return False

def is_noun(self: TreeBankSymbols):
    if self in [self.NN, self.NNP, self.NNS, self.NNPS, self.PRP]:
        return True
    return False

def is_adj(self: TreeBankSymbols):
    if self in [self.PRP5, self.JJ, self.JJR, self.JJS]:
        return True
    return False


TreeBankSymbols.desc = desc
TreeBankSymbols._missing_ = classmethod(_missing_)
TreeBankSymbols.is_verb = is_verb
TreeBankSymbols.is_noun = is_noun
TreeBankSymbols.is_adj = is_adj

def generate_stub():
    """This only has to be invoked once, to populate the .pyi stub file"""

    s =       "from enum import Enum\n"
    s +=      "class TreeBankSymbols(Enum):\n"
    for name, member in TreeBankSymbols.__members__.items():
        if "$" in name:
            # Skip the dollar signs but keep the aliases with $->5
            continue
        s += f"    {name} = {member.value}\n"
    s +=      "    def desc(self)->str: ... \n"
    s +=      "    def is_verb(self)->bool: ... \n"
    s +=      "    def is_noun(self)->bool: ... \n"
    s +=      "    def is_adj(self)->bool: ... \n"
    with open( Path(__file__).parent / "treebank_symbols.pyi", "w") as f:
        f.write( s )


if __name__ == "__main__":
    print(TreeBankSymbols.__members__)
    generate_stub()
