# forge-py

The Footprint Generator project provides tools for generating geographic footprints from various data sources. This tool supports different generation strategies using open cv or alpha shape.

## Installation

**Using pip:**

```bash
pip install forge-py
```

**Using poetry:**

```bash
poetry install
```

## CLI Usage

```bash
forge-py -c configuration_file.cfg -g granule_file.nc
```

The forge-py command-line tool accepts the following options:

- **`-c`, `--config`**: _(Optional)_ Specifies the path to the configuration file. This file contains parameters for customizing the footprint generation process.

- **`-g`, `--granule`**: _(Required)_ Specifies the path to the data granule file. This file contains the raw data used to generate the footprints.


## Footprint Configuration

The configuration file specifies the parameters for generating footprints from various data sources, primarily using OpenCV and Alpha Shape algorithms.

## Configuration Options

### `footprint`
* **`lonVar`** (string, required): Longitude variable in the dataset include group if in one.
* **`latVar`** (string, required): Latitude variable in the dataset include group if in one.
* **`is360`** (boolean, optional, default: False): Indicates if the data is in 360 format.
* **`strategy`** (optional, default: alpha_shape): 
  * **`open_cv`**: Uses OpenCV-based image processing techniques to extract footprints.
  * **`alpha_shape`**: Employs the Alpha Shape algorithm to construct footprints from point data.

* **`open_cv`**:
  * **`pixel_height`** (int, optional, default: 1800): Desired pixel height for the input image.
  * **`min_area`** (int, optional): Minimum area for polygons to be retained.
  * **`fill_kernel`** (list of int, optional, default: None): Kernel size for filling holes in polygons.
  * **`simplify`** (float, optional,): Controls the level of simplification applied to extracted polygons.
  * **`fill_value`** (float, optional, default: np.nan): Fill value in the latitude, longitude arrays.

* **`alpha_shape`**:
  * **`alpha`** (float, optional, default: 0.05): Alpha value for the Alpha Shape algorithm, affecting the shape of polygons.
  * **`thinning`** (dic, optional):
    * **`method`** (string): Thinning method to apply to the Alpha Shape.
    * **`value`** (list of float or float): Thinning parameters.
  * **`cutoff_lat`** (int, optional): Latitude cutoff for smoothing.
  * **`min_area`** (int, optional): Minimum area for polygons to be retained.
  * **`smooth_poles`** (list of int, optional): Latitude range for smoothing near poles.
  * **`simplify`** (float, optional): Controls the level of simplification applied to extracted polygons.
  * **`fill_value`** (float, optional, default: np.nan): Fill value in the latitude, longitude arrays.

## Example Configuration

```json
   {
      "latVar":"group1/group2/lat",
      "lonVar":"group1/group2/lon",
      "timeVar":"time",
      "is360":false,
      "footprint":{
        "strategy": "open_cv",
        "open_cv": {
           "pixel_height": 1000,
           "simplify":0.3,
           "min_area": 30,
           "fill_value": -99999.0,
           "fill_kernel": [30,30]
        },
        "alpha_shape": {
           "alpha":0.2,
           "thinning": {"method": "bin_avg", "value": [0.5, 0.5]},
           "cutoff_lat": 80,
           "smooth_poles": [78,80],
           "simplify" : 0.3,
           "min_area": 30,
           "fill_value": -99999.0
        }
      }
    }
