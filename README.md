# tilelayer_finder

Tilelayer_finder is for finding tilelayers/group layers available via the NLS tileserver and creating `metadata.json` files for them (for use in MapReader).

## Installation (Poetry)

`git clone https://github.com/rwood-97/tilelayer_finder.git`
`cd tilelayer_finder`
`poetry install`
`poetry shell`

## Usage

### CLI

``` python
usage: tlf_run [-h] [-c] [-ot TILES_OUTPUT] [-og GROUPS_OUTPUT] [-n [NAME ...]]

options:
  -h, --help            show this help message and exit
  -c, --clean           Whether to clean data
  -ot TILES_OUTPUT, --tiles-output TILES_OUTPUT
                        Name to use when saving output tilelayer file
  -og GROUPS_OUTPUT, --groups-output GROUPS_OUTPUT
                        Name to use when saving output group layer file
  -n [NAME ...], --name [NAME ...]
                        Name(s) of tilelayer(s)/group layer(s) to create metadata for
```

### Interactive (notebooks)

``` python
from tilelayer_finder import finder

tlf = finder.TileLayerFinder()
tlf.get_data(clean=True)
```

``` python
tlf.list_tilelayers()
tlf.list_group_layers()
```

``` python
tlf.save_data()
```

``` python
tlf.create_metadata_json("oneinch2nd")
```
