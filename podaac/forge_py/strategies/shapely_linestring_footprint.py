"""Python footprint generator for linestring geometries, utilizing the Shapely package."""

import numpy as np
import shapely
from shapely import LineString, MultiLineString


def fit_footprint(lon, lat, simplify=0.9, **kwargs):
    """
    Fits instrument coverage footprint for level 2 linestring data (e.g coverage
    falls on a single line or curve). Uses a function from the Shapely package,
    shapely.simplify(). Output is a polygon object for the indices of the footprint
    outline. Returns a shapely.MultiLineString object.

    Inputs
    ------
    lon, lat: array-like, 1D.
        Longitude, latitude values as 1D arrays.
    tolerance: float.
        Keyword arg passed to shapely.simplify(). The maximum allowed geometry
        displacement. The higher this value, the smaller the number of vertices
        in the resulting geometry.
    """
    # Fit footprint:
    lon = np.array(lon)
    lat = np.array(lat)
    points = LineString([(x, y) for x, y in zip(lon, lat)])
    fit = shapely.simplify(points, tolerance=simplify)

    # Segment the footprint at international dateline crossings:
    fit_splitted = split_linestring_idl(fit.xy[0], fit.xy[1])

    # Repackage into MultiLineString:
    segments = []
    for i in range(len(fit_splitted[0])):
        segments.append([(x, y) for x, y in zip(fit_splitted[0][i], fit_splitted[1][i])])
    return MultiLineString(segments)


def split_linestring_idl(lons, lats):
    """
    Splits a linestring representing a latitude, longitude path on the international
    dateline (IDL). Can do multiple splits if there are several IDL crossings. Inputs lon, lat
    are 1D numpy arrays with the same length and ordered along the path. Longitudes should
    have the domain [-180, 180).
    """
    # Find indices where longitude difference is >= 360 between subsequent points.
    lons = np.array(lons)
    lats = np.array(lats)
    dlons_abs = abs(lons[1:] - lons[:-1])
    i_cross = np.where(dlons_abs > 359)[0] + 1  # Use 359 instead of 360 to be safe. +1 translates dlon to lon index.

    # Split lon, lat on these indices, to create a list of arrays for each linestring segment:
    if len(i_cross) > 0:
        lons_split = np.split(lons, i_cross)
        lats_split = np.split(lats, i_cross)
        return lons_split, lats_split

    else:  # if no splitting needed, return lons, lats as single arrays:
        return [lons], [lats]
