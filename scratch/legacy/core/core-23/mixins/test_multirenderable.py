# No longer supported

from tangl.core.renderable import Renderable, MultiRenderable



def test_multi_renderable():

    r = MultiRenderable(
        descs = ["Hello {{ name }}", "Goodbye {{ name }}"]
    )

    print("--------------")
    res = r.desc( which=0, name="tangldev" )
    print(res)
    assert res == "Hello tangldev"

    res = r.desc( which=1, name="tangldev" )
    print(res)
    assert res == "Goodbye tangldev"


if __name__ == "__main__":
    test_renderable()
    test_multi_renderable()
