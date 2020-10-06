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
        saturation=treatment.saturation,
        brightness=treatment.brightness,
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


def apply_transforms(image, saturation, brightness):
    """Apply the needed transformations to the given image."""
    img_alpha = image.getchannel("A")
    img_rgb = image.convert("RGB")

    color_space = DEFAULT_COLORSPACE.matrix(saturation, brightness)

    img_converted = img_rgb.convert("RGB", color_space)
    img_converted.putalpha(img_alpha)

    return img_converted

