"""
Requires rembg package
"""
import io

from rembg import remove
from PIL import Image
from pathlib import Path

fg_path = Path( '~/Desktop/id_cards/03215-2866661853-pretty blonde scientist.png' ).expanduser()
bg_path = Path( '~/Desktop/id_cards/card_bg2.png').expanduser()
bg_frame_path = Path( '~/Desktop/id_cards/card_bg_frame3.png').expanduser()
wing_path = Path( '~/Desktop/id_cards/green_wing.png').expanduser()
fg_text_path = Path( '~/Desktop/id_cards/card_text.svg' ).expanduser()
# output_path = 'output.png'

from tangl.world.demographics.similar_name import similar_full_name
gn, fn = similar_full_name("Katya", "Goncharev")

# mk text
import cairosvg
with open(fg_text_path) as f:
    svg = f.read()

svg = svg.replace("Alice James", f"{gn} {fn}")

img_b = cairosvg.svg2png(svg)
img_b_io = io.BytesIO( img_b )
text_img = Image.open( img_b_io )


fg = Image.open(fg_path)
bg = Image.open(bg_path)
bg_frame = Image.open(bg_frame_path)

wing = Image.open(wing_path)
bg.paste( wing, box=(0, bg.size[1] - wing.size[1]), mask=wing )

fg_rembg = remove(fg)
ratio = ( bg.size[1] / fg.size[1] ) * 0.9
print( fg.size, bg.size, ratio )
new_dims = ( int(fg.size[0] * ratio), int(fg.size[1] * ratio ) )
fg_ = fg_rembg.resize( (new_dims), )
paste_offset = int( bg.size[1] * 0.1 )
bg.paste(fg_, mask=fg_, box=(paste_offset // 2, paste_offset))
bg.paste(bg_frame, mask=bg_frame)

from PIL import ImageFilter
text_img_b = text_img.filter(ImageFilter.GaussianBlur(radius=0.5))
paste_offset = int( bg.size[0] * 0.55 ), int( bg.size[1] * 0.2)
# bg.paste(text_img_b, mask=text_img_b, box=paste_offset)
bg.paste(text_img, mask=text_img_b, box=paste_offset)

bg.show()

bg.save(f"id_card_{gn}_{fn}.webp")

# output.save(output_path)