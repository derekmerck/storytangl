import pytest
from click.testing import CliRunner
from PIL import Image, PngImagePlugin
from tangl.media.illustrated.stableforge.scripts.annotate_images import annotate_images

@pytest.fixture
def test_image(tmp_path):
    # Create a new image with RGB mode and white background
    img = Image.new('RGB', (704, 512), color = (255, 255, 255))

    # Prepare the info field
    info = PngImagePlugin.PngInfo()
    info.add_text("parameters", "stunning realistic photo of friendly bard aria with long purple hair lavender dress pink fairy butterfly wings highres masterpiece\nNegative prompt: cg 3d rendering lowres cartoon anime\nSteps: 28, Sampler: Euler a, CFG scale: 4.5, Seed: 1408737212, Size: 704x512, Model hash: 9aba26abdf")

    # Save the image with the info field
    test_file = tmp_path / "test_image.png"
    img.save(test_file, pnginfo=info)

    return test_file

@pytest.mark.skip(reason="output not going to stdout with click anymore")
def test_annotate_images(test_image):

    with Image.open(test_image) as im:
        # print( im )
        # im.show()
        assert im

    runner = CliRunner()
    result = runner.invoke(annotate_images, ['-d', str(test_image)])

    # Check the output
    assert result.exit_code == 0
    print(result.output)
    assert '-------INFO-------' in result.output
    assert '-------SPEC-------' in result.output
    assert '-------XMP-------' not in result.output

    result = runner.invoke(annotate_images, ['-g', str(test_image)])

    # Check the output
    assert result.exit_code == 0
    assert '-------INFO-------' not in result.output
    assert '-------SPEC-------' in result.output
    assert '-------XMP-------' in result.output
    print(result.output)
