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

    @classmethod
    def from_yaml(cls, yaml_fragment: Dict[str, float]):
        """Read the sprite treatment to do from a yaml fragment."""
        return cls(
            saturation=yaml_fragment["saturation"],
            brightness=yaml_fragment["brightness"],
        )


@attr.s(auto_attribs=True)
class SpriteCategory:
    """Describe a category of sprite, and the associated treatment."""

    source: Path
    mods: Set[str]
    treatment: SpriteTreatment
    patterns: List[Path]
    excludes: List[str]

    @classmethod
    def from_yaml(cls, yaml_path: Path):
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
            mod_patterns = parse_mod_patterns(Path(mod), first_node)
            patterns.extend(mod_patterns)

        return cls(
            source=yaml_path,
            mods=set(definition.keys()),
            treatment=treatment,
            patterns=patterns,
            excludes=excludes,
        )

    def sprite_paths(self, root_dir):
        """Yield all sprite paths matching this category."""
        yield from (
            sprite_path
            # For each graphic directory we want recursively all png file
            for pattern in self.patterns
            for sprite_path in (root_dir / "data").glob(pattern.as_posix())
            # But they should not match any of the excludes
            if all(
                exclude not in sprite_path.relative_to(root_dir).as_posix()
                for exclude in self.excludes
            )
        )
