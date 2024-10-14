import numpy as np
import cv2
from shapely.geometry import Polygon, MultiPolygon
import xarray as xr
from PIL import Image
import cv2

# Image pre-processing functions
def read_and_threshold_image(image_path, threshold_value=185):
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, img_th = cv2.threshold(gray, threshold_value, 255, cv2.THRESH_BINARY)
    return img_th

def apply_morphological_operations(image, kernel_size=(5,5)):
    kernel = np.ones(kernel_size, np.uint8)
    img_cleaned = cv2.morphologyEx(image, cv2.MORPH_CLOSE, kernel)  # Fill gaps
    img_cleaned = cv2.morphologyEx(img_cleaned, cv2.MORPH_OPEN, kernel)  # Remove small noise
    return img_cleaned

# Contour and coordinate conversion functions
def pixel_to_lonlat(x, y, width, height):
    lon = x * (360 / width) - 180
    lat = 90 - y * (180 / height)
    return lon, lat

def contour_to_lonlat(contour, width, height):
    lonlat_contour = []
    for point in contour:
        x, y = point[0]  # extract x, y coordinates
        lon, lat = pixel_to_lonlat(x, y, width, height)
        lonlat_contour.append([lon, lat])
    return np.array(lonlat_contour)

# Functions for processing polygons
def create_polygon_from_contours(outer_contour, holes, width, height):
    outer_coords = contour_to_lonlat(outer_contour, width, height)
    hole_coords_list = [contour_to_lonlat(hole, width, height) for hole in holes if len(hole) > 2]
    
    if len(outer_coords) > 2:
        return Polygon(outer_coords, hole_coords_list)
    return None

def simplify_polygon(polygon, tolerance=0.2):
    return polygon.simplify(tolerance=tolerance, preserve_topology=True)

# Strategy for handling multipolygons with holes
def process_multipolygons(contours, hierarchy, width, height):
    polygons = []
    for i, contour in enumerate(contours):
        if hierarchy[i][3] == -1:  # No parent -> outer contour (possible new polygon)
            # Find holes for this outer contour
            holes = []
            for j in range(len(contours)):
                if hierarchy[j][3] == i:  # Contour `j` is a child of outer contour `i` (hole)
                    holes.append(contours[j])
            
            # Create polygon for the outer contour and its holes
            polygon = create_polygon_from_contours(contour, holes, width, height)
            if polygon is not None:
                polygons.append(polygon)
    
    # Return a MultiPolygon if there are multiple polygons, else a single polygon
    if len(polygons) > 1:
        return MultiPolygon(polygons)
    elif len(polygons) == 1:
        return polygons[0]
    return None

# Apply morphological closing to fill small gaps in the image
def process_mask(image, kernel_size=(20, 20)):
    kernel = np.ones(kernel_size, np.uint8)
    return cv2.morphologyEx(image, cv2.MORPH_CLOSE, kernel)

# Convert latitude and longitude to image coordinates
def convert_to_image_coords(lon, lat, image_width=3600, image_height=1800):
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

# Create and save the processed image
def write_image(filename, lat, lon, image_width=3600, image_height=1800):
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
    result_image.save(f'{filename}.png')

    print(f"Processed image saved as {filename}.png")

def reduce_precision(geometry, precision=4):
    def round_coords(coords, precision):
        return [(round(x, precision), round(y, precision)) for x, y in coords]
    
    if isinstance(geometry, Polygon):
        exterior = round_coords(geometry.exterior.coords, precision)
        interiors = [round_coords(interior.coords, precision) for interior in geometry.interiors]
        return Polygon(exterior, interiors)
    elif isinstance(geometry, MultiPolygon):
        # Use the .geoms attribute to iterate over individual polygons in the MultiPolygon
        polygons = [reduce_precision(polygon, precision) for polygon in geometry.geoms]
        return MultiPolygon(polygons)
    else:
        raise ValueError("Unsupported geometry type")

# Main pipeline for image processing and polygon creation
def main(image_path, width=1800, height=900, threshold_value=185):

    # Load the dataset and extract latitude and longitude
    file = 'netcdf_file.nc'
    dataset = xr.open_dataset(file, decode_times=False)

    lon = np.array(dataset['lon']).flatten()
    lat = np.array(dataset['lat']).flatten()

    # Ensure longitude is in the range [-180, 180]
    lon = ((lon + 180) % 360.0) - 180

    # Remove NaNs from lat/lon data
    valid_points = ~np.isnan(lon * lat)
    lon = lon[valid_points]
    lat = lat[valid_points]

    # Create and save the image
    write_image('modis', lat, lon, image_width=width, image_height=height)

    img_th = read_and_threshold_image(image_path, threshold_value)
    img_cleaned = apply_morphological_operations(img_th)

    contours, hierarchy = cv2.findContours(img_cleaned, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    hierarchy = hierarchy[0] if hierarchy is not None else []

    polygon_structure = process_multipolygons(contours, hierarchy, width, height)

    if polygon_structure is not None:
        simplified_polygon = simplify_polygon(polygon_structure)
        simplified_polygon = reduce_precision(simplified_polygon)
        print("WKT of the multipolygon in lon/lat coordinates:")
        print(simplified_polygon.wkt)
    else:
        print("No valid polygons found.")

# Execute the pipeline
main('modis.png', width=3600, height=1800)
