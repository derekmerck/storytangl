def adjective_to_adverb(adjective):
    irregular_adverbs = {
        "good": "well",
        "ashamed": "shamefully",
        "disgraced": "disgracefully",
        # Add other irregular adjectives and their adverb forms here as needed
    }

    ignore_adjectives = {
        'soupy', 'mindbroken', "full", "sultry", "exhausted",
        "spent", "fatigued", "drained", "beat", "luscious",
        "bald", "shaved", "humiliated"
    }

    if adjective in ignore_adjectives or \
            adjective.find(" ") > 0 or \
            adjective.endswith("-") or \
            adjective.endswith("ering"):
        return None

    if adjective in irregular_adverbs:
        return irregular_adverbs[adjective]

    if adjective.endswith("y"):
        # Replace 'y' with 'ily'
        return adjective[:-1] + "ily"
    elif adjective.endswith("le") and len(adjective) > 2:
        # Replace the ending 'e' with 'y'
        return adjective[:-1] + "y"
    elif adjective.endswith("ic"):
        # Add 'ally' for adjectives ending with 'ic'
        return adjective + "ally"
    else:
        # Append 'ly' for the regular case
        return adjective + "ly"
