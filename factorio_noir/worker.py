"""Process all sprites for all the given categories."""
import time
from concurrent.futures import FIRST_EXCEPTION, ProcessPoolExecutor, wait
from contextlib import contextmanager

import click

from typing import Any, Callable, Iterable, Iterator


@contextmanager
def sprite_processor(func: Callable[..., Any]) -> Iterator[Callable[..., Any]]:
    """Create a processor for sprites using the given function."""
    start_time = time.perf_counter()
    processor, futures = ProcessPoolExecutor(), []

    def submit(*args: Any, **kwargs: Any) -> None:
        future = processor.submit(func, *args, **kwargs)
        futures.append(future)

    try:
        yield submit

        with click.progressbar(futures, label="Processing sprites") as progress:
            for future in progress:
                future.result()

    except Exception as e:
        # Enter in error management
        click.secho(f"Got an error, cancelling all: {e}")
        for future in futures:
            if not future.done():
                future.cancel()
        raise e

    finally:
        processor.shutdown()

    click.secho(
        f"Processed {len(futures)} sprites in "
        f"{time.perf_counter() - start_time:.1f}s",
        fg="green",
    )
