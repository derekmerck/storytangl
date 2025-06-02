import pytest

from legacy.utils.ansi import ansi_linewrap, span2ansi


@pytest.mark.xfail(raises=NameError, reason="No colorama support")
def test_ansi_char_handling():
    s = "here is a test\n"
    for sp in ['red', 'blue', 'green']:
        s += f"<span style='color: {sp}'>Some content for {sp}</span>\n"
    s += "the end of the test"

    assert s.find("span") > 0

    print(s)
    t = span2ansi(s)
    print(t)

    assert len(t) > 10
    assert t.find("span") < 0

    print()
    print("------------")

    tt = t.replace("\n", " ") + " """
    tt = tt * 10
    aa = ansi_linewrap(tt, 20)
    print(aa)


if __name__ == "__main__":
    test_ansi_char_handling()

