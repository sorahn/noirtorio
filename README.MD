# Factorio Noir

## Requirements

Requirements are handled via (Pipenv)[https://pipenv.pypa.io], getting the
requirements is as easy as doing:

```bash
pipenv install
```

## How to use

Copy the graphics folders from Factorio:

- `<factorio>/data/base/graphics` -> `originals/base/graphics`
- `<factorio>/data/core/graphics` -> `originals/core/graphics`

run `./do-the-things.sh`

Zip Command
`zip -r factorio-noir.zip . -x '*originals*' -x '*.git*'`
