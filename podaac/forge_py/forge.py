"""Python footprint generator"""
# pylint: disable=unused-argument

import json
from shapely.geometry import Polygon, MultiPolygon
from shapely.wkt import dumps
from podaac.forge_py.strategies import open_cv_footprint, alpha_shape_footprint, shapely_linestring_footprint


class GroupMismatchError(Exception):
    """Custom exception raised when the groups for lon and lat variables differ."""


def find_common_group_and_variables(lon_var, lat_var):
    """
    Determines the common group path for longitude and latitude variables
    and returns the variable names without their groups.

    Raises:
        GroupMismatchError: If the groups for lon_var and lat_var are different.

    Args:
        lon_var (str): Full path of the longitude variable (e.g., "group1/group2/lon").
        lat_var (str): Full path of the latitude variable (e.g., "group1/group2/lat").

    Returns:
        tuple: (common_group, lon_variable_name, lat_variable_name)
               - common_group (str): The common group path.
               - lon_variable_name (str): The name of the longitude variable without its group.
               - lat_variable_name (str): The name of the latitude variable without its group.
    """
    # Extract group paths and variable names
    lon_group, _, lon_name = lon_var.rpartition('/')
    lat_group, _, lat_name = lat_var.rpartition('/')

    # Check if the group paths are the same
    if lon_group != lat_group:
        raise GroupMismatchError(
            f"Longitude variable '{lon_var}' and latitude variable '{lat_var}' belong to different groups: "
            f"'{lon_group}' and '{lat_group}'"
        )

    return lon_group, lon_name, lat_name


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

    lon_var = read_config.get('lonVar')
    lat_var = read_config.get('latVar')

    group, lon, lat = find_common_group_and_variables(lon_var, lat_var)

    # Include general options like is360 if needed outside strategies
    common_params = {
        'is360': read_config.get('is360', False),
        'longitude_var': lon,
        'latitude_var': lat,
        'group': group
    }

    # Merge strategy parameters with any additional common parameters
    return strategy, {**common_params, **strategy_params}


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

    is_lon_lat_invalid = are_all_lon_lat_invalid(lon, lat)
    if is_lon_lat_invalid:
        raise Exception("Can't generate footprint for empty granule")

    # Dispatch to the correct footprint strategy based on `strategy`
    if strategy == "open_cv":
        footprint = open_cv_footprint.footprint_open_cv(lon, lat, path=path, **kwargs)
    elif strategy == "shapely_linestring":
        footprint = shapely_linestring_footprint.fit_footprint(lon, lat, **kwargs)
        if not footprint.is_valid:
            footprint = footprint.buffer(0)
    else:
        footprint = alpha_shape_footprint.fit_footprint(lon, lat, **kwargs)
        if not footprint.is_valid:
            footprint = footprint.buffer(0)

    if 'simplify' in kwargs:
        footprint = footprint.simplify(tolerance=kwargs['simplify'], preserve_topology=True)

    # Optionally filter small polygons
    if "min_area" in kwargs:
        footprint = remove_small_polygons(footprint, kwargs['min_area'])

    return dumps(footprint, trim=True)


def are_all_lon_lat_invalid(lon, lat):
    """
    Checks if all longitude and latitude values in a NetCDF file are invalid.

    Parameters:
        lon (array): longitude values.
        lat (array): latitude values.

    Returns:
        bool: True if all longitude and latitude values are invalid, False otherwise.
    """

    # Define valid ranges
    valid_lon = (lon >= -180) & (lon <= 180)
    valid_lat = (lat >= -90) & (lat <= 90)

    # Check if all values are invalid
    all_invalid_lon = (~valid_lon).all().item()
    all_invalid_lat = (~valid_lat).all().item()

    return all_invalid_lon and all_invalid_lat
