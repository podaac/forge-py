"""Python footprint generator"""
# pylint: disable=unused-argument

import json
import numpy as np
import alphashape
from shapely.geometry import Polygon, MultiPolygon
from shapely.wkt import dumps
import shapely
import pandas as pd
from podaac.forge_py import open_cv_footprint


def load_footprint_config(config_file):
    """
    Load and process the footprint configuration from a JSON file.

    Parameters:
    ----------
    config_file : str
        Path to the JSON configuration file.

    Returns:
    -------
    tuple
        (strategy, config), where `strategy` is the footprint strategy to use,
        and `config` is a dictionary of parameters specific to that strategy.
    """
    with open(config_file) as config_f:
        read_config = json.load(config_f)

    # Select the specified strategy and its parameters
    footprint_config = read_config.get('footprint', {})
    strategy = footprint_config.get('strategy', 'alpha_shape')  # Default to 'alpha_shape'
    strategy_params = footprint_config.get(strategy, {})  # Get params for chosen strategy

    # Include general options like is360 if needed outside strategies
    common_params = {
        'is360': read_config.get('is360', False),
        'longitude_var': read_config.get('lonVar'),
        'latitude_var': read_config.get('latVar')
    }

    # Merge strategy parameters with any additional common parameters
    return strategy, {**common_params, **strategy_params}


def thinning_bin_avg(x, y, rx, ry):
    """
    One of the options for fit_footprint().
    Thin out x, y data via binning and averaging method.

    Inputs
    ------
    x, y: 1d array-like.
        Data
    rx, ry: scalars.
        Nearest values to round x and y to. E.g. if rx=2, then x will be rounded to
        nearest 0, 2, 4, 6, ... . If rx=0.5, then x will be rounded to nearest
        0, 0.5, 1, 1.5, ... .
    """

    xy = pd.DataFrame({"x": x, "y": y})
    x_rounded = rx*np.round(xy["x"]/rx)
    y_rounded = ry*np.round(xy["y"]/ry)
    xy_thinned = xy.groupby(by=[x_rounded, y_rounded]).mean()
    return xy_thinned["x"].values, xy_thinned["y"].values


def remove_small_polygons(geometry, min_area):
    """
    Removes polygons from a MultiPolygon that are smaller than a specified area threshold.

    If the input is a single Polygon, it is returned as-is without filtering. If the input
    is a MultiPolygon, only polygons with an area greater than or equal to the specified
    minimum area are retained in the output.

    Parameters:
    ----------
    geometry : shapely.geometry.Polygon or shapely.geometry.MultiPolygon
        The input geometry, which can be a single Polygon or a MultiPolygon.
    min_area : float
        The minimum area threshold. Polygons with an area less than this value
        are removed if the input is a MultiPolygon.

    Returns:
    -------
    shapely.geometry.Polygon or shapely.geometry.MultiPolygon or None
        - If the input is a single Polygon, it is returned without modification.
        - If the input is a MultiPolygon, a new MultiPolygon containing only polygons
          meeting the area threshold is returned.
        - If entire area too small then return original multipolygon
    """

    # Ensure the geometry is a MultiPolygon for uniform processing
    if isinstance(geometry, Polygon):
        return geometry

    # Filter polygons based on minimum area
    filtered_polygons = [polygon for polygon in geometry.geoms if polygon.area >= min_area]

    # Create a new MultiPolygon from the filtered polygons
    result = MultiPolygon(filtered_polygons) if filtered_polygons else geometry

    # Return WKT format if it was originally a string, otherwise return the geometry object
    return result


def generate_footprint(lon, lat, strategy=None, is360=False, path=None, **kwargs):
    """
    Generates a geographic footprint using a specified strategy.

    Parameters:
    ----------
    lon, lat : list or array-like
        Latitude and longitude values.
    strategy : str, optional
        The footprint strategy to use ('open_cv' or 'alpha_shape').
    is360 : bool, default=False
        If True, adjusts longitude values from 0-360 to -180-180 range.
    path : str, optional
        File path for saving output if the strategy requires it.
    **kwargs : dict, optional
        Additional parameters to be passed to the chosen strategy function.

    Returns:
    -------
    str
        The footprint as a WKT (Well-Known Text) string.
    """
    # Adjust longitude for 0-360 to -180-180 range if needed
    if is360:
        lon = ((lon + 180) % 360.0) - 180

    # Dispatch to the correct footprint strategy based on `strategy`
    if strategy == "open_cv":
        footprint = open_cv_footprint.footprint_open_cv(lon, lat, path=path, **kwargs)
    else:
        footprint = fit_footprint(lon, lat, **kwargs)
        if not footprint.is_valid:
            footprint = footprint.buffer(0)

    if 'simplify' in kwargs:
        footprint = footprint.simplify(tolerance=kwargs['simplify'], preserve_topology=True)

    # Optionally filter small polygons
    if "min_area" in kwargs:
        footprint = remove_small_polygons(footprint, kwargs['min_area'])

    return dumps(footprint)


def fit_footprint(
        lon, lat, alpha=0.05,
        thinning=None, cutoff_lat=None,
        smooth_poles=None, fill_value=np.nan,
        return_xythin=False, **kwargs):
    """
    Fits instrument coverage footprint for level 2 data set. Output is a polygon object for
    the indices of the footprint outline. Uses the alphashape package for the fit,
    which returns a shapely.geometry.polygon.Polygon or
    shapely.geometry.multipolygon.MultiPolygon object.

    lon, lat: list/array-like's
        Latitudes and longitudes of instrument coverage. Should be the same shape and size.
    alpha: float
        The alpha parameter passed to alphashape. Typical values that work for
        L2 footprinting are in the range 0.02 - 0.06.
    thinning: (optional) dictionary
        Optional method for removing some of the data points in the lon, lat arrays. It is
        often handy because thinning out the data makes the fit faster. Dict keys are
        "method" and "value". If "method" is set to "standard", then e.g. a "value" of
        100 will thin out the arrays to every 100th point; in this case "value" should be
        an int.
    cutoff_lat: (optional) float, default = None
        If specified, latitudes higher than this threshold value will be
        removed before the fit is performed. This works in both the north and
        south direction, e.g. for a value of x, both points north of x and south
        of -x will be removed.
    smooth_poles: (optional) 2-tuple of floats, default = None
        If specified, the first element gives the threshold latitude above which
        any footprint indicies will have their latitudes set to the value of the
        second element in "smooth_poles".
    fill_value: (optional) float
        Fill value in the latitude, longitude arrays. Default = np.nan; the default
        will work even if the data have no NAN's. Future functionality will accommodate
        multiple possible fill values.
    return_xythin: bool, default = False
        If True, returns the thinned out latitude, longitude arrays along with the
        footprint.
    """

    # Prep arrays and remove missing values:
    x = np.array(lon).flatten()
    y = np.array(lat).flatten()
    if fill_value is np.nan:
        inan = np.isnan(x*y)
    else:
        inan = (x == fill_value) | (y == fill_value)
    x = x[~inan]
    y = y[~inan]

    # Optional thinning (typically helps alphashape fit faster):
    if thinning is not None:
        if thinning["method"] == "standard":
            x_thin = x[np.arange(0, len(x), thinning["value"])]
            y_thin = y[np.arange(0, len(y), thinning["value"])]
        if thinning["method"] == "bin_avg":
            rx, ry = thinning["value"][0], thinning["value"][1]
            x_thin, y_thin = thinning_bin_avg(x, y, rx, ry)
    else:
        x_thin = x
        y_thin = y

    # Optional removal of "outlying" data near the poles. Removes data at latitudes
    # higher than the specified value. This will have an impact on footprint shape.
    if cutoff_lat is not None:
        i_lolats = np.where(abs(y_thin) < cutoff_lat)
        x_thin = x_thin[i_lolats]
        y_thin = y_thin[i_lolats]

    # Fit with alphashape
    xy = np.array(list(zip(x_thin, y_thin)))  # Reshape coords to use with alphashape
    footprint = alpha_shape = alphashape.alphashape(xy, alpha=alpha)

    # Optional pole smoothing: if the data was thinned, the fitted footprint may
    # have jagged pole-edges. This can be optionally smoothed by making all
    # latitudes higher than some threshold a constant value:
    def pole_smoother(fp_lon, fp_lat, lat_thresh, lat_target):
        """
        Takes longitude, latitude array-likes from a single Polygon representing a footprint.
        Smooths the latitude values that exceed a certain threshold by clamping them to a target value.
        """
        # Convert to numpy arrays if they are not already
        fp_lat = np.asarray(fp_lat, dtype=np.float64)

        # Apply thresholding using boolean indexing
        fp_lat[fp_lat > lat_thresh] = lat_target
        fp_lat[fp_lat < -lat_thresh] = -lat_target

        # Return the smoothed polygon
        return Polygon(zip(fp_lon, fp_lat))

    smooth_poles = None
    if smooth_poles is not None:
        if isinstance(alpha_shape, shapely.geometry.polygon.Polygon):
            footprint = pole_smoother(*alpha_shape.exterior.coords.xy, *smooth_poles)
        elif isinstance(alpha_shape, shapely.geometry.multipolygon.MultiPolygon):
            footprint = MultiPolygon([
                pole_smoother(*p.exterior.coords.xy, *smooth_poles)
                for p in alpha_shape.geoms
            ])

    if return_xythin:
        return footprint, x_thin, y_thin
    return footprint
