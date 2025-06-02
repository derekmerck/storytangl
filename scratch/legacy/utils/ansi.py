"""
Requires colorama, cairo, and climage2ansi
"""

import re
from io import BytesIO
try:
    from colorama import Fore, Style
    import cairosvg
    import climage
except:  # pragma: no cover
    from warnings import warn
    warn("No ansi utils avail")

def span2ansi(s):
    # See https://stackoverflow.com/a/33206814

    replacements = {
        '#b94f3a': u'\u001b[38;5;166m',
        'green': Fore.GREEN,
        'red': Fore.RED,
        'crimson': Fore.RED,
        'blue': Fore.BLUE,
        'plum': Fore.MAGENTA,
        'purple': Fore.MAGENTA,
        'yellow': Fore.YELLOW,
        'yellowgreen': u'\u001b[38;5;155m',
        'gold': Fore.YELLOW,
        'pink': Fore.LIGHTRED_EX,
        'silver': Fore.LIGHTWHITE_EX,
    }
    for k, v in replacements.items():
        rex = re.compile(f"<span style='color: ?{k}'>")
        s = rex.sub(v, s)
    rex = re.compile("</span>")
    s = rex.sub(Style.RESET_ALL, s)

    rex = re.compile(r"<[ib]>")
    s = rex.sub( u'\u001b[3m', s )
    rex = re.compile(r"</[ib]>")
    s = rex.sub( u'\u001b[0m', s )
    return s

def ansi_linewrap(s, width=80):
    ansi_escape = re.compile(r'(?:\x1B[@-_]|[\x80-\x9F])[0-?]*[ -/]*[@-~]')

    def get_line(s, width=80):
        j = 0
        output = ""
        for i, c in enumerate( s ):
            if c == "\n":
                output += c
                return output

            m = ansi_escape.match(s[i:])

            if m:
                # Next few chars are ansi, back-off count
                j -= m.end() - 1
            else:
                j += 1
            output += c

            if j > width:
                # backup
                jj = len(output)-1
                while output[jj] != " ":
                    jj -= 1
                output = output[:jj] + "\n"
                return output # overran line
        return output  # ran out of content

    output_ = ""
    while s:
        line = get_line(s, width)
        output_ += line
        # print( line, width )
        s = s[len(line):]
    return output_


def svg2ansi(svg: str, width=80) -> str:
    png = cairosvg.svg2png(svg)
    b = BytesIO(png)
    ansi = climage.convert(b, is_unicode=True, width=width)
    return ansi