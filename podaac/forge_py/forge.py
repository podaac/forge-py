import xarray as xr
import numpy as np
import alphashape
from shapely.wkt import dumps
from netCDF4 import Dataset

def fit_footprint(lon, lat, thinning_fac=100, alpha=0.05, return_xythin=False):
    """
    lon, lon: list/array-like
        Latitudes and longitudes.
    thinning_fac: int
        Factor to thin out data by (makes alphashape fit faster).
    alpha: float
        The alpha parameter passed to alphashape.
    """
    # lat, lon need to be 1D:
    x = np.array(lon).flatten()
    y = np.array(lat).flatten()

    # Thinning out the number of data points helps alphashape fit faster
    x_thin = x[np.arange(0, len(x), thinning_fac)]
    y_thin = y[np.arange(0, len(y), thinning_fac)]

    xy = np.array(list(zip(x_thin, y_thin))) # Reshape coords to use with alphashape
    alpha_shape = alphashape.alphashape(xy, alpha=alpha)
    if return_xythin:
        return alpha_shape, x_thin, y_thin
    else:
        return alpha_shape

if __name__ == "__main__":

    file = "/Users/simonl/Desktop/forge_py/measures_esdr_scatsat_l2_wind_stress_23433_v1.1_s20210228-054653-e20210228-072612.nc"

    data = xr.open_dataset(file)

    alpha_shape = fit_footprint(nc['lon'], nc['lat'], thinning_fac=70, alpha=0.03, return_xythin=False)
    wkt_representation = dumps(alpha_shape)

    print(wkt_representation)
