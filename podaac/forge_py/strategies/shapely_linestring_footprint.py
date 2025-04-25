"""Python footprint generator for linestring geometries, utilizing the Shapely package."""

import numpy as np
import shapely
from shapely import LineString


def fit_footprint(lon, lat, tolerance=0.9, **kwargs):
    """
    Fits instrument coverage footprint for level 2 linestring data (e.g coverage 
    falls on a single line or curve). Uses a function from the Shapely package, 
    shapely.simplify(). Output is a polygon object for the indices of the footprint 
    outline. Returns a shapely.geometry.linestring.LineString object.

    Inputs
    ------
    lon, lat: array-like, 1D. 
        Longitude, latitude values as 1D arrays.
    tolerance: float.
        Keyword arg passed to shapely.simplify(). The maximum allowed geometry 
        displacement. The higher this value, the smaller the number of vertices 
        in the resulting geometry.
    """
    lon = np.array(lon)
    lat = np.array(lat)
    points = LineString([(x,y) for x, y in zip(lon, lat)])
    return shapely.simplify(points, tolerance=tolerance)