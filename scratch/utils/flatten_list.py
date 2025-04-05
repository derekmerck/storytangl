
def flatten(list_of_lists):
    # I can never remember this syntax...
    flattened_list = [item for sublist in list_of_lists for item in sublist]
    return flattened_list
