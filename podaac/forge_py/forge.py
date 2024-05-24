"""Python footprint generator"""
import numpy as np
import alphashape
from shapely.geometry import Polygon
from shapely.wkt import dumps


def fit_footprint(lon, lat, thinning_fac=100, alpha=0.05):
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

    xy = np.array(list(zip(x_thin, y_thin)))  # Reshape coords to use with alphashape
    alpha_shape = alphashape.alphashape(xy, alpha=alpha)

    return alpha_shape


def scatsat_footprint(lon, lat, thinning_fac=30, alpha=0.035):
    """
    Fits footprint g-polygon for level 2 data set SCATSAT1_ESDR_L2_WIND_STRESS_V1.1. Uses the
    alphashape package for the fit, which returns a shapely.geometry.polygon.Polygon object.

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

    # Outlying data near the poles. As a quick fix, remove all data near the poles, at latitudes higher than
    # 87 degrees. This quick fix has impact on footprint shape.
    i_lolats = np.where(abs(y) < 86)
    x = x[i_lolats]
    y = y[i_lolats]

    # Thinning out the number of data points helps alphashape fit faster
    x_thin = x[np.arange(0, len(x), thinning_fac)]
    y_thin = y[np.arange(0, len(y), thinning_fac)]

    # Fit with alphashape
    xy = np.array(list(zip(x_thin, y_thin)))  # Reshape coords to use with alphashape
    alpha_shape = alphashape.alphashape(xy, alpha=alpha)

    # Because of the thinning processes, the pole-edges of the footprint are jagged rather than
    # flat, quick fix this by making all latitude points above 85 degrees a constant value:
    fp_lon, fp_lat = alpha_shape.exterior.coords.xy
    fp_lat = np.array(fp_lat)
    fp_lat[np.where(fp_lat > 82)] = 88
    fp_lat[np.where(fp_lat < -82)] = -88
    footprint = Polygon(list(zip(fp_lon, np.asarray(fp_lat, dtype=np.float64))))

    return footprint


def cowvr_footprint(lon, lat, thinning_fac=200, alpha=0.03):
    """
    Uses alphashape to get the footprint from a COWVR EDR or TSDR file using the lat, lon data.
    Returns: (1) the alpha shape object (contains a shapely object with the footprint coords),

    lon, lon: list/array-like
        Latitudes and longitudes.
    thinning_fac: int
        Factor to thin out data by (makes alphashape fit faster).
    alpha: float
        The alpha parameter passed to alphashape.
    """

    # Remove missing values:
    lon_qc = lon.where(lon > -999999).values
    lat_qc = lat.where(lat > -999999).values

    ifinite = np.isfinite(lon_qc * lat_qc)
    lon_qc = lon_qc[ifinite]
    lat_qc = lat_qc[ifinite]

    # Thin out arrays so that alphashape doesn't have to work as hard:
    lon_thin = lon_qc[np.arange(0, len(lon_qc), thinning_fac)]
    lat_thin = lat_qc[np.arange(0, len(lat_qc), thinning_fac)]

    # Fit the footprint to a polygon:
    xy = np.array(list(zip(lon_thin, lat_thin)))  # Reshape coords to use with alphashape
    alpha_shape = alphashape.alphashape(xy, alpha=alpha)

    return alpha_shape


def generate_footprint(lon, lat, thinning_fac=30, alpha=0.035, is360=False, simplify=0.1, strategy=None):
    """
    Generates footprint by calling different footprint strategies

    lon, lon: list/array-like
        Latitudes and longitudes.
    thinning_fac: int
        Factor to thin out data by (makes alphashape fit faster).
    alpha: float
        The alpha parameter passed to alphashape.
    is360: bool
        Tell us if the logitude data is between 0-360
    simplify:
        simplify polygon factor
    strategy:
        What footprint strategy to use
    """

    strategy_functions = {
        "scatsat": scatsat_footprint,
        "cowvr": cowvr_footprint
    }
    # Get the function corresponding to the strategy, or the default function
    selected_function = strategy_functions.get(strategy, fit_footprint)
    # Transform lon array if it is 360
    lon_array = lon
    if is360:
        lon_array = ((lon + 180) % 360.0) - 180
    # Call the selected function with the provided arguments
    alpha_shape = selected_function(lon_array, lat, thinning_fac=thinning_fac, alpha=alpha)
    alpha_shape = alpha_shape.simplify(simplify)

    # If the polygon is not valid, attempt to fix self-intersections
    if not alpha_shape.is_valid:
        alpha_shape = alpha_shape.buffer(0)

    wkt_alphashape = dumps(alpha_shape)
    return wkt_alphashape
