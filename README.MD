Copy the graphics folders from Factorio:

- `<factorio>/data/base/graphics` -> `originals/base/graphics`
- `<factorio>/data/core/graphics` -> `originals/core/graphics`

run `./do-the-things.sh`

Zip Command
`zip -r factorio-noir.zip . -x '*originals*' -x '*.git*'`
