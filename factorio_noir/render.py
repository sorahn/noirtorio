"""Render a modified sprite."""

from pathlib import Path

from functools import lru_cache
from dataclasses import dataclass
from PIL import Image

from factorio_noir.category import SpriteTreatment


def process_sprite(source_path: Path, target_path: Path, treatment: SpriteTreatment):
    """Process a sprite"""

    target_path.parent.mkdir(exist_ok=True, parents=True)

    sprite = Image.open(source_path).convert("RGBA")
    processed_sprite = apply_transforms(
        sprite,
        treatment,
    )
    processed_sprite.save(target_path)


@dataclass(eq=True, frozen=True)
class ColorSpace:
    """A color space."""

    X: float
    Y: float
    Z: float

    @lru_cache()
    def matrix(self, saturation, brightness):
        """Return a color space matrix for given saturation and brightess."""

        # This matrix works by:
        # if saturation == 0:
        #     image[r] = (X*r + Y*g + Z*b + 0*a)
        #     image[g] = (X*r + Y*g + Z*b + 0*a)
        #     image[b] = (X*r + Y*g + Z*b + 0*a)
        #     # This converts the image to greyscale, along the (X, Y, Z) vector
        # elif saturation == 1:
        #     image[r] = (1*r + 0*g + 0*b + 0*a) = r
        #     image[g] = (0*r + 1*g + 0*b + 0*a) = g
        #     image[b] = (0*r + 0*g + 1*b + 0*a) = b
        #     # This leaves the image unchanged

        saturated_matrix = [
            self.X + (1 - self.X) * saturation,
            self.Y * (1 - saturation),
            self.Z * (1 - saturation),
            0,
            self.X * (1 - saturation),
            self.Y + (1 - self.Y) * saturation,
            self.Z * (1 - saturation),
            0,
            self.X * (1 - saturation),
            self.Y * (1 - saturation),
            self.Z + (1 - self.Z) * saturation,
            0,
        ]

        # Scale the matrix by the brightness to scale the final image
        return [c * brightness for c in saturated_matrix]


# Numbers taken from factorio's shader. Keep in sync with data-final-fixes.lua
DEFAULT_COLORSPACE = ColorSpace(X=0.3086, Y=0.6094, Z=0.0820)


def apply_transforms(image, treatment):
    """Apply the needed transformations to the given image."""
    img_alpha = image.getchannel("A")
    img_rgb = image.convert("RGB")

    color_space = DEFAULT_COLORSPACE.matrix(treatment.saturation, treatment.brightness)

    img_converted = img_rgb.convert("RGB", color_space)

    for x_index, x_tile in enumerate(treatment.tiling):
        y_max = len(x_tile)
        for y_index, tile_strength in enumerate(x_tile):
            if tile_strength == 1:
                continue

            # TODO: Double check for off by one errors here
            bounding_box = (
                int(image.width * x_index / len(treatment.tiling)),
                int(image.height * y_index / len(x_tile)),
                int(image.width * (x_index + 1) / len(treatment.tiling)),
                int(image.height * (y_index + 1) / len(x_tile)),
            )

            image_box = img_rgb.crop(bounding_box)
            # converted_box = img_converted.crop(bounding_box)

            # blended_box = image_box.blend(converted_box, tile_strength)

            # TODO: why doesn't blend work?
            assert tile_strength == 0
            blended_box = image_box

            img_converted.paste(blended_box, bounding_box)

    img_converted.putalpha(img_alpha)

    return img_converted
