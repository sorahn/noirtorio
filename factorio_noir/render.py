"""Render a modified sprite."""

from pathlib import Path

from functools import lru_cache
from dataclasses import dataclass
from PIL import Image  # type: ignore
from typing import List, Optional, Tuple, Iterable, NewType
import math

from factorio_noir.category import SpriteTreatment
from factorio_noir.mod import LazyFile

Matrix = NewType("Matrix", List[List[float]])


def process_sprite(
    lazy_source_file: LazyFile,
    lazy_match_size_file: Optional[LazyFile],
    target_file_path: Path,
    treatment: SpriteTreatment,
    bright: bool,
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
            bright,
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
    def matrix(self, saturation: float, brightness: float, hue: float) -> List[float]:
        """Return a color space matrix for given saturation and brightess."""

        # print("Getting matrix:", saturation, brightness, hue)
        matrix = self.saturation_matric(saturation)

        if brightness != 1:
            matrix = self.scale_matrix(matrix, brightness)

        if hue != 0:
            matrix = self.rotate_matrix(matrix, hue)

        return list(self.flatten_matrix(matrix))

    def saturation_matric(self, saturation: float) -> Matrix:
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

        return Matrix(
            [
                [
                    self.X + (1 - self.X) * saturation,
                    self.Y * (1 - saturation),
                    self.Z * (1 - saturation),
                ],
                [
                    self.X * (1 - saturation),
                    self.Y + (1 - self.Y) * saturation,
                    self.Z * (1 - saturation),
                ],
                [
                    self.X * (1 - saturation),
                    self.Y * (1 - saturation),
                    self.Z + (1 - self.Z) * saturation,
                ],
            ]
        )

    def scale_matrix(self, m: Matrix, scale: float) -> Matrix:
        return Matrix([[c * scale for c in row] for row in m])

    def rotate_matrix(self, m: Matrix, theta: float) -> Matrix:
        # see: https://en.wikipedia.org/wiki/Rodrigues%27_rotation_formula
        #   rotation_matrix = I + sin(theta)*k + (1-cos(theta))*(k*k)

        x, y, z = self.normalize([self.X, self.Y, self.Z])

        k = Matrix(
            [
                [0, -z, y],
                [z, 0, -x],
                [-y, x, 0],
            ]
        )

        k2 = self.matrix_multiply(k, k)

        identy_matrix = Matrix(
            [
                [1.0, 0.0, 0.0],
                [0.0, 1.0, 0.0],
                [0.0, 0.0, 1.0],
            ]
        )

        rotation_matrix = self.matrix_add(
            identy_matrix,
            self.scale_matrix(k, math.sin(theta * math.tau)),
            self.scale_matrix(k2, 1 - math.cos(theta * math.tau)),
        )

        return self.matrix_multiply(m, rotation_matrix)

    def matrix_add(self, m1: Matrix, *others: Matrix) -> Matrix:
        for m2 in others:
            m1 = Matrix(
                [
                    [c1 + c2 for (c1, c2) in zip(row1, row2)]
                    for (row1, row2) in zip(m1, m2)
                ]
            )

        return m1

    def matrix_multiply(self, m1: Matrix, *others: Matrix) -> Matrix:
        for m2 in others:
            # We don't strictly need this transpose, but it makes the
            # iteration much nicer
            m2 = self.transpose(m2)

            m1 = Matrix([[self.dot_product(row1, row2) for row2 in m2] for row1 in m1])
        return m1

    def transpose(self, m: Matrix) -> Matrix:
        return Matrix(
            [
                [m[col_i][row_i] for col_i, _ in enumerate(row)]
                for row_i, row in enumerate(m)
            ]
        )

    def flatten_matrix(self, m: Matrix) -> Iterable[float]:
        # Pillow wants a flat array of a 3x4 matrix

        for row in m:
            for c in row:
                yield c
            yield 0

    def normalize(self, v: List[float]) -> List[float]:
        length = math.sqrt(sum(e * e for e in v))

        return [e / length for e in v]

    def dot_product(self, v1: List[float], v2: List[float]) -> float:
        return sum(e1 * e2 for (e1, e2) in zip(v1, v2))


def apply_transforms(
    image: Image,
    treatment: SpriteTreatment,
    bright: bool,
    new_size: Optional[Tuple[float, float]],
) -> Image:
    """Apply the needed transformations to the given image."""
    img_alpha = image.getchannel("A")
    img_rgb = image.convert("RGB")

    sat = treatment.saturation
    bri = treatment.brightness

    if bright:
        if sat <= 0.9:
            sat += 0.1

        if bri <= 0.9:
            bri += 0.1

    transformation_matrix = ColorSpace(*treatment.color_space).matrix(
        sat, bri, treatment.hue
    )

    img_converted = img_rgb.convert("RGB", transformation_matrix)

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
