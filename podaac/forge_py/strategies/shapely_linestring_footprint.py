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
    # Fit footprint:
    lon = np.array(lon)
    lat = np.array(lat)
    points = LineString([(x,y) for x, y in zip(lon, lat)])
    fit = shapely.simplify(points, tolerance=tolerance)

    # Segment the footprint at international dateline crossings:
    fit_splitted = split_linestring_idl(fit.xy[0], fit.xy[1])
    
    # Repackage into MultiLineString:
    segments = []
    for i in range(len(fit_splitted[0])):
        segments.append([(x,y) for x, y in zip(fit_splitted[0][i], fit_splitted[1][i])])
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
    dlons_abs[np.where(dlons_abs > 359)]  # Use 359 instead of 360 to be safe.
    i_cross = np.where(dlons_abs > 180)[0] + 1 # +1 for translating dlon index to lon index.
    
    # Split lon, lat on these indices, to create a list of arrays for each linestring segment:
    if len(i_cross) > 0:
        i_split = [0] + list(i_cross) + [len(lons_test)] # Index bounds to subset on. Add first/last
        lons_split, lats_split = [], []
        for j in range(len(i_split)-1):
            lons_split.append(lons[i_split[j]:i_split[j+1]])
            lats_split.append(lats[i_split[j]:i_split[j+1]])

        return lons_split, lats_split

    else: # if no splitting needed, return lons, lats as single arrays:
        return [lons], [lats]