import requests
import re
import pandas as pd
from owslib.wfs import WebFeatureService
from typing import Optional

class TileServerFinder:
    """For finding tileservers available from the NLS."""
    
    def __init__(self):
        """For finding tileservers available from the NLS."""
        self.get_wfs()
        self.queries = {}

    def get_data(self, clean: Optional[bool] = True):
        """Gets the data and saves to `self.data`.

        Parameters
        -----------
        clean : bool, optional
            Whether to clean up dataframe by removing duplicate and unavailable layers.
        """

        self._find_current_file()
        self._generate_layers_dict()
        self._extract_data(clean=clean)

    def _find_current_file(self):
        """Find the url of the current live .js file and save to `self.current_file`.
        """
        with requests.get('https://maps.nls.uk/geo/version') as response:
            current_file = re.findall(r"(?<=Current live file:\s<a\shref=\")(.*)(?=\")", response.text)[0]
            print(f"[INFO] Current file is: '{current_file}'")
            self.current_file = current_file
            
    def _generate_layers_dict(self):
        """Generate a dictionary containing available tilelayers and save to `self.layers_dict`. 
        Keys are tilelayer names.
        """
        current_file = self.current_file
        
        with requests.get(current_file) as response:
            layers = re.findall(r"(?<=overlayLayers =  \[)(.*)(?=\])", response.text)[0]
            layers_list = re.split(r",\s*", layers)
            all_layers_dict = {layer:re.findall(fr"(?<=var\s{layer}\b)\s+=\s+(.*?)(?=\);)", response.text, re.DOTALL)[0] for layer in layers_list}

        tile_layers_dict = {k:v for k, v in all_layers_dict.items() 
                            if re.search(r"new\s*ol.layer.Tile\(", v)}
        
        for k, v in tile_layers_dict.items():
            tile_layers_dict[k]=re.sub(r"\n//.*", "", v)
            
        self.layers_dict = tile_layers_dict
        
    def _extract_data(self, clean: Optional[bool] = True):
        """Extract data (name, title, typename, XYZ url and maxZ) from `self.layers_dict` and save to `self.data`. 

        Parameters
        -----------
        clean : bool, optional
            Whether to clean up dataframe by removing duplicate and unavailable layers.
        """
        data_dict={}
        for k, v in self.layers_dict.items():
            title = re.findall(r"(?<=title:)\s*[\"|\'](.*)(?=[\"|\'],)", v)
            sourceXYZ = re.findall(r"(?<=source:)\s*new\sol.source.XYZ\(\{(.*)(?=\}\),)", v, re.DOTALL)
            if len(sourceXYZ)>0:
                XYZ = re.findall(r"(?<=url:)\s*[\"|\'](.*[png|jpg])(?=[\"|\'],)", sourceXYZ[0])
                maxZ = re.findall(r"(?<=maxZ:)\s*(\d+)", sourceXYZ[0])
                if len(maxZ)==0:
                    maxZ = re.findall(r"(?<=maxZ:)\s*(\d+)", v)
                typename = re.findall(r"(?<=typename:)\s*[\"|\'](.*)(?=[\"|\'],)", v)
                data_dict[k] = [value[0] if len(value)!=0 else None for value in [title, typename, XYZ, maxZ]]
                
        data = pd.DataFrame.from_dict(data_dict, orient="index", columns=["Title", "Typename", "XYZ URL", "Max Z"])
        
        if clean:
            # remove 'nls:WFS' as these tend to be single maps rather than layers
            data = data[data["Typename"] != "nls:WFS"]
            # ensure typename is available on WFS
            for i, typename in data["Typename"].items():
                if typename not in list(self.wfs.contents):
                    data.drop(i, inplace=True)
        
        data.reset_index(inplace=True, names="Name")
        print(f"[INFO] Dataframe has {len(data)} values.")
        self.data = data

    def save_data(self, fname : Optional[str] = "./NLS_tilelayers.csv"):
        """Save extracted data (`self.data`) to csv file.

        Parameters
        ----------
        fname : str, optional
            The name to use when saving the file (should end in ".csv").
            By default, "./NLS_tilelayers.csv"
        """

        if not fname.endswith(".csv"):
            fname = f"{fname}.csv"
        print(f"[INFO] Saving data to '{fname}'.")
        self.data.to_csv(fname)

    def load_data(
            self, 
            file_path: str,
            ):
        """Loads a csv file containing the data (name, title, typename, XYZ url and maxZ).

        Parameters
        ----------
        file_path : str
            The path to file to load.
        
        Notes
        -----
        The NLS periodically updates the .js file used to generate this data.
        If your data is over a few months old, it may be worth re-creating your csv file using the ``.get_data()`` method.
        """
        
        data = pd.read_csv(file_path, index_col=0)
        self.data = data

    def list_tilelayers(self):
        """Print the names and titles of available tilelayers.
        """
        tilelayers = list(self.data["Name"])
        print(*tilelayers, sep="\n")

    def create_metadata_json(
        self,
        name: str,
        bbox: Optional[tuple] = None,
        srsname: Optional[str] = "urn:x-ogc:def:crs:EPSG:4326",
    ):
        """Create a .json file containing the metadata for the named tilelayer.

        Parameters
        ----------
        name : str
            The name of the tilelayer whose metadata is to be downloaded.
        bbox : Optional[tuple], optional
            The bounding box in the form (minx, miny, maxx, maxy, "EPSG:XXX").
            If None, the bounding box will be looked up for the chosen tilelayer.
            By default, None.
        srsname : Optional[str], optional
            The spatial reference system (EPSG code) to request the data in. 
            By default, "urn:x-ogc:def:crs:EPSG:4326".
        """
        typename = self.data[self.data["Name"]==name]['Typename'].item()
        print(f"[INFO] Getting metadata for {name} (typename: '{typename}')")
        XYZ = self.data[self.data["Name"]==name]['XYZ URL'].item()
        print(f"[INFO] XYZ URL for this layer is: '{XYZ}'")
        maxZ = self.data[self.data["Name"]==name]['Max Z'].item()
        print(f"[INFO] Max zoom level for this layer is: {maxZ}")

        try:
            self.wfs.contents[typename]
        except KeyError:
            raise KeyError("[ERROR] The metadata for this tilelayer is unavailable.")
        
        if not bbox:
            try:
                bbox_wgs84 = self.wfs.contents[typename].boundingBoxWGS84 + ("EPSG:4326",)
            except AttributeError:
                (-9.26,49.77,2.73,60.97, "EPSG:4326")
        wfs_feature = self.wfs.getfeature(
            typename=typename,
            bbox=bbox_wgs84,
            outputFormat="json",
            srsname=srsname)
        
        self.queries[name] = wfs_feature

        print(f"[INFO] Writing to file: './{name}.json'")
        with open(f"{name}.json", "wb") as f:
            f.write(wfs_feature.getbuffer())
        
    def get_wfs(
        self, 
        url: Optional[str] = 'https://geoserver.nls.uk/geoserver/wfs', 
        version: Optional[str] ='1.1.0'
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