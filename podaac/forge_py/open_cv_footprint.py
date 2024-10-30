"""Script with algorithm to generate a wkt footprint for netcdf file using open cv"""
# pylint: disable=no-member, broad-exception-raised

import uuid
import numpy as np
import cv2
from shapely import wkt
from shapely.geometry import Polygon, MultiPolygon
from PIL import Image


def ensure_counter_clockwise(geometry):
    """
    Ensure that a given polygon or multipolygon is represented in counter-clockwise order.

    This function accepts a WKT (Well-Known Text) string or a Shapely Polygon/MultiPolygon
    object. If the input is in a clockwise orientation, it will reverse the coordinates
    to ensure counter-clockwise ordering.

    Parameters:
        geometry (str or Polygon or MultiPolygon):
            The input geometry to be checked and potentially corrected. This can be:
            - A WKT string representing a Polygon or MultiPolygon.
            - A Shapely Polygon object.
            - A Shapely MultiPolygon object.

    Returns:
        str: The corrected geometry in counter-clockwise order.

    Raises:
        ValueError: If the input is not a WKT string, Polygon, or MultiPolygon.

    Example:
        original_wkt_polygon = "POLYGON ((0 0, 1 1, 1 0, 0 0))"
        corrected_wkt = ensure_counter_clockwise(original_wkt_polygon)

        # The returned geometry will be in counter-clockwise order.
    """
    if isinstance(geometry, str):
        geometry = wkt.loads(geometry)

    # Function to ensure a single polygon is counter-clockwise
    def correct_polygon(polygon):
        # Correct the exterior ring if it's not counterclockwise
        if not polygon.exterior.is_ccw:
            exterior = list(polygon.exterior.coords)[::-1]
        else:
            exterior = list(polygon.exterior.coords)

        # Correct each interior ring if it's counterclockwise (should be clockwise for holes)
        interiors = [
            list(interior.coords)[::-1] if interior.is_ccw else list(interior.coords)
            for interior in polygon.interiors
        ]

        # Return a new polygon with corrected orientations
        return Polygon(exterior, interiors)

    # If the input is a MultiPolygon, process each polygon
    if isinstance(geometry, MultiPolygon):
        corrected_polygons = [correct_polygon(polygon) for polygon in geometry.geoms]
        corrected_geometry = MultiPolygon(corrected_polygons)
    # If the input is a single Polygon, correct it directly
    elif isinstance(geometry, Polygon):
        corrected_geometry = correct_polygon(geometry)
    else:
        raise ValueError("Input must be a WKT string, Polygon, or MultiPolygon.")

    # Return the WKT representation of the corrected geometry
    return corrected_geometry


def read_and_threshold_image(image_path, threshold_value=185):
    """
    Reads an image from the specified file path, converts it to grayscale, and applies a binary threshold.

    Parameters:
    - image_path (str): The file path to the input image.
    - threshold_value (int, optional): The threshold value for binarization. Default is 185.

    Returns:
    - img_th (ndarray): The binarized (thresholded) grayscale image.

    Notes:
    - The function converts the image to grayscale using OpenCV, then applies a binary threshold where pixel values
      above `threshold_value` are set to 255 (white), and those below are set to 0 (black).
    """
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, img_th = cv2.threshold(gray, threshold_value, 255, cv2.THRESH_BINARY)
    return img_th


def apply_morphological_operations(image, kernel_size=(5, 5)):
    """
    Applies morphological operations to clean up binary images by filling gaps and removing small noise.

    Parameters:
    - image (ndarray): The input binary image to be processed.
    - kernel_size (tuple of int, optional): The size of the structuring element for morphological operations.
      Default is (5, 5).

    Returns:
    - img_cleaned (ndarray): The image after applying morphological closing and opening operations.

    Notes:
    - This function uses a morphological closing operation to fill small gaps in the image and
      a morphological opening operation to remove small noise, both using a rectangular structuring element.
    """
    kernel = np.ones(kernel_size, np.uint8)
    img_cleaned = cv2.morphologyEx(image, cv2.MORPH_CLOSE, kernel)  # Fill gaps
    img_cleaned = cv2.morphologyEx(img_cleaned, cv2.MORPH_OPEN, kernel)  # Remove small noise
    return img_cleaned


def pixel_to_lonlat(x, y, width, height):
    """
    Converts pixel coordinates (x, y) in an image to geographic coordinates (longitude, latitude).

    Parameters:
    - x (int): The x-coordinate (horizontal) of the pixel in the image.
    - y (int): The y-coordinate (vertical) of the pixel in the image.
    - width (int): The width of the image in pixels.
    - height (int): The height of the image in pixels.

    Returns:
    - lon (float): The calculated longitude corresponding to the pixel's x-coordinate.
    - lat (float): The calculated latitude corresponding to the pixel's y-coordinate.

    Notes:
    - The conversion assumes a geographic projection where the full image width maps to the longitude range
      from -180° to +180° and the image height maps to the latitude range from +90° to -90°.
    """
    lon = x * (360 / width) - 180
    lat = 90 - y * (180 / height)
    return lon, lat


def contour_to_lonlat(contour, width, height):
    """
    Converts a contour from pixel coordinates to geographic coordinates (longitude, latitude).

    Parameters:
    - contour (ndarray): An array of contour points in pixel coordinates, typically in the format (N, 1, 2)
      where N is the number of points, and each point contains [x, y] coordinates.
    - width (int): The width of the image in pixels.
    - height (int): The height of the image in pixels.

    Returns:
    - lonlat_contour (ndarray): An array of contour points in geographic coordinates (longitude, latitude),
      with the same shape as the input contour.

    Notes:
    - The function uses `pixel_to_lonlat` to convert each pixel coordinate to longitude and latitude
      based on the image dimensions.
    - This is useful for mapping pixel-based contours onto geographic coordinates in applications
      involving geospatial data.
    """
    lonlat_contour = []
    for point in contour:
        x, y = point[0]  # extract x, y coordinates
        lon, lat = pixel_to_lonlat(x, y, width, height)
        lonlat_contour.append([lon, lat])
    return np.array(lonlat_contour)


def create_polygon_from_contours(outer_contour, holes, width, height):
    """
    Creates a polygon from an outer contour and optional inner contours (holes), converting pixel coordinates
    to geographic coordinates (longitude, latitude).

    Parameters:
    - outer_contour (ndarray): The outer contour of the polygon in pixel coordinates.
    - holes (list of ndarray): A list of inner contours (holes) in pixel coordinates. Each contour should
      be in the format (N, 1, 2), where N is the number of points, with each point as [x, y].
    - width (int): The width of the image in pixels.
    - height (int): The height of the image in pixels.

    Returns:
    - Polygon or None: A Shapely Polygon object representing the geographic polygon with the outer contour
      and holes, or `None` if the outer contour has fewer than 3 points.

    Notes:
    - The function uses `contour_to_lonlat` to convert each contour from pixel to geographic coordinates.
    - This is particularly useful for geospatial applications where polygons are needed in longitude-latitude format.
    """
    outer_coords = contour_to_lonlat(outer_contour, width, height)
    hole_coords_list = [contour_to_lonlat(hole, width, height) for hole in holes if len(hole) > 2]

    if len(outer_coords) > 2:
        return Polygon(outer_coords, hole_coords_list)
    return None


def simplify_polygon(polygon, tolerance=0.2):
    """
    Simplifies a polygon by reducing the number of vertices while preserving its general shape.

    Parameters:
    - polygon (Polygon): A Shapely Polygon object to be simplified.
    - tolerance (float, optional): The tolerance for simplification. Higher values result in greater simplification.
      Default is 0.2.

    Returns:
    - Polygon: A new Shapely Polygon object with a reduced number of vertices, simplified based on the specified tolerance.

    Notes:
    - The function uses the Douglas-Peucker algorithm, controlled by the tolerance parameter.
    - Setting `preserve_topology=True` ensures that the simplified polygon maintains its original topology,
      avoiding self-intersections.
    """
    return polygon.simplify(tolerance=tolerance, preserve_topology=True)


def process_multipolygons(contours, hierarchy, width, height):
    """
    Processes a set of contours and hierarchy information to construct polygons with holes,
    handling multiple polygons as a MultiPolygon if needed.

    Parameters:
    - contours (list of ndarray): A list of contours, where each contour is an array of points in pixel coordinates.
    - hierarchy (ndarray): An array representing the hierarchical relationships between contours,
      with each element containing indices [Next, Previous, First Child, Parent].
    - width (int): The width of the image in pixels.
    - height (int): The height of the image in pixels.

    Returns:
    - MultiPolygon or Polygon or None: A Shapely MultiPolygon if multiple polygons are detected,
      a single Polygon if only one polygon is present, or `None` if no valid polygons are found.

    Notes:
    - Outer contours (without a parent) are identified and processed as the main polygon bodies.
    - Inner contours (with the current contour as their parent) are treated as holes for the outer contours.
    - `create_polygon_from_contours` is used to construct the polygons from pixel coordinates, converting
      them into geographic coordinates (longitude, latitude).
    - This function is useful for geospatial applications that involve converting image contours into geographic polygons.
    """
    polygons = []
    for i, contour in enumerate(contours):
        if hierarchy[i][3] == -1:  # No parent -> outer contour (possible new polygon)
            # Find holes for this outer contour
            holes = [contours[j] for j in range(len(contours)) if hierarchy[j][3] == i]
            # Create polygon for the outer contour and its holes
            polygon = create_polygon_from_contours(contour, holes, width, height)
            if polygon is not None:
                polygons.append(polygon)

    # Return a MultiPolygon if there are multiple polygons, else a single polygon
    if len(polygons) > 1:
        return MultiPolygon(polygons)
    if len(polygons) == 1:
        return polygons[0]
    return None


def process_mask(image, kernel_size=(20, 20)):
    """
    Applies morphological closing to an image mask to fill small gaps, enhancing contiguous regions.

    Parameters:
    - image (ndarray): The input binary mask image to be processed.
    - kernel_size (tuple of int, optional): The size of the structuring element (kernel) used for morphological closing.
      Default is (20, 20).

    Returns:
    - ndarray: The processed binary image with small gaps filled.

    Notes:
    - Morphological closing is performed using a rectangular structuring element, which fills small gaps and
      helps create smoother, more continuous regions in binary masks.
    """
    kernel = np.ones(kernel_size, np.uint8)
    return cv2.morphologyEx(image, cv2.MORPH_CLOSE, kernel)


def convert_to_image_coords(lon, lat, image_width=3600, image_height=1800):
    """
    Converts geographic coordinates (longitude, latitude) to pixel coordinates in an image.

    Parameters:
    - lon (float or ndarray): Longitude values to be converted, either as a single value or an array.
    - lat (float or ndarray): Latitude values to be converted, either as a single value or an array.
    - image_width (int, optional): Width of the image in pixels. Default is 3600.
    - image_height (int, optional): Height of the image in pixels. Default is 1800.

    Returns:
    - img_x (ndarray): Array of x-coordinates (pixels) corresponding to the input longitude values.
    - img_y (ndarray): Array of y-coordinates (pixels) corresponding to the input latitude values.

    Notes:
    - Longitude and latitude values are converted to pixel coordinates based on the image dimensions.
    - The function ensures that pixel coordinates are within the bounds of the image dimensions using `np.clip`.
    - This is useful for mapping geographic coordinates onto an image with a specified width and height.
    """
    # Convert inputs to NumPy arrays if they aren't already
    lon = np.asarray(lon)
    lat = np.asarray(lat)

    # Perform vectorized operations
    img_x = ((lon + 180) * (image_width / 360)).astype(int)
    img_y = ((90 - lat) * (image_height / 180)).astype(int)

    # Ensure coordinates are within bounds
    img_x = np.clip(img_x, 0, image_width - 1)
    img_y = np.clip(img_y, 0, image_height - 1)

    return img_x, img_y


def write_image(filename, lat, lon, image_width=3600, image_height=1800):
    """
    Creates an image from geographic coordinates, processes it to fill gaps, and saves it as a PNG file.

    Parameters:
    - filename (str): path to the filename.
    - lat (float or ndarray): Latitude values of points to plot, either as a single value or an array.
    - lon (float or ndarray): Longitude values of points to plot, either as a single value or an array.
    - image_width (int, optional): Width of the image in pixels. Default is 3600.
    - image_height (int, optional): Height of the image in pixels. Default is 1800.

    Returns:
    - None

    Notes:
    - This function rounds latitude and longitude values, converts them to image coordinates,
      and creates a binary image where each coordinate point is set to white (255) on a black background.
    - The image is processed with a morphological closing operation to fill gaps.
    - The final processed image is saved as a PNG file with the specified filename.
    """
    # Round lat/lon to two decimal places
    lon_rounded = np.round(lon, 2)
    lat_rounded = np.round(lat, 2)

    # Initialize the image array
    image = np.zeros((image_height, image_width), dtype=np.uint8)

    # Set pixels corresponding to the lat/lon points
    # Assuming lon_rounded and lat_rounded are numpy arrays
    lon_rounded = np.array(lon_rounded)
    lat_rounded = np.array(lat_rounded)

    # Convert coordinates to image indices
    img_x, img_y = convert_to_image_coords(lon_rounded, lat_rounded, image_width, image_height)

    # Ensure indices are within image dimensions
    img_x = np.clip(img_x, 0, image_width - 1)
    img_y = np.clip(img_y, 0, image_height - 1)

    # Create an empty image array
    image = np.zeros((image_height, image_width), dtype=np.uint8)

    # Set the pixel values to 255 at the calculated coordinates
    image[img_y, img_x] = 255

    # Process the image (fill gaps using morphological closing)
    processed_image = process_mask(image)

    # Save the image
    result_image = Image.fromarray(processed_image)
    result_image.save(filename)


def reduce_precision(geometry, precision=4):
    """
    Reduces the precision of the coordinates in a geometric object (Polygon or MultiPolygon)
    by rounding them to a specified number of decimal places.

    Parameters:
    - geometry (Polygon or MultiPolygon): The geometric object whose coordinates are to be simplified.
    - precision (int, optional): The number of decimal places to round the coordinates to.
      Default is 4.

    Returns:
    - Polygon or MultiPolygon: A new geometric object with coordinates rounded to the specified precision.

    Raises:
    - ValueError: If the input geometry is neither a Polygon nor a MultiPolygon.

    Notes:
    - This function rounds the coordinates of the exterior and interior rings (if present) of
      the Polygon or MultiPolygon, allowing for reduced precision while maintaining the overall shape.
    - Useful for simplifying geometries for storage or display, particularly in applications where
      exact coordinate precision is less critical.
    """
    def round_coords(coords, precision):
        return [(round(x, precision), round(y, precision)) for x, y in coords]

    if isinstance(geometry, Polygon):
        exterior = round_coords(geometry.exterior.coords, precision)
        interiors = [round_coords(interior.coords, precision) for interior in geometry.interiors]
        return Polygon(exterior, interiors)
    if isinstance(geometry, MultiPolygon):
        # Use the .geoms attribute to iterate over individual polygons in the MultiPolygon
        polygons = [reduce_precision(polygon, precision) for polygon in geometry.geoms]
        return MultiPolygon(polygons)
    raise ValueError("Unsupported geometry type")


def footprint_open_cv(lon, lat, width=3600, height=1800, path=None, threshold_value=185):
    """
    Main pipeline for processing geographic coordinates to create a footprint polygon using image processing techniques.

    Parameters:
    - lon (array-like): Array of longitude values.
    - lat (array-like): Array of latitude values.
    - width (int, optional): Width of the output image in pixels. Default is 1800.
    - height (int, optional): Height of the output image in pixels. Default is 900.
    - threshold_value (int, optional): Threshold value for binarizing the image. Default is 185.

    Returns:
    - str: Well-Known Text (WKT) representation of the simplified polygon created from the input coordinates.

    Raises:
    - Exception: If no valid polygons are found after processing.

    Notes:
    - The function first removes any NaN values from the input longitude and latitude arrays.
    - It creates an image from the valid latitude and longitude points, processes the image to threshold
      and clean it, and then extracts contours.
    - Contours are analyzed to form polygons, which are subsequently simplified and their precision reduced.
    - The final output is a WKT representation of the polygon, which can be used for geographic data representation.
    """
    new_lon = np.array(lon).flatten()
    new_lat = np.array(lat).flatten()

    # Ensure longitude is in the range [-180, 180]
    new_lon = ((new_lon + 180) % 360.0) - 180

    # Remove NaNs from lat/lon data
    valid_points = ~np.isnan(new_lon * new_lat)
    new_lon = new_lon[valid_points]
    new_lat = new_lat[valid_points]

    # Create and save the image
    filename = f"{path}/image_{uuid.uuid4()}.png"
    write_image(filename, new_lat, new_lon, image_width=width, image_height=height)
    img_th = read_and_threshold_image(filename, threshold_value)

    img_cleaned = apply_morphological_operations(img_th)

    contours, hierarchy = cv2.findContours(img_cleaned, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    hierarchy = hierarchy[0] if hierarchy is not None else []

    polygon_structure = process_multipolygons(contours, hierarchy, width, height)

    if polygon_structure is not None:
        simplified_polygon = simplify_polygon(polygon_structure)
        reduced_precision = reduce_precision(simplified_polygon)
        counter_clockwise = ensure_counter_clockwise(reduced_precision)
        print(counter_clockwise.wkt)
        return counter_clockwise.wkt

    raise Exception("No valid polygons found.")
