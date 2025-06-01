# import inflect

# def plural(arg: str):
#     if not arg:
#         return ''
#     p = inflect.engine()
#     p.classical(all=True)
#     return p.plural(arg)
#
#
# def num2word(arg: int):
#     p = inflect.engine()
#     p.classical(all=True)
#     return p.number_to_words(arg)


def oxford_join(values: list[str]):
    if not values:
        return ""
    if len(values) == 1:
        return values[0]
    if len(values) == 2:
        return f"{values[0]} and {values[1]}"
    else:
        values[-1] = f"and {values[-1]}"
        return ", ".join(values)
