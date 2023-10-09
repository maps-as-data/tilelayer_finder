from argparse import ArgumentParser

from tileserver_finder import finder

def main():
    # parse arguments
    parser = ArgumentParser()
    parser.add_argument("-c","--clean", action="store_true", help="Whether to clean data")
    parser.add_argument("-o","--output", type=str, default="nls_tilelayers.csv", help="Name to use when saving output file")
    parser.add_argument("-n","--name", nargs="*", type=str, default=[], help="Name of tilelayer to create metadata for")
    args = parser.parse_args()

    # run tileserver_finder
    tsf = finder.TileServerFinder()
    tsf.get_data(clean=args.clean)
    tsf.save_data(fname=args.output)

    # save metadata if any names are passed
    if len(args.name)>0:
        for name in args.name:
            tsf.create_metadata_json(name=name)

if __name__ == "__main__":
    main()