"""Python footprint generator"""
import numpy as np
import alphashape
from shapely.geometry import Polygon
from shapely.wkt import dumps


def fit_footprint(lon, lat, thinning_fac=100, alpha=0.05, is360=False):
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

    return alpha_shape


def scatsat_footprint(lon, lat, thinning_fac=30, alpha=0.035, is360=False):
    """
    Fits footprint g-polygon for level 2 data set SCATSAT1_ESDR_L2_WIND_STRESS_V1.1. Uses the
    alphashape package for the fit, which returns a shapely.geometry.polygon.Polygon object.

    lon, lon: list/array-like
        Latitudes and longitudes.
    thinning_fac: int
        Factor to thin out data by (makes alphashape fit faster).
    alpha: float
        The alpha parameter passed to alphashape.
    is360: bool
        Tell us if the logitude data is between 0-360
    """
    # lat, lon need to be 1D:

    lon_array = lon
    if is360:
        lon_array = ((lon + 180) % 360.0) - 180

    x = np.array(lon_array).flatten()
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

    if strategy == "scatsat":
        alpha_shape = scatsat_footprint(lon, lat, thinning_fac=thinning_fac, alpha=alpha, is360=is360)
    else:
        alpha_shape = fit_footprint(lon, lat, thinning_fac=thinning_fac, alpha=alpha, is360=is360)
    alpha_shape = alpha_shape.simplify(simplify)

    # If the polygon is not valid, attempt to fix self-intersections
    if not alpha_shape.is_valid:
        alpha_shape = alpha_shape.buffer(0)

    wkt_alphashape = dumps(alpha_shape)
    return wkt_alphashape
