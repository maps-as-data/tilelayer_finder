from argparse import ArgumentParser

from tilelayer_finder import finder


def main():
    # parse arguments
    parser = ArgumentParser()
    parser.add_argument(
        "-c", "--clean", action="store_true", help="Whether to clean data"
    )
    parser.add_argument(
        "-ot",
        "--tiles-output",
        type=str,
        default="nls_tilelayers.csv",
        help="Name to use when saving output tilelayer file",
    )
    parser.add_argument(
        "-og",
        "--groups-output",
        type=str,
        default="nls_group_layers.csv",
        help="Name to use when saving output group layer file",
    )
    parser.add_argument(
        "-n",
        "--name",
        nargs="*",
        type=str,
        default=[],
        help="Name(s) of tilelayer(s)/group layer(s) to create metadata for",
    )
    args = parser.parse_args()

    # run tilelayer_finder
    tsf = finder.TileLayerFinder()
    tsf.get_data(clean=args.clean)
    tsf.save_data(tiles_fname=args.tiles_output, groups_fname=args.groups_output)

    # save metadata if any names are passed
    if len(args.name) > 0:
        for name in args.name:
            tsf.create_metadata_json(name=name)


if __name__ == "__main__":
    main()
