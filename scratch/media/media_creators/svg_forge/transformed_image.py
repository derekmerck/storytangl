from PIL import Image


class TransformedImage(Image.Image):
    def __init__(self, image, *args, position: tuple[int, int] = (0, 0), scale: tuple[float, float] = (1., 1.), **kwargs):

        self.__dict__.update(image.__dict__)
        self.position = position  # (x, y)
        self.scale = scale        # (sx, sy)

    def apply_transform(self):
        # Apply the scaling
        width, height = self.size
        new_size = (int(width * self.scale[0]), int(height * self.scale[1]))
        scaled_image = self.resize(new_size, Image.BICUBIC)
        return scaled_image

    @classmethod
    def from_file(cls, fn, *args, **kwargs):
        im = Image.open(fn)
        im.load()
        im.convert('RGBA')
        return cls(im, *args, **kwargs)


def composite_images(base_image: Image.Image, transformed_images: list[TransformedImage]):
    for transformed_image in transformed_images:
        transformed = transformed_image.apply_transform()
        # base_image.alpha_composite(transformed_image, transformed_image.position )
        base_image.paste(transformed, transformed_image.position, transformed.point(lambda x: 255 if x > 8 else 0, mode="1"))  # if transformed.mode == 'RGB' else None)
    return base_image

# # Example usage:
# base_image = Image.new('RGBA', (500, 500), (255, 255, 255, 255))  # Create a white base image
#
# # Create some transformed images
# transformed_images = [
#     TransformedImage(Image.new('RGBA', (100, 100), (255, 0, 0, 128)), position=(50, 50)),
#     TransformedImage(Image.new('RGBA', (150, 150), (0, 255, 0, 128)), position=(200, 100), scale=(0.5, 0.5)),
#     TransformedImage(Image.new('RGBA', (200, 200), (0, 0, 255, 128)), position=(300, 300), scale=(0.25, 0.25)),
# ]
#
# # Composite the images
# result_image = composite_images(base_image, transformed_images)
# result_image.show()
