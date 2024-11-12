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
* **`strategy`**: 
  * `open_cv` (string): Uses OpenCV-based image processing techniques to extract footprints.
  * `alpha_shape` (string): Employs the Alpha Shape algorithm to construct footprints from point data.
* **`open_cv`**:
  * `pixel_height` (int): Sets the desired pixel height for the input image.
  * `simplify` (float): Controls the level of simplification applied to the extracted polygons.
  * `min_area` (int): Specifies the minimum area for polygons to be considered to be removed.
  * `fill_kernel` (list of int): Defines the kernel size for filling holes in the extracted polygons.
  * `group` (string): Specifies the NetCDF file group to use for input data.
* **`alpha_shape`**:
  * `alpha` (float): Sets the alpha value for the Alpha Shape algorithm, controlling the shape of the generated polygons.
  * `thinning`: 
    * `method` (string): Specifies the thinning method to apply to the Alpha Shape.
    * `value` (list of float or float): Sets the thinning parameters.
  * `cutoff_lat` (int): Defines the latitude cutoff for smoothing.
  * `smooth_poles` (list of int): Specifies the latitude range for smoothing near the poles.
  * `group` (string): Specifies the NetCDF file group to use for input data.
  * `simplify` (float): Controls the level of simplification applied to the Alpha Shape polygons.

## Example Configuration

```json
   "footprint":{
      "strategy": "open_cv",
      "open_cv": {
         "pixel_height": 1000,
         "simplify":0.3,
         "min_area": 30,
         "fill_kernel": [30,30],
         "group": "group for lon lat"
      },
      "alpha_shape": {
         "alpha":0.2,
         "thinning": {"method": "bin_avg", "value": [0.5, 0.5]},
         "cutoff_lat": 80,
         "smooth_poles": [78,80],
         "group": "group for lon lat",
         "simplify" : 0.3
      }
   }
