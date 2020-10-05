"""CLI interface for generating Factorio-Noir sprites.

Notes:
- On masOS --factorio-data should be /Applications/factorio.app/Contents/data
"""
import tempfile
from pathlib import Path

import click
from click import Argument

from factorio_noir.category import SpriteCategory


@click.command()
@click.option("--pack-version", default="0.0.1")
@click.option(
    "--factorio-data",
    type=click.Path(exists=True, dir_okay=True, file_okay=False, readable=True),
    help="Factorio install directory, needed only if packaging Vanilla pack.",
    envvar="FACTORIO_DATA",
)
@click.argument(
    "pack-dir",
    type=click.Path(exists=True, dir_okay=True, file_okay=False, readable=True),
)
def cli(pack_dir, pack_version, factorio_data):
    """Generate a Factorio-Noir package from pack directory."""
    click.echo(f"Loading categories for pack: {pack_dir}")
    categories = [
        SpriteCategory.from_yaml(category_file)
        for category_file in Path(pack_dir).glob("**/*.yml")
    ]

    used_mods = {c.mod for c in categories}
    click.secho(
        f"Loaded {len(categories)} categories using a total of {len(used_mods)} mods.",
        fg="green",
    )


if __name__ == "__main__":
    cli()
