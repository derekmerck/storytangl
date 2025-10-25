
# Dependency matches extends direct adoptions to dependent words
from spacy.matcher import DependencyMatcher
matcher = DependencyMatcher(nlp.vocab)

# pattern = [
#     {
#         "RIGHT_ID": "voice_anchor",
#         # "RIGHT_ATTRS": {"ENT_TYPE": "VOICE"}
#         "RIGHT_ATTRS": {"POS": "PRON"}
#     },
#     {
#         "LEFT_ID": "voice_anchor",
#         "REL_OP": "<",
#         "RIGHT_ID": "voice_verb",
#         "RIGHT_ATTRS": {"POS": "VERB"},
#     }
# ]
#
# pattern = [
#     {
#         "RIGHT_ID": "voice_verb",
#         "RIGHT_ATTRS": {"TAG": {"IN": ["VBD", "VBP"]}}
#     },
#     {
#         "LEFT_ID": "voice_verb",
#         "REL_OP": ">",
#         "RIGHT_ID": "voice_subject",
#         "RIGHT_ATTRS": {"DEP": "nsubj",
#                         "TAG": "PRP",
#                         "ENT_TYPE": "VOICE"},
#     },
# ]
#
pattern = [
    {
        "RIGHT_ID": "voice_verb",
        "RIGHT_ATTRS": {"TAG": {"IN": ["VBD", "VBP"]},
                        'ENT_TYPE': "VOICE"}
    },
    {
        "LEFT_ID": "voice_verb",
        "REL_OP": ">",
        "RIGHT_ID": "voice_object",
        "RIGHT_ATTRS": {"DEP": {"IN": ["obj", "iobj", "obl"]}},
    },
]

# matcher.add('follow_voice', [pattern])

for doc in docs:
    matches = matcher(doc)
    if matches:
        for m in matches:
            match_id, toks = m
            print( doc[toks[1]],
                   doc[toks[1]].ent_id_,
                   doc[toks[0]],
                   doc[toks[0]].ent_id_ )
