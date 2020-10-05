"""CLI interface for generating Factorio-Noir sprites.

Notes:
- On masOS --factorio-data should be /Applications/factorio.app/Contents/data
"""
import json
import shutil
import tempfile
from pathlib import Path

import click

from factorio_noir.category import SpriteCategory
from factorio_noir.mods import VANILLA_MODS, prepare_vanilla_mod
from factorio_noir.render import process_sprite
from factorio_noir.worker import sprite_processor

MOD_ROOT = Path(__file__).parent.parent.resolve()
FILES_TO_COPY_VERBATIM = {
    "info.json",
    "config.lua",
    "data-final-fixes.lua",
    "background-image.jpg",
}


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

    if Path(pack_dir).name.lower() == "vanilla":
        pack_name = f"Factorio-Noir"
    else:
        pack_name = f"Factorio-Noir-{Path(pack_dir).name}"

    target_dir = Path(tempfile.mkdtemp()) / f"{pack_name}_{pack_version}"
    target_dir.mkdir(exist_ok=True, parents=True)

    click.echo(f"Created temporary directory: {target_dir}")
    if VANILLA_MODS & used_mods:
        if factorio_data is None:
            click.secho(
                "Missing --factorio-data value, required for editing vanilla graphics.",
                fg="red",
            )
            raise click.Abort

        factorio_data = Path(factorio_data)
        if any(not (factorio_data / mod).exists() for mod in VANILLA_MODS):
            click.secho(
                f"{factorio_data} is not a valid factorio data directory.",
                fg="red",
            )
            raise click.Abort

        for mod in VANILLA_MODS & used_mods:
            click.echo(f"Preparing mod: {mod}")
            prepare_vanilla_mod(factorio_data, mod, target_dir=target_dir)

    if VANILLA_MODS ^ used_mods:
        raise NotImplementedError(
            "Loading other mods than vanilla is not implemented yet."
        )

    click.secho("Prepared all mods, now adding info.json and other files.", fg="green")
    for f in FILES_TO_COPY_VERBATIM:
        shutil.copy(MOD_ROOT / f, target_dir)

    click.echo("Patching the info.json file")
    with (target_dir / "info.json").open() as file:
        info_file = json.load(file)

    info_file["name"] = pack_name
    info_file["version"] = pack_version
    info_file["dependencies"].extend(VANILLA_MODS ^ used_mods)

    with (target_dir / "info.json").open("w") as file:
        json.dump(info_file, file, indent=4)

    click.echo("Starting to process sprites")
    with sprite_processor(process_sprite) as submit:
        with click.progressbar(categories) as progress:
            for category in progress:
                for sprite_path in category.sprite_paths(target_dir):
                    submit(
                        sprite_path=sprite_path,
                        treatment=category.treatment,
                    )

    click.echo("Making ZIP package")
    archive_name = shutil.make_archive(
        MOD_ROOT / f"{pack_name}_{pack_version}",
        format="zip",
        root_dir=target_dir.parent,
        base_dir=target_dir.name,
    )
    click.secho(
        f"Created archive for pack: {Path(archive_name).relative_to(Path.cwd())}",
        fg="green",
    )
    click.secho("Removing temp dir, and cleaning up.", fg="yellow")
    shutil.rmtree(target_dir)


if __name__ == "__main__":
    cli()
