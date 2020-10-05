#!/usr/bin/env python3

from PIL import Image, ImageEnhance
from pathlib import Path
from concurrent.futures import FIRST_EXCEPTION, ProcessPoolExecutor, wait
import os
import shutil
import time

ORIGINAL_GRAPHICS_PATH = Path("originals")

NUM_PROCESSES = os.cpu_count()

MISC_STUFF = [
    "base/graphics/item-group",
    "base/graphics/technology",
    "base/graphics/equipment",
    "base/graphics/achievement",
    "base/graphics/icons",
]

BASE_ENTITIES = [
    "base/graphics/entity/accumulator",
    "base/graphics/entity/beacon",
    "base/graphics/entity/big-electric-pole",
    "base/graphics/entity/boiler",
    "base/graphics/entity/burner-inserter",
    "base/graphics/entity/burner-mining-drill",
    "base/graphics/entity/car",
    "base/graphics/entity/cargo-wagon",
    "base/graphics/entity/centrifuge",
    "base/graphics/entity/chemical-plant",
    "base/graphics/entity/circuit-connector",
    "base/graphics/entity/combinator",
    "base/graphics/entity/compilatron",
    "base/graphics/entity/compilatron-chest",
    "base/graphics/entity/curved-rail",
    "base/graphics/entity/diesel-locomotive",
    "base/graphics/entity/electric-furnace",
    "base/graphics/entity/electric-mining-drill",
    "base/graphics/entity/flamethrower-turret",
    "base/graphics/entity/fluid-wagon",
    "base/graphics/entity/gate",
    "base/graphics/entity/gun-turret",
    "base/graphics/entity/heat-exchanger",
    "base/graphics/entity/heat-pipe",
    "base/graphics/entity/infinity-chest",
    "base/graphics/entity/iron-chest",
    "base/graphics/entity/lab",
    "base/graphics/entity/land-mine",
    "base/graphics/entity/laser-turret",
    "base/graphics/entity/loader",
    "base/graphics/entity/market",
    "base/graphics/entity/medium-electric-pole",
    "base/graphics/entity/nuclear-reactor",
    "base/graphics/entity/offshore-pump",
    "base/graphics/entity/oil-refinery",
    "base/graphics/entity/pipe",
    "base/graphics/entity/pipe-covers",
    "base/graphics/entity/pipe-to-ground",
    "base/graphics/entity/power-switch",
    "base/graphics/entity/programmable-speaker",
    "base/graphics/entity/pump",
    "base/graphics/entity/pumpjack",
    "base/graphics/entity/radar",
    "base/graphics/entity/rail-chain-signal",
    "base/graphics/entity/rail-endings",
    "base/graphics/entity/rail-signal",
    "base/graphics/entity/remnants",
    "base/graphics/entity/roboport",
    "base/graphics/entity/rocket-silo",
    "base/graphics/entity/small-electric-pole",
    "base/graphics/entity/small-lamp",
    "base/graphics/entity/solar-panel",
    "base/graphics/entity/spidertron",
    "base/graphics/entity/steam-engine",
    "base/graphics/entity/steam-turbine",
    "base/graphics/entity/steel-chest",
    "base/graphics/entity/steel-furnace",
    "base/graphics/entity/stone-furnace",
    "base/graphics/entity/storage-tank",
    "base/graphics/entity/straight-rail",
    "base/graphics/entity/substation",
    "base/graphics/entity/tank",
    "base/graphics/entity/train-stop",
    "base/graphics/entity/tree",
    "base/graphics/entity/wall",
    "base/graphics/entity/wooden-chest",
]

BRIGHT_ENTITIES = [
    "base/graphics/entity/assembling-machine-1",
    "base/graphics/entity/assembling-machine-2",
    "base/graphics/entity/assembling-machine-3",
    "base/graphics/entity/burner-inserter",
    "base/graphics/entity/inserter",
    "base/graphics/entity/long-handed-inserter",
    "base/graphics/entity/fast-inserter",
    "base/graphics/entity/filter-inserter",
    "base/graphics/entity/stack-inserter",
    "base/graphics/entity/stack-filter-inserter",
    "base/graphics/entity/express-splitter",
    "base/graphics/entity/express-transport-belt",
    "base/graphics/entity/express-underground-belt",
    "base/graphics/entity/fast-splitter",
    "base/graphics/entity/fast-transport-belt",
    "base/graphics/entity/fast-underground-belt",
    "base/graphics/entity/splitter",
    "base/graphics/entity/transport-belt",
    "base/graphics/entity/underground-belt",
    "base/graphics/entity/logistic-chest",
]

ENTITY_EXCLUDE = [
    "shadow",
    "glow",
    "heater",
    "heated",
    "light",
    "fire",
    "flame",
    "mask",
    "green",
    "liquid",
    "foam",
    "fluid-flow",
    "diode-red",
    "laser-body",
    "charge",
    "signal.png",
]

TERRAIN = [
    "base/graphics/terrain",
    "base/graphics/entity/artillery-turret",
    "base/graphics/entity/artillery-wagon",
]

TERRAIN_EXCLUDE = [
    "cliff",
    "hazard",
    # "artillery-turret-base",
    # "artillery-wagon-base",
]

ORE = [
    "base/graphics/entity/copper-ore",
    "base/graphics/entity/iron-ore",
    "base/graphics/entity/stone",
    "base/graphics/entity/coal",
    "base/graphics/entity/uranium-ore",
]

ORE_EXCLUDE = ["glow"]

CORE = ["core/graphics"]

CORE_EXCLUDE = [
    "green-wire",
    "red-wire",
]


def generate_filenames(dirs, exclude=[]):
    for dir in dirs:
        for path in Path().glob(str(ORIGINAL_GRAPHICS_PATH / dir / "**" / "*.png")):
            if should_exclude(path, exclude):
                continue
            yield path


def should_exclude(path, exclude):
    for exclude_path_part in exclude:
        if exclude_path_part in path.name:
            return True
    return False


def render_image(path, brightness, saturation):
    replace = Path("data", *path.parts[1:])

    os.makedirs(replace.parent, exist_ok=True)

    img_orig = Image.open(path).convert("RGBA")

    img_alpha = img_orig.getchannel("A")
    img_rgb = img_orig.convert("RGB")

    # Numbers taken from factorio's shader. Keep in sync with data-final-fixes.lua
    color_space = (
        0.3086 + 0.6914*saturation, 0.6094 - 0.6094*saturation, 0.0820 - 0.0820*saturation, 0,
        0.3086 - 0.3086*saturation, 0.6094 + 0.3906*saturation, 0.0820 - 0.0820*saturation, 0,
        0.3086 - 0.3086*saturation, 0.6094 - 0.6094*saturation, 0.0820 + 0.9180*saturation, 0,
    )
    color_space = list(c*brightness for c in color_space)

    img_converted = img_rgb.convert("RGB", color_space)
    img_converted.putalpha(img_alpha)

    print(path, "->", replace)
    img_converted.save(replace)


def main():
    start = time.perf_counter()

    processor = ProcessPoolExecutor(NUM_PROCESSES)
    futures = []

    def render(*args):
        futures.append(processor.submit(render_image, *args))

    for filename in generate_filenames(CORE, CORE_EXCLUDE):
        render(filename, 0.7, 0.1)

    # Misc STuff
    for filename in generate_filenames(MISC_STUFF):
        render(filename, 0.6, 0.05)

    # Base Entities
    for filename in generate_filenames(BASE_ENTITIES, ENTITY_EXCLUDE):
        render(filename, 0.7, 0.05)

    # Entites that need more color
    for filename in generate_filenames(BRIGHT_ENTITIES, ENTITY_EXCLUDE):
        render(filename, 0.7, 0.10)

    # Terrain
    for filename in generate_filenames(TERRAIN, TERRAIN_EXCLUDE):
        render(filename, 1, 0.4)

    # Ore
    for filename in generate_filenames(ORE, ORE_EXCLUDE):
        render(filename, 0.7, 0.2)

    # Wait for the all tasks to complete or the first one to raise an exception
    result = wait(futures, return_when=FIRST_EXCEPTION)

    # Cancel pending tasks after one failed with an exception
    for pending in result.not_done:
        pending.cancel()

    # Wait for processor to complete all pending tasks that could not be canceled.
    processor.shutdown()

    # Retrieve result for all tasks, this will re-raise the exception if the
    # task failed and cause it to be printed to the console
    for done in result.done:
        done.result()

    print(f"Done in {time.perf_counter() - start:.1f}s")


if __name__ == "__main__":
    main()
