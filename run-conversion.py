#!/usr/bin/env python3

import os
import shutil
import time
from concurrent.futures import FIRST_EXCEPTION, ProcessPoolExecutor, wait
from pathlib import Path

from PIL import Image, ImageEnhance

ORIGINAL_GRAPHICS_PATH = Path("originals")

NUM_PROCESSES = os.cpu_count()


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

    # TODO: move to factorio_noir module once
    from factorio_noir.render import apply_transforms

    img_converted = apply_transforms(img_orig)

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
        render(filename, 0.5, 0.6)

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
