"""Render a modified sprite."""

from pathlib import Path

from functools import lru_cache
from dataclasses import dataclass
from PIL import Image  # type: ignore
from typing import List, Optional, Tuple

from factorio_noir.category import SpriteTreatment
from factorio_noir.mod import LazyFile


def process_sprite(
    lazy_source_file: LazyFile,
    lazy_match_size_file: Optional[LazyFile],
    target_file_path: Path,
    treatment: SpriteTreatment,
) -> None:
    """Process a sprite"""

    target_file_path.parent.mkdir(exist_ok=True, parents=True)

    if lazy_match_size_file is not None:
        with lazy_match_size_file.open() as match_size_file:
            new_size = Image.open(match_size_file).size
    else:
        new_size = None

    with lazy_source_file.open() as source_file:
        sprite = Image.open(source_file).convert("RGBA")
        processed_sprite = apply_transforms(
            sprite,
            treatment,
            new_size,
        )
        processed_sprite.save(target_file_path)


@dataclass(eq=True, frozen=True)
class ColorSpace:
    """A color space."""

    X: float
    Y: float
    Z: float

    @lru_cache()
    def matrix(self, saturation: float, brightness: float) -> List[float]:
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


def apply_transforms(
    image: Image, treatment: SpriteTreatment, new_size: Optional[Tuple[float, float]]
) -> Image:
    """Apply the needed transformations to the given image."""
    img_alpha = image.getchannel("A")
    img_rgb = image.convert("RGB")

    color_space = DEFAULT_COLORSPACE.matrix(treatment.saturation, treatment.brightness)

    img_converted = img_rgb.convert("RGB", color_space)

    for bounding_box, tile_strength in treatment.tiles(image.width, image.height):
        if tile_strength == 1:
            # we are wanting this tile left untouched
            continue

        image_box = img_rgb.crop(bounding_box)
        converted_box = img_converted.crop(bounding_box)

        blended_box = Image.blend(image_box, converted_box, tile_strength)

        img_converted.paste(blended_box, bounding_box)

    img_converted.putalpha(img_alpha)

    if new_size is not None and img_converted.size != new_size:
        img_converted = img_converted.resize(new_size)

    return img_converted
