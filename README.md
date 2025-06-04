# forge-py

The Footprint Generator project provides tools for generating geographic footprints from various data sources. This tool supports different generation strategies applicable to variable geometry types. Requires parameters for `forge-py` to be saved in a configuration file (see below), and data files saved in either netCDF and HDF format.


## Installation

**Using pip:**

```bash
pip install podaac-forge-py
```

**Using poetry:**

```bash
poetry install
```


## Usage

Once `forge-py` is installed in an environment, it is used via the CLI without needing to be imported, e.g.:

```bash
forge-py -c configuration_file.cfg -g granule_file.nc
```

and will return the indices of the footprint in WKT (Well-Known Text) format.

The forge-py command-line tool accepts the following options:

- **`-c`, `--config`**: _(Required)_ Specifies the path to the configuration file. This file contains parameters for customizing the footprint generation process (see below).

- **`-g`, `--granule`**: _(Required)_ Specifies the path to the data granule file. This file contains the raw data used to generate the footprints.

- **`-o`**: _(Optional)_ File name to save output to.


## Footprint Configuration File

The configuration file (typically JSON) specifies the parameters for generating footprints from various data sources.

### Example Configuration in JSON

```json
   {
      "latVar": "group1/group2/lat",
      "lonVar": "group1/group2/lon",
      "timeVar": "time",
      "is360": false,
      "footprint": {
        "strategy": "open_cv",
        "open_cv": {
           "pixel_height": 1000,
           "simplify": 0.3,
           "min_area": 30,
           "fill_value": -99999.0,
           "fill_kernel": [30,30]
        },
        "alpha_shape": {
           "alpha": 0.2,
           "thinning": {"method": "bin_avg", "value": [0.5, 0.5]},
           "cutoff_lat": 80,
           "smooth_poles": [78,80],
           "simplify" : 0.3,
           "min_area": 30,
           "fill_value": -99999.0
        },
        "shapely_linestring": {
          "simplify": 0.9
        }
      }
    }
```

### Description of Fields

* **`lonVar`** (string, required): Longitude variable in the dataset include group if in one.
* **`latVar`** (string, required): Latitude variable in the dataset include group if in one.
* **`timevar`** (string, optional): Time variable in the dataset include group if in one.
* **`is360`** (boolean, optional, default: False): Indicates if the data is in 360 format.
* **`strategy`** (string, optional, default: alpha_shape): The algorithm to use for fitting the footprint. Options are:
  * **"alpha_shape"**: Applicable for 2D geometries like satellite swaths. Can handle file formats where the longtidue, latitude variables have dimensions `cross_track`, `along_track`, or files where the lon, lat variables are dimensions themselves and are 1D. Employs the Alpha Shape package / algorithm to construct footprints from point data.
  * **"open_cv"**: Uses OpenCV-based image processing techniques to extract footprints.
  * **"shapely_linestring"**: Applicable for linestring geometries, e.g. "1D" curves / paths. Utilizes the shapely package.

If a strategy is specified, the corresponding field to set parameters for that strategy should also be included.

* **`open_cv`**: A dictionary-like mapping of parameters to use with the `open_cv` algorithm. Parameters that can be included are:
  * **`pixel_height`** (int, optional, default: 1800): Desired pixel height for the input image.
  * **`min_area`** (int, optional): Minimum area for polygons to be retained.
  * **`fill_kernel`** (list of int, optional, default: None): Kernel size for filling holes in polygons.
  * **`simplify`** (float, optional): Controls the level of simplification applied to extracted polygons. Valid range is (0 - 1). A higher value simplifies the footprint to fewer points.
  * **`fill_value`** (float, optional, default: np.nan): Fill value in the latitude, longitude arrays.

* **`alpha_shape`** (dict, optional): A dictionary-like mapping of parameters to use with the `alpha_shape` algorithm. Parameters that can be included are:
  * **`alpha`** (float, optional, default: 0.05): Alpha value for the Alpha Shape algorithm, affecting the shape of polygons. Using a higher value will create a tighter fit, e.g. more detailed geometry. Typical values range from 0.01 to 0.2. 
  * **`thinning`** (dict, optional): Thinning the lon, lat data is typically necessary to reduce the computation time of the alpha shape algorithm. Dict key/value pairs are:
    * **`method`** (string): Thinning method to apply to the Alpha Shape. Options are "standard" and "bin_avg". "standard" will flatten the lon, lat arrays and keep every nth element. "bin_avg" will bin and average the lons, lats to a specified resolution.
    * **`value`** (list of float or float): Thinning parameter(s). If `method` is "standard", `value` is a single float specifying n, where every nth element will be retained. If `method` is "bin_avg", `value` is a 2-element list-like for the longitude and latitude bin widths to average over.
  * **`cutoff_lat`** (int, optional): Latitude above which data will be ignored.
  * **`smooth_poles`** (2-tuple of int, optional): In some cases, the poleward edge of the footprints have artifacts (e.g. jagged edges). This parameter can be used to retroactively smooth the poleward edge of the footprint. The first element is the latitude above which all points should be set to the second element. For example, `smooth_poles`=(78, 80) will take all points northward/southward of +/- 78 and change the latitude value to +/- 80, respectively.
  * **`min_area`** (int, optional): Minimum area for a polygon to be retained.
  * **`simplify`** (float, optional): Controls the level of simplification applied to extracted polygons. Valid range is (0 - 1). A higher value simplifies the footprint to fewer points.
  * **`fill_value`** (float, optional, default: np.nan): Fill value in the latitude, longitude arrays.

* **`shapely_linestring`**: A dictionary-like mapping of parameters to use with the `shapely_linestring` algorithm. Parameters that can be included are:
  * **`simplify`** (float, optional, default: 0.9): Valid range is (0 - 1). A higher value will simplify the footprint to fewer points. A lower value retains more features / vertices.

