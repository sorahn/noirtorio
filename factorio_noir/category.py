"""A sprite category described in a YAML file."""
from fnmatch import fnmatch
import itertools
import pprint
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set, Tuple, Union, Optional

import attr
import click
from attr import converters
from ruamel.yaml import YAML  # type: ignore

from factorio_noir.mod import Mod, LazyFile, open_mod_read

SAFE_PARSER = YAML(typ="safe")


def _float_or_percent(val: Union[float, str]) -> float:
    """Parse a percent string (XX%) to float if possible."""
    if isinstance(val, float):
        return val

    if not isinstance(val, str) or not val.endswith("%"):
        raise ValueError(f"{val} is neither a float of a percent value")

    return float(val[:-1]) / 100


def _validate_tiling(inst: Any, attr: Any, value: List[List[float]]) -> None:
    """Ensure tiling is valid."""
    if len(value) == 0:
        raise ValueError("Tiling must have at least 1 row")

    if any(len(t) == 0 for t in value):
        raise ValueError("Tiling must have at least 1 column")

    if min(len(t) for t in value) != max(len(t) for t in value):
        raise ValueError("Tiling must have the same number of column for each row.")


def _parse_tiling(value: Optional[List[str]]) -> List[List[float]]:
    # Tiling is read as a list of strings to make it be layed out graphically

    if value is None:
        return [[1.0]]
    else:
        return [[float(t) for t in row.split()] for row in value]


TileSet = Iterable[Tuple[Tuple[int, int, int, int], float]]


@attr.s(auto_attribs=True)
class SpriteTreatment:
    """Describe the treatment to execute on a given sprite."""

    saturation: float = attr.ib(converter=_float_or_percent)
    brightness: float = attr.ib(converter=_float_or_percent)
    tiling: List[List[float]] = attr.ib(
        converter=_parse_tiling,
        validator=_validate_tiling,
    )

    @classmethod
    def from_yaml(cls, yaml_fragment: Dict[str, Any]) -> "SpriteTreatment":
        """Read the sprite treatment to do from a yaml fragment."""
        return cls(
            saturation=yaml_fragment["saturation"],
            brightness=yaml_fragment["brightness"],
            tiling=yaml_fragment.get("tiling"),
        )

    def tiles(self, width: int, height: int) -> TileSet:
        """Yield each tile in the sprite, with the given strength to apply."""
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
    source_dirs: List[Path]
    mods: Set[str]
    treatment: SpriteTreatment
    patterns: List[Tuple[Mod, Path]]
    excludes: List[str]
    includes: List[str]
    replaces: Dict[str, str]
    copy_files: Dict[str, Path]

    @classmethod
    def from_yaml(cls, yaml_path: Path, source_dirs: List[Path]) -> "SpriteCategory":
        """Read the sprite category to do from a yaml fragment."""
        definition = SAFE_PARSER.load(yaml_path)
        try:
            treatment = SpriteTreatment.from_yaml(definition.pop("treatment"))
        except ValueError as e:
            click.secho(f"Invalid value for treatment in {yaml_path}:", fg="red")
            click.secho(f"  - {e}", fg="red")
            raise click.Abort()
        except KeyError as e:
            click.secho(f"Missing key {e} in treatment of {yaml_path}", fg="red")
            raise click.Abort()

        excludes = definition.pop("excludes", [])
        includes = definition.pop("includes", [])
        replaces = definition.pop("replaces", {})
        copy_files = {
            k: yaml_path.parent / v for k, v in definition.pop("copy_files", {}).items()
        }

        patterns: List[Tuple[Mod, Path]] = []

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
            mod = open_mod_read(mod_name, source_dirs)

            mod_patterns = [(mod, p) for p in parse_mod_patterns(Path("."), first_node)]
            patterns.extend(mod_patterns)

        return cls(
            source=yaml_path,
            source_dirs=source_dirs,
            mods=set(definition.keys()),
            treatment=treatment,
            patterns=patterns,
            excludes=excludes,
            includes=includes,
            replaces=replaces,
            copy_files=copy_files,
        )

    def sprite_files(self) -> Iterable[Tuple[LazyFile, Optional[LazyFile], str]]:
        """Yield all sprite paths matching this category."""

        missed_patterns = []

        # For each graphic directory we want recursively all png file
        for mod, pattern in self.patterns:
            pattern_used = False

            for sprite_path in mod.files(pattern):
                # But they should not match any of the excludes
                if any(
                    fnmatch(sprite_path, f"*{exclude}*") for exclude in self.excludes
                ):
                    continue

                if len(self.includes) > 0:
                    # They must contain an includes
                    if all(
                        not fnmatch(sprite_path, f"*{include}*")
                        for include in self.includes
                    ):
                        continue

                full_sprite_path = f"__{mod.name}__/{sprite_path}"

                replaced_mod, replaced_sprite_path = self.replace_path(full_sprite_path)

                pattern_used = True

                lazy_match_size_file = None
                if replaced_mod != mod or replaced_sprite_path != sprite_path:
                    lazy_match_size_file = mod.lazy_file(sprite_path)

                yield (
                    replaced_mod.lazy_file(replaced_sprite_path),
                    lazy_match_size_file,
                    full_sprite_path,
                )

            if not pattern_used:
                missed_patterns.append(f"__{mod.name}__/{pattern}")

        if len(missed_patterns) > 0:
            click.secho(
                f"Warning: Resources with no match in file {self.source}:\n    "
                + "\n    ".join(missed_patterns),
                fg="yellow",
            )

    def replace_path(self, full_sprite_path: str) -> Tuple[Mod, str]:
        new_path = full_sprite_path
        for find, replace in self.replaces.items():
            new_path = new_path.replace(find, replace)

        new_mod_name, new_sprite_path = new_path.split("/", 1)

        # remove '__' srounding the mod name
        assert new_mod_name[:2] == "__" and new_mod_name[-2:] == "__"
        new_mod_name = new_mod_name[2:-2]

        return open_mod_read(new_mod_name, self.source_dirs), new_sprite_path
