"""A sprite category described in a YAML file."""
import itertools
from pathlib import Path
from typing import Dict, List, Set, Any, Tuple, Iterable, Union

import attr
from ruamel.yaml import YAML  # type: ignore

from factorio_noir.mod import open_mod_read, Mod

SAFE_PARSER = YAML(typ="safe")


@attr.s(auto_attribs=True)
class SpriteTreatment:
    """Describe the treatment to execute on a given sprite."""

    saturation: float
    brightness: float
    tiling: List[List[float]]

    @classmethod
    def from_yaml(cls, yaml_fragment: Dict[str, Any]) -> "SpriteTreatment":
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

    def tiles(
        self, width: int, height: int
    ) -> Iterable[Tuple[Tuple[int, int, int, int], float]]:
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
    patterns: List[Tuple[Mod, Path]]
    excludes: List[str]

    @classmethod
    def from_yaml(cls, yaml_path: Path, source_dirs: List[Path]) -> "SpriteCategory":
        """Read the sprite category to do from a yaml fragment."""
        definition = SAFE_PARSER.load(yaml_path)
        treatment = SpriteTreatment.from_yaml(definition.pop("treatment"))
        excludes = definition.pop("excludes", [])

        patterns: List[Tuple[Mod, Path]] = []
        mod_cache = {}

        def parse_mod_patterns(path: Path, node: Any) -> Iterable[Path]:
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

        for mod_name, first_node in definition.items():
            if mod_name not in mod_cache:
                mod_cache[mod_name] = open_mod_read(mod_name, source_dirs)

            mod = mod_cache[mod_name]

            mod_patterns = [(mod, p) for p in parse_mod_patterns(Path("."), first_node)]
            patterns.extend(mod_patterns)

        return cls(
            source=yaml_path,
            mods=set(definition.keys()),
            treatment=treatment,
            patterns=patterns,
            excludes=excludes,
        )

    def sprite_paths(self) -> Iterable[Tuple[Mod, str]]:
        """Yield all sprite paths matching this category."""

        yield from (
            (mod, sprite_path)
            # For each graphic directory we want recursively all png file
            for mod, pattern in self.patterns
            for sprite_path in mod.files(pattern)
            # But they should not match any of the excludes
            if all(exclude not in sprite_path for exclude in self.excludes)
        )
