"""A sprite category described in a YAML file."""
from pathlib import Path
from typing import Dict, List, Union

import attr
from ruamel.yaml import YAML

SAFE_PARSER = YAML(typ="safe")


@attr.s(auto_attribs=True)
class SpriteTreatment:
    """Describe the treatment to execute on a given sprite."""

    saturation: float = attr.ib(converter=attr.converters.default_if_none(0.1))
    brightness: float = attr.ib(converter=attr.converters.default_if_none(0.7))

    @classmethod
    def from_yaml(cls, yaml_fragment: Dict[str, float]):
        """Read the sprite treatment to do from a yaml fragment."""
        return cls(
            saturation=yaml_fragment.get("saturation"),
            brightness=yaml_fragment.get("brightness"),
        )


@attr.s(auto_attribs=True)
class SpriteCategory:
    """Describe a category of sprite, and the associated treatment."""

    mod: str
    treatment: SpriteTreatment
    graphics: List[str]
    excludes: List[str] = attr.ib(
        converter=attr.converters.default_if_none(factory=list)
    )

    @classmethod
    def from_yaml(cls, yaml_path: Path):
        """Read the sprite category to do from a yaml fragment."""
        definition = SAFE_PARSER.load(yaml_path)
        return cls(
            mod=definition["mod"],
            treatment=SpriteTreatment.from_yaml(definition.get("treatment", {})),
            graphics=definition["graphics"],
            excludes=definition.get("excludes"),
        )

    def sprite_paths(self, root_dir):
        """Yield all sprite paths matching this category."""
        graphics_dir = root_dir / "data" / self.mod / "graphics"
        yield from (
            sprite_path
            # For each graphic directory we want recursively all png file
            for graphic in self.graphics
            for sprite_path in graphics_dir.glob(str(Path(graphic) / "**" / "*.png"))
            # But they should not match any of the excludes
            if all(exclude not in str(sprite_path) for exclude in self.excludes)
        )
