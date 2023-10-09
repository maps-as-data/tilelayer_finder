import tileserver_finder
from argparse import ArgumentParser

parser = ArgumentParser()
parser.add_argument("-c","--clean", action="store_true", help="Whether to clean data")
parser.add_argument("-o","--output", nargs="?", type=str, default="./NLS_tilelayers.csv", const="./NLS_tilelayers.csv", help="Name to use when saving output file")
parser.add_argument("-n","--name", nargs="?", type=str, default="oneinch2nd", const="oneinch2nd", help="Name of tilelayer to create metadata for")
args = parser.parse_args()

# run the code 
TSF = tileserver_finder.TileServerFinder()
TSF.get_data(clean=args.clean)
TSF.save_data(fname=args.output)

# if you wanted to create a json of one of your tilelayers, uncomment the below and pass the "-n" argument to set which tilelayer to create metadata for
# TSF.create_metadata_json(name=args.name)