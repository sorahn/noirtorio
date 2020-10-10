"""A sprite category described in a YAML file."""
import itertools
from pathlib import Path
from typing import Dict, List, Set

import attr
from ruamel.yaml import YAML

SAFE_PARSER = YAML(typ="safe")


@attr.s(auto_attribs=True)
class SpriteTreatment:
    """Describe the treatment to execute on a given sprite."""

    saturation: float
    brightness: float
    tiling: List[List[float]]

    @classmethod
    def from_yaml(cls, yaml_fragment: Dict[str, float]):
        """Read the sprite treatment to do from a yaml fragment."""

        # Tiling is read as a list of strings to make it be layed out graphically
        tiling = [
            [float(t) for t in row.split()]
            for row in yaml_fragment.get("tiling", ["1"])
        ]

        assert len(tiling) > 0, "tiling must have at least 1 row"
        for row in tiling:
            assert len(row) > 0, "tiling must have at least 1 column"

        return cls(
            saturation=yaml_fragment["saturation"],
            brightness=yaml_fragment["brightness"],
            tiling=tiling,
        )

    def tiles(self, width, height):
        y_count = len(self.tiling)
        for y_index, y_tile in enumerate(self.tiling):

            x_count = len(y_tile)
            for x_index, tile_strength in enumerate(y_tile):

                # Doing multiplication before devision here to make sure rounding is correct
                bounding_box = (
                    # from (x1, y1)
                    int(width * x_index / x_count),
                    int(height * y_index / y_count),
                    # to (x2, y2)
                    int(width * (x_index + 1) / x_count),
                    int(height * (y_index + 1) / y_count),
                )

                yield bounding_box, tile_strength


@attr.s(auto_attribs=True)
class SpriteCategory:
    """Describe a category of sprite, and the associated treatment."""

    source: Path
    mods: Set[str]
    treatment: SpriteTreatment
    patterns: List[Path]
    excludes: List[str]

    @classmethod
    def from_yaml(cls, yaml_path: Path, source_dirs: List[Path]):
        """Read the sprite category to do from a yaml fragment."""
        definition = SAFE_PARSER.load(yaml_path)
        treatment = SpriteTreatment.from_yaml(definition.pop("treatment"))
        excludes = definition.pop("excludes", [])

        patterns = []

        def parse_mod_patterns(path, node):
            if node is None:
                return [path / "**" / "*.png"]

            if isinstance(node, list):
                return itertools.chain(
                    *(parse_mod_patterns(path, sub_node) for sub_node in node)
                )

            if not isinstance(node, dict):
                return [path / "**" / f"*{node}*.png"]

            return itertools.chain(
                *(
                    parse_mod_patterns(path / key, sub_node)
                    for key, sub_node in node.items()
                )
            )

        for mod, first_node in definition.items():
            for mod_root in source_dirs:
                mod_path = mod_root / mod

                # TODO: Mod could have version number, and/or be a zip file
                if mod_path.exists():
                    break
            else:
                raise Exception("Failed to find code for mod: %s" % mod)

            mod_patterns = [
                (mod_path, mod, p.relative_to(mod_path))
                for p in parse_mod_patterns(mod_path, first_node)
            ]
            patterns.extend(mod_patterns)

        return cls(
            source=yaml_path,
            mods=set(definition.keys()),
            treatment=treatment,
            patterns=patterns,
            excludes=excludes,
        )

    def sprite_paths(self):
        """Yield all sprite paths matching this category."""

        yield from (
            (sprite_path, Path(mod) / sprite_path.relative_to(mod_path))
            # For each graphic directory we want recursively all png file
            for mod_path, mod, pattern in self.patterns
            for sprite_path in mod_path.glob(pattern.as_posix())
            # But they should not match any of the excludes
            if all(
                exclude not in sprite_path.relative_to(mod_path).as_posix()
                for exclude in self.excludes
            )
        )
