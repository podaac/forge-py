"""Python footprint generator for linestring geometries, utilizing the Shapely package."""

import numpy as np
import shapely
from shapely import LineString, MultiLineString


def fit_footprint(lon, lat, simplify=0.9, max_dist=None, **kwargs):
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
    max_dist (optional): float
        Maximum distance allowed between adjacent footprint points, above which the
        path will be broken into segments on either side of those pair of points 
        (breaking the LineString into MultiLineString).
    """
    lon = np.array(lon)
    lat = np.array(lat)

    # Optional splitting at pairs of points farther apart than a threshold distance:
    if max_dist is None:  # Default to a single segment with entire path:
        lon_segments, lat_segments = [lon], [lat]
    else:
        lon_segments, lat_segments = split_path_maxdist(lon, lat, max_dist)
    
    # Package as LineString objects:
    points_segments = []  # Hold LineString objects for each segment in here.
    for lonseg, latseg in zip(lon_segments, lat_segments):
        points_segments.append(LineString([(x, y) for x, y in zip(lonseg, latseg)]))

    # Fit, either whole path or each segment if there was splitting:
    fit = [ shapely.simplify(pts, tolerance=simplify) for pts in points_segments ]
    
    # Split any footprint segments at international dateline crossings.
    # During this process there is an awkward recasting of paths from LineString 
    # objs to a list of np.arrays, which accounts for most of the code below:
    fit_idlsplit = [[],[]]  # First element for lons, 2nd element for lats.
    for seg in fit:
        lons_split_idl, lats_split_idl = split_path_idl(seg.xy[0], seg.xy[1])
        fit_idlsplit[0] = fit_idlsplit[0] + lons_split_idl
        fit_idlsplit[1] = fit_idlsplit[1] + lats_split_idl

    # Recast final result into a MultiLineString object and return:
    temp_segs = []
    for i in range(len(fit_idlsplit[0])):
        temp_segs.append([(x, y) for x, y in zip(fit_idlsplit[0][i], fit_idlsplit[1][i])])
    return MultiLineString(temp_segs)


def split_path_idl(lons, lats):
    """
    Splits a 1D latitude, longitude path into two if the path crosses the international
    dateline (IDL). Can do multiple splits if there are several IDL crossings. Inputs lon, lat
    are 1D numpy arrays with the same length and ordered along the path. Longitudes should
    have the domain [-180, 180). Returns two lists of numpy arrays, one each for lons and lats.
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
    

def split_path_maxdist(lons, lats, max_dist):
    """
    Splits a 1D latitude, longitude path into two or several segments at pairs of points that are
    further apart than a threshold distance (computed as the haversine great circle distance).
    Inputs lon, lat are 1D numpy arrays with the same length and ordered along the path. max_dist
    is the threshold distance (float). Returns two lists of numpy arrays, one each for lons and lats.
    """
    # Compute haversine distance and get the index for values grater than threshold:
    havdist = haversine_distance(lons[:-1], lats[:-1], lons[1:], lats[1:])
    i_gt_max = np.where(havdist > max_dist)[0]

    # Split arrays if needed:
    if len(i_gt_max) > 0:
        # Append first/last index for easier indexing. -1 is used instead of 0 for the first index 
        # so that when +1 is added below it will return to 0:
        i_gt_max = [-1] + list(i_gt_max) + [len(havdist)]
        lon_segs = []
        lat_segs = []
        for j in range(len(i_gt_max)-1):
            lon_segs.append(lons[i_gt_max[j] + 1 : i_gt_max[j+1] + 1])  # +1 translates to needed index in lons.
            lat_segs.append(lats[i_gt_max[j] + 1 : i_gt_max[j+1] + 1])  # +1 translates to needed index in lats.
        return lon_segs, lat_segs
    else:
        return [lons], [lats]
    

def haversine_distance(lon1, lat1, lon2, lat2, r_earth=6378.137):
    """
    Computes the great circle distance between two points in km's. Input latitude and longitudes 
    should be in degrees and numpy array-like. Default is to assume radius of Earth at equator. 
    r_earth should be in km's.
    """
    lon1 = np.deg2rad(lon1)  # Convert to radians
    lat1 = np.deg2rad(lat1)
    lon2 = np.deg2rad(lon2)
    lat2 = np.deg2rad(lat2)

    # Compute chord length, central angle, and great circle distance:
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    chord_len = 2*( np.sin(dlat/2)**2 + np.cos(lat1)*np.cos(lat2)*np.sin(dlon/2)**2 )**0.5
    return r_earth*2*np.arcsin(chord_len/2)
