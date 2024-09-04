"""Python footprint generator"""
import numpy as np
import alphashape
from shapely.geometry import Polygon, MultiPolygon
from shapely.wkt import dumps
import shapely


def get_outer_edges(arr):
    """Function to get the outer edge points of a 2d array"""

    top_edge = arr[0, :]  # First row
    bottom_edge = arr[-1, ::-1]  # Last row (reversed)

    left_edge = arr[1:-1, 0]  # First column (excluding first and last rows)
    right_edge = arr[1:-1, -1][::-1]  # Last column (excluding first and last rows, reversed)

    # Combine all edges into a single array
    return np.concatenate((top_edge, right_edge, bottom_edge, left_edge))


def remove_outer_nan_edges(arr):
    """Function to remove nans around the edges of a 2d array"""

    # Check and remove rows from the top and bottom that are all NaN
    while np.isnan(arr[0, :]).all():
        arr = arr[1:, :]
    while np.isnan(arr[-1, :]).all():
        arr = arr[:-1, :]

    # Check and remove columns from the left and right that are all NaN
    while np.isnan(arr[:, 0]).all():
        arr = arr[:, 1:]
    while np.isnan(arr[:, -1]).all():
        arr = arr[:, :-1]

    return arr


def generate_footprint(lon, lat, thinning_fac=30, alpha=0.05, is360=False, simplify=0.1,
                       strategy=None, cutoff_lat=None, smooth_poles=None, fill_value=np.nan,  # pylint: disable=unused-argument
                       thinning_method='standard'):
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
    thinning_method string:
        Method to thing out the array
    """

    # Transform lon array if it is 360
    lon_array = lon
    if is360:
        lon_array = ((lon + 180) % 360.0) - 180
    thinning = {'method': thinning_method, 'value': thinning_fac}
    alpha_shape = fit_footprint(lon_array, lat, alpha=alpha, thinning=thinning, cutoff_lat=cutoff_lat, smooth_poles=smooth_poles, fill_value=fill_value)
    alpha_shape = alpha_shape.simplify(simplify)

    # If the polygon is not valid, attempt to fix self-intersections
    if not alpha_shape.is_valid:
        alpha_shape = alpha_shape.buffer(0)

    wkt_alphashape = dumps(alpha_shape)
    return wkt_alphashape


def fit_footprint(
        lon, lat, alpha=0.05,
        thinning=None, cutoff_lat=None,
        smooth_poles=None, fill_value=np.nan,
        return_xythin=False):
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
        elif thinning["method"] == "outer-edges":
            new_lon = remove_outer_nan_edges(lon)
            new_lat = remove_outer_nan_edges(lat)
            outer_lon_edges = get_outer_edges(new_lon).flatten()
            outer_lat_edges = get_outer_edges(new_lat).flatten()

            x_thin = x[np.arange(0, len(x), thinning["value"])]
            y_thin = y[np.arange(0, len(y), thinning["value"])]

            x_thin = np.concatenate((outer_lon_edges, x_thin))
            y_thin = np.concatenate((outer_lat_edges, y_thin))
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
