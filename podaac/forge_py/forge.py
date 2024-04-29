"""Python footprint generator"""

import numpy as np
import alphashape


def fit_footprint(lon, lat, thinning_fac=100, alpha=0.05, return_xythin=False, is360=False):
    """
    lon, lon: list/array-like
        Latitudes and longitudes.
    thinning_fac: int
        Factor to thin out data by (makes alphashape fit faster).
    alpha: float
        The alpha parameter passed to alphashape.
    is360: bool
        Tell us if the logitude data is between 0-360
    """

    lon_array = lon
    if is360:
        lon_array = ((lon + 180) % 360.0) - 180

    # lat, lon need to be 1D:
    x = np.array(lon_array).flatten()
    y = np.array(lat).flatten()

    # Thinning out the number of data points helps alphashape fit faster
    x_thin = x[np.arange(0, len(x), thinning_fac)]
    y_thin = y[np.arange(0, len(y), thinning_fac)]

    xy = np.array(list(zip(x_thin, y_thin)))  # Reshape coords to use with alphashape
    alpha_shape = alphashape.alphashape(xy, alpha=alpha)
    if return_xythin:
        return alpha_shape, x_thin, y_thin
    return alpha_shape
