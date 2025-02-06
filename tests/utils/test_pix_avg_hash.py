import pytest
from PIL import Image
from tangl.utils.pixel_avg_hash import pix_avg_hash

def test_pix_avg_hash():
    # Create a 10x10 black image
    im = Image.new('RGB', (10, 10), color = 'black')
    # Since all pixels are the same (black), the hash should be 'f'*25
    assert pix_avg_hash(im) == 'f' * 25

    # Create a 10x10 white image
    im = Image.new('RGB', (10, 10), color = 'white')
    # Since all pixels are the same (white), the hash should be 'f'*25
    assert pix_avg_hash(im) == 'f' * 25

    # Create a 10x10 checkerboard image
    pixels = []
    for i in range(10):
        for j in range(10):
            if (i + j) % 2 == 0:
                pixels.append((255, 255, 255))  # white
            else:
                pixels.append((0, 0, 0))  # black
    im = Image.new('RGB', (10, 10))
    im.putdata(pixels)
    # Since the image is a checkerboard, the hash value will depend on the specific implementation of the function
    # Without knowing the specific expected hash, we can at least check that it doesn't hash to 'f'*25 or '0'*25
    hash_val = pix_avg_hash(im)
    assert hash_val != 'f' * 25
    assert hash_val != '0' * 25
    print( hash_val )

    assert hash_val == '559aa559aa559aa559aa559aa'
