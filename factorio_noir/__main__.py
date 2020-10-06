"""CLI interface for generating Factorio-Noir sprites.

Notes:
- On masOS --factorio-data should be /Applications/factorio.app/Contents/data
"""
import json
import pprint
import shutil
import sys
import tempfile
from pathlib import Path

import click

from factorio_noir.category import SpriteCategory
from factorio_noir.render import process_sprite
from factorio_noir.worker import sprite_processor

MOD_ROOT = Path(__file__).parent.parent.resolve()

VANILLA_MODS = {"core", "base"}


@click.command()
@click.option("--pack-version", default="0.0.1")
@click.option("--dev", is_flag=True, envvar="DEV")
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
def cli(pack_dir, dev, pack_version, factorio_data):
    is_vanilla = Path(pack_dir).name.lower() == "vanilla"

    pack_name = "factorio-noir"
    if not is_vanilla:
        pack_name += f"-{Path(pack_dir).name}"

    if dev is True:
        # for JD h4x
        # target_dir = MOD_ROOT / ".." / "mods" / pack_name
        target_dir = MOD_ROOT / "dist" / "dev" / pack_name

        click.secho(
            f"Using dev directory: {target_dir.relative_to(Path.cwd())}", fg="blue"
        )
        if target_dir.exists() and not target_dir.is_dir():
            click.secho("  - Not a directory, deleting it", fg="yellow")
            target_dir.unlink()
        elif target_dir.exists():
            click.secho("  - Emptying directory", fg="yellow")
            for f in target_dir.iterdir():
                if f.is_file():
                    f.unlink()
                else:
                    shutil.rmtree(f)

        target_dir.mkdir(exist_ok=True, parents=True)

    else:
        target_dir = Path(tempfile.mkdtemp()) / f"{pack_name}_{pack_version}"
        target_dir.mkdir(exist_ok=True, parents=True)
        click.echo(f"Created temporary directory: {target_dir}")

    if is_vanilla:
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

    if not is_vanilla:
        raise NotImplementedError(
            "Loading other mods than vanilla is not implemented yet."
        )

    gen_pack_files(
        pack_dir, [Path(factorio_data)], target_dir, pack_name, pack_version, is_vanilla
    )

    if dev is True:
        return

    click.echo("Making ZIP package")
    (MOD_ROOT / "dist").mkdir(parents=True, exist_ok=True)
    archive_name = shutil.make_archive(
        MOD_ROOT / "dist" / f"{pack_name}_{pack_version}",
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


def gen_pack_files(
    pack_dir, source_dirs, target_dir, pack_name, pack_version, is_vanilla
):
    """Generate a Factorio-Noir package from pack directory."""
    click.echo(f"Loading categories for pack: {pack_dir}")
    categories = [
        SpriteCategory.from_yaml(category_file, source_dirs)
        for category_file in Path(pack_dir).glob("**/*.yml")
    ]

    used_mods = {m for c in categories for m in c.mods}
    click.secho(
        f"Loaded {len(categories)} categories using a total of {len(used_mods)} mods.",
        fg="green",
    )

    click.secho("Prepared all mods, now adding info.json and other files.", fg="green")
    updated_assets = set()

    shutil.copy(MOD_ROOT / "data-final-fixes.lua", target_dir)

    if is_vanilla:
        graphics_dir = target_dir / "data" / "core" / "graphics"
        graphics_dir.mkdir(exist_ok=True, parents=True)

        shutil.copy(MOD_ROOT / "background-image.jpg", graphics_dir)
        updated_assets.add("__core__/graphics/background-image.jpg")

    click.echo("Patching the info.json file")
    with (MOD_ROOT / "info.json").open() as file:
        info_file = json.load(file)

    info_file["name"] = pack_name
    info_file["version"] = pack_version
    info_file["dependencies"].extend(VANILLA_MODS ^ used_mods)

    with (target_dir / "info.json").open("w") as file:
        json.dump(info_file, file, indent=4)

    click.echo("Starting to process sprites")
    marked_for_processing = {}
    with sprite_processor(process_sprite) as submit:
        with click.progressbar(categories, label="Make sprites tasks") as progress:
            for category in progress:
                for (
                    absolute_sprite_path,
                    relative_sprite_path,
                ) in category.sprite_paths():
                    if absolute_sprite_path in marked_for_processing:
                        click.echo()
                        click.secho(
                            f"The sprite {absolute_sprite_path} was included in processing "
                            f"from more than one category: ",
                            fg="red",
                        )
                        pprint.pprint(
                            category,
                            stream=sys.stderr,
                        )
                        pprint.pprint(
                            marked_for_processing[absolute_sprite_path],
                            stream=sys.stderr,
                        )
                        raise click.Abort()
                    marked_for_processing[absolute_sprite_path] = category

                    # TODO: support streaming to/from a zip file
                    submit(
                        source_path=absolute_sprite_path,
                        target_path=target_dir / "data" / relative_sprite_path,
                        treatment=category.treatment,
                    )

                    # Always use '/' seperator for lua paths
                    updated_assets.add(
                        "__%s__/%s"
                        % (
                            relative_sprite_path.parts[0],
                            "/".join(relative_sprite_path.parts[1:]),
                        )
                    )

    # inform lua which files need to be replaced
    with (target_dir / "config.lua").open("w") as file:
        file.write(
            """
return {
    is_vanilla = %s,
    resource_pack_name = "%s",
    updated_assets = {
"""
            % (str(is_vanilla).lower(), pack_name)
        )

        for asset in sorted(updated_assets):
            file.write('["%s"]=1,\n' % asset)

        file.write("    },\n")
        file.write("}\n")


if __name__ == "__main__":
    cli()
