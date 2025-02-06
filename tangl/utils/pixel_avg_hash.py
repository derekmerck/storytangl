from PIL import Image

def pix_avg_hash(im: Image) -> str:
    im_ = im.resize((10, 10), Image.Resampling.LANCZOS)
    im_ = im_.convert("L")
    pixel_data = list(im_.getdata())
    avg_pixel = sum(pixel_data) / len(pixel_data)
    bits = "".join(['1' if (px >= avg_pixel) else '0' for px in pixel_data])
    pixel_h = str(hex(int(bits, 2)))[2:][::-1]
    return pixel_h
