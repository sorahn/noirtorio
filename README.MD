# Factorio Noir

## Requirements

Requirements are handled via [Pipenv](https://pipenv.pypa.io), getting the
requirements is as easy as doing:

```bash
pipenv install
```

## How to use

```bash
pipenv run python -m factorio_noir --factorio-data <FACTORIO_DATA_DIR> packs/Vanilla
```

This will generate a ready archive file in the subdirectory `dist/` that can be
uploaded to the portal.

There is also a `--dev` flag that don't zip the package and instead write
everything to a directory in `dist/`

Notes:
- If a environment variable `FACTORIO_DATA` is present, the `--factorio-data`
  flag is not needed
- Same `DEV=true` enable permanent dev mode
- [Pipenv load `.env` file in `pipenv shell` and `pipenv run`](https://pipenv.pypa.io/en/latest/advanced/#automatic-loading-of-env)
