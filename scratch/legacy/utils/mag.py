"""
This is a useful jinja filter for automatically converting integers to magnitudes
such as 1345 to 1k or 1.3k.

It can also prefix or suffix a unit description like $ or 'km'.
"""
import typing as typ


def mag(value: typ.Union[int, float, dict], units: str = "", prefix_unit: bool = True) -> str:

    if value is None:
        return
    elif isinstance(value, dict):
        value = value['cash']

    map = [
        (1, ""),
        (1000, "K"),
        (1000000, "M"),
        (1000000000, "G"),
        (1000000000000, "T")
    ]

    num = 0
    suffix = ""
    for k, v in map:
        if value // k < 1000:
            if v == "":
                num = int( value / k )
            else:
                num = round( value / k, 1)
            suffix = v
            break

    if prefix_unit:
        ref = f"{units}{num}{suffix}"
    else:
        ref = f"{num}{suffix}{units}"

    return ref
