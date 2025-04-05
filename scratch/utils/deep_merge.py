
def deep_merge( source: dict, update ):
    """
    Merge two dictionaries recursively.

    Lists of dictionaries are zipped and each pair is merged individually.

    Keys marked with an initial "_" are considered important and the
    most recent value is preserved under the non-underscored key.
    """

    if not isinstance( update, dict ):
        return update

    for k, v in update.items():
        if k in source and isinstance(v, dict):
            deep_merge( source[k], v )
        elif k in source and isinstance(v, list):
            if isinstance( v[0], dict):
                for ss, vv in zip(source[k], v):
                    deep_merge(ss, vv)
            else:
                source[k] += v
        elif isinstance(source, str):
            pass  # This is a 'consumes' str, could compress it out
        else:
            source[k] = v

    for k in list( source.keys() ):
        # preserves important _keys
        if k.startswith("_"):
            source[k[1:]] = source[k]
