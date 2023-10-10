import re

import pandas as pd
import requests
from owslib.wfs import WebFeatureService


class TileServerFinder:
    """For finding tileservers available from the NLS."""

    def __init__(self):
        """For finding tileservers available from the NLS."""
        self.get_wfs()
        self.queries = {}

    def get_data(self, clean: bool | None = True):
        """Gets the data and saves to `self.tile_data`.

        Parameters
        -----------
        clean : bool, optional
            Whether to clean up dataframe by removing duplicate and unavailable layers.
        """

        self._find_current_file()
        self._generate_layers_dicts()
        self._extract_data(clean=clean)

    def _find_current_file(self):
        """Find the url of the current live .js file and save to `self.current_file`."""
        with requests.get("https://maps.nls.uk/geo/version") as response:
            current_file = re.findall(
                r"(?<=Current live file:\s<a\shref=\")(.*)(?=\")", response.text
            )[0]
            print(f"[INFO] Current file is: '{current_file}'")
            self.current_file = current_file

    def _generate_layers_dicts(self):
        """Generate a dictionary containing available tilelayers and group layers and save to `self.tilelayers_dict` and `self.group_layers_dict`.
        Keys are tilelayer names.
        """
        current_file = self.current_file

        with requests.get(current_file) as response:
            all_layers = re.findall(r"(?<=var)\s*(.*?)\s*=\s*new", response.text)
            all_layers_dict = {
                layer: re.findall(
                    rf"(?<=var\s{layer}\b)\s+=\s+(.*?)(?=\);)", response.text, re.DOTALL
                )[0]
                for layer in all_layers
            }

        tilelayers_dict = {
            k: v
            for k, v in all_layers_dict.items()
            if re.search(r"new\s*ol.layer.Tile\(", v)
        }

        for k, v in tilelayers_dict.items():
            tilelayers_dict[k] = re.sub(r"\n//.*", "", v)

        self.tilelayers_dict = tilelayers_dict

        group_layers_dict = {
            k: v
            for k, v in all_layers_dict.items()
            if re.search(r"new\s*ol.layer.Group\(", v)
        }

        for k, v in group_layers_dict.items():
            group_layers_dict[k] = re.sub(r"\n//.*", "", v)

        self.group_layers_dict = group_layers_dict

    def _extract_data(self, clean: bool | None = True):
        """Extract data (name, title, typename, XYZ url, maxZ and layers) from layers dicts and save to `self.tile_data` and `self.group_data`.

        Parameters
        -----------
        clean : bool, optional
            Whether to clean up dataframes by removing duplicate and unavailable layers.
        """
        tile_data_dict = {}
        for k, v in self.tilelayers_dict.items():
            title = re.findall(r"(?<=title:)\s*[\"|\'](.*)(?=[\"|\'],)", v)
            source_xyz = re.findall(
                r"(?<=source:)\s*new\sol.source.XYZ\(\{(.*)(?=\}\),)", v, re.DOTALL
            )
            if len(source_xyz) > 0:
                xyz = re.findall(
                    r"(?<=url:)\s*[\"|\'](.*[png|jpg])(?=[\"|\'],)", source_xyz[0]
                )
                max_z = re.findall(r"(?<=maxZ:)\s*(\d+)", source_xyz[0])
                if len(max_z) == 0:
                    max_z = re.findall(r"(?<=maxZ:)\s*(\d+)", v)
                typename = re.findall(r"(?<=typename:)\s*[\"|\'](.*)(?=[\"|\'],)", v)
                tile_data_dict[k] = [
                    value[0] if len(value) != 0 else None
                    for value in [title, typename, xyz, max_z]
                ]

        tile_data = pd.DataFrame.from_dict(
            tile_data_dict,
            orient="index",
            columns=["Title", "Typename", "XYZ URL", "Max Z"],
        )

        group_data_dict = {}
        for k, v in self.group_layers_dict.items():
            title = re.findall(r"(?<=title:)\s*[\"|\'](.*)(?=[\"|\'],)", v)
            typename = re.findall(r"(?<=typename:)\s*[\"|\'](.*)(?=[\"|\'],)", v)
            layers = re.findall(r"(?<=layers:)\s*\[\s*(.*)(?=\s*\],)", v)
            if len(layers) != 0:
                layers = layers[0].split(",")
                layers = [layer.strip() for layer in layers]  # remove whitespace
            group_data_dict[k] = [
                title[0] if len(title) != 0 else None,
                typename[0] if len(typename) != 0 else None,
                layers,
            ]

        group_data = pd.DataFrame.from_dict(
            group_data_dict, orient="index", columns=["Title", "Typename", "Layers"]
        )

        if clean:
            # drop groups with missing layers
            for i, row in group_data.iterrows():
                if any(layer not in list(tile_data.index) for layer in row["Layers"]):
                    group_data.drop(i, inplace=True)

            # remove 'nls:WFS' as these tend to be single maps rather than layers
            tile_data = tile_data[tile_data["Typename"] != "nls:WFS"]
            group_data = group_data[group_data["Typename"] != "nls:WFS"]

            # ensure typename is available on WFS
            for i, typename in tile_data["Typename"].items():
                if typename not in list(self.wfs.contents):
                    self.tile_data.drop(i, inplace=True)
            for i, typename in group_data["Typename"].items():
                if typename not in list(self.wfs.contents):
                    self.group_data.drop(i, inplace=True)

        tile_data.reset_index(inplace=True, names="Name")
        print(f"[INFO] Tile dataframe has {len(tile_data)} values.")
        self.tile_data = tile_data

        group_data.reset_index(inplace=True, names="Name")
        print(f"[INFO] Group dataframe has {len(group_data)} values.")
        self.group_data = group_data

    def save_data(
        self,
        tiles_fname: str | None = "nls_tilelayers.csv",
        groups_fname: str | None = "nls_grouplayers.csv",
    ):
        """Save extracted data (`self.tile_data` and `self.group_data`) to csv file.

        Parameters
        ----------
        tiles_fname : str, optional
            The name to use when saving the file (should end in ".csv").
            By default, "nls_tilelayers.csv"
        groups_fname : str, optional
            The name to use when saving the file (should end in ".csv")
            By default, "nls_grouplayers.csv"
        """

        if not tiles_fname.endswith(".csv"):
            tiles_fname = f"{tiles_fname}.csv"
        print(f"[INFO] Saving tile_data to '{tiles_fname}'.")
        self.tile_data.to_csv(tiles_fname)

        if not groups_fname.endswith(".csv"):
            groups_fname = f"{groups_fname}.csv"
        print(f"[INFO] Saving group_data to '{groups_fname}'.")
        self.group_data.to_csv(groups_fname)

    def load_data(
        self,
        tiles_fname: str | None = "nls_tilelayers.csv",
        groups_fname: str | None = "nls_grouplayers.csv",
    ):
        """Loads csv files containing the tilelayer and group layer data.

        Parameters
        ----------
        tiles_fname : str, optional
            The name of the tilelayer data file.
            By default, "nls_tilelayers.csv"
        groups_fname : str, optional
            The name of the group layer data file.
            By default, "nls_grouplayers.csv"

        Notes
        -----
        The NLS periodically updates the .js file used to generate this data.
        If your data is over a few months old, it may be worth re-creating your csv file using the ``.get_data()`` method.
        """

        tile_data = pd.read_csv(tiles_fname, index_col=0)
        self.tile_data = tile_data

        group_data = pd.read_csv(groups_fname, index_col=0)
        self.group_data = group_data

    def list_tilelayers(self):
        """Print the names and titles of available tilelayers."""
        tilelayers = list(self.tile_data["Name"])
        print(*tilelayers, sep="\n")

    def list_group_layers(self):
        """Print the names and titles of available group layers."""
        group_layers = list(self.group_data["Name"])
        print(*group_layers, sep="\n")

    def create_metadata_json(
        self,
        name: str,
        bbox: tuple | None = None,
        srsname: str | None = "urn:x-ogc:def:crs:EPSG:4326",
    ):
        """Create a .json file containing the metadata for the named tilelayer/group layer.

        Parameters
        ----------
        name : str
            The name of the tilelayer/group layer whose metadata is to be downloaded.
        bbox : Optional[tuple], optional
            The bounding box in the form (minx, miny, maxx, maxy, "EPSG:XXX").
            If None, the bounding box will be looked up for the chosen tilelayer.
            By default, None.
        srsname : Optional[str], optional
            The spatial reference system (EPSG code) to request the data in.
            By default, "urn:x-ogc:def:crs:EPSG:4326".
        """
        if name in list(self.tile_data["Name"]):
            typename = self.tile_data[self.tile_data["Name"] == name]["Typename"].item()
            print(f"[INFO] Getting metadata for {name} (typename: '{typename}')")
            xyz = self.tile_data[self.tile_data["Name"] == name]["XYZ URL"].item()
            print(f"[INFO] XYZ URL for this layer is: '{xyz}'")
            max_z = self.tile_data[self.tile_data["Name"] == name]["Max Z"].item()
            print(f"[INFO] Max zoom level for this layer is: {max_z}")
        elif name in list(self.group_data["Name"]):
            typename = self.group_data[self.group_data["Name"] == name][
                "Typename"
            ].item()
            print(f"[INFO] Getting metadata for {name} (typename: '{typename}')")
        else:
            msg = f'"{name}" not found in data.'
            raise ValueError(msg)

        try:
            self.wfs.contents[typename]
        except KeyError as err:
            msg = "[ERROR] The metadata for this tilelayer is unavailable."
            raise KeyError(msg) from err

        if not bbox:
            try:
                bbox_wgs84 = (
                    *self.wfs.contents[typename].boundingBoxWGS84,
                    "EPSG:4326",
                )
            except AttributeError:
                bbox_wgs84 = (-9.26, 49.77, 2.73, 60.97, "EPSG:4326")
        wfs_feature = self.wfs.getfeature(
            typename=typename, bbox=bbox_wgs84, outputFormat="json", srsname=srsname
        )

        self.queries[name] = wfs_feature

        print(f"[INFO] Writing to file: './{name}.json'")
        with open(f"{name}.json", "wb") as f:
            f.write(wfs_feature.getbuffer())

    def get_wfs(
        self,
        url: str | None = "https://geoserver.nls.uk/geoserver/wfs",
        version: str | None = "1.1.0",
    ):
        """Get the WFS and save to `self.wfs`.

        Parameters
        ----------
        url : Optional[str], optional
            The URL of the WFS, by default 'https://geoserver.nls.uk/geoserver/wfs'
        version : Optional[str], optional
            The version of the WFS to use, by default '1.1.0'
        """
        wfs = WebFeatureService(url, version)
        self.wfs = wfs

    def print_found_queries(self):
        """Print the names of previously queried tilelayers.
        Each of these can be re-accessed using `self.queries["tilelayer_name"]`.
        """
        if len(self.queries) == 0:
            print("[INFO] No queries made so far.")

        else:
            queried_wfs_features = list(self.queries.keys())
            print("[INFO] Queried WFS features:")
            print(queried_wfs_features, sep="\n")
