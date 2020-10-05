# Factorio Noir

## Requirements

Requirements are handled via (Pipenv)[https://pipenv.pypa.io], getting the
requirements is as easy as doing:

```bash
pipenv install
```

## How to use

```bash
pipenv run python -m factorio_noir --factorio-data <FACTORIO_DATA_DIR> packs/Vanilla
```

Notes:
- If a environment variable `FACTORIO_DATA` is present, the `--factorio-data`
  flag is not needed

