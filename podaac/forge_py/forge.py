"""Python footprint generator"""
import numpy as np
import alphashape
from shapely.geometry import Polygon, MultiPolygon
from shapely.wkt import dumps
import shapely


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


def generate_footprint(lon, lat, thinning_fac=30, alpha=0.035, is360=False, simplify=0.1,
                       strategy=None, cutoff_lat=None, smooth_poles=None):
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
    selected_function = strategy_functions.get(strategy, None)
    # Transform lon array if it is 360
    lon_array = lon
    if is360:
        lon_array = ((lon + 180) % 360.0) - 180
    # Call the selected function with the provided arguments
    if selected_function is not None:
        alpha_shape = selected_function(lon_array, lat, thinning_fac=thinning_fac, alpha=alpha)
    else:
        thinning = {'method': 'standard', 'value': thinning_fac}
        alpha_shape = fit_footprint(lon_array, lat, thinning=thinning, cutoff_lat=cutoff_lat, smooth_poles=smooth_poles)
    alpha_shape = alpha_shape.simplify(simplify)

    # If the polygon is not valid, attempt to fix self-intersections
    if not alpha_shape.is_valid:
        alpha_shape = alpha_shape.buffer(0)

    wkt_alphashape = dumps(alpha_shape)
    return wkt_alphashape


def fit_footprint(
        lon, lat, alpha=0.05,
        thinning=None, cutoff_lat=None,
        smooth_poles=None,
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
    return_xythin: bool, default = False
        If True, returns the thinned out latitude, longitude arrays along with the
        footprint.
    """

    x, y = np.array(lon).flatten(), np.array(lat).flatten()
    mask = ~np.isnan(x) & ~np.isnan(y)
    x, y = x[mask], y[mask]

    # Optional thinning (typically helps alphashape fit faster):
    if thinning is not None:
        if thinning["method"] == "standard":
            x_thin = x[np.arange(0, len(x), thinning["value"])]
            y_thin = y[np.arange(0, len(y), thinning["value"])]
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
