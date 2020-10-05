"""Render a modified sprite."""

from pathlib import Path

import attr
from PIL import Image

from factorio_noir.category import SpriteTreatment


def process_sprite(sprite_path: Path, treatment: SpriteTreatment):
    """Process a sprite in-place, copy the file before to not affect the original."""
    sprite = Image.open(sprite_path).convert("RGBA")
    processed_sprite = apply_transforms(
        sprite,
        brightness=treatment.saturation,
        saturation=treatment.brightness,
    )
    sprite_path.unlink()
    processed_sprite.save(sprite_path)


@attr.s(auto_attribs=True)
class ColorSpace:
    """A color space."""

    X: float
    Y: float
    Z: float

    def matrix(self, saturation, brightness):
        """Return a color space matrix for given saturation and brightess."""
        saturated_matrix = [
            self.X + (self.Y + self.Z) * saturation,
            self.Y * (1 - saturation),
            self.Z * (1 - saturation),
            0,
            self.X * (1 - saturation),
            self.Y + (self.X + self.Z) * saturation,
            self.Z * (1 - saturation),
            0,
            self.X * (1 - saturation),
            self.Y * (1 - saturation),
            self.Z + (self.X + self.Y) * saturation,
            0,
        ]
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


def old_transforms(img_orig, brightness, saturation):
    img_alpha = img_orig.getchannel("A")
    img_rgb = img_orig.convert("RGB")

    # fmt: off
    # Numbers taken from factorio's shader. Keep in sync with data-final-fixes.lua
    color_space = (
        0.3086 + 0.6914 * saturation, 0.6094 - 0.6094 * saturation, 0.0820 - 0.0820 * saturation, 0,
        0.3086 - 0.3086 * saturation, 0.6094 + 0.3906 * saturation, 0.0820 - 0.0820 * saturation, 0,
        0.3086 - 0.3086 * saturation, 0.6094 - 0.6094 * saturation, 0.0820 + 0.9180 * saturation, 0,
    )
    # fmt: on

    color_space = list(c * brightness for c in color_space)

    img_converted = img_rgb.convert("RGB", color_space)
    img_converted.putalpha(img_alpha)

    return img_converted
