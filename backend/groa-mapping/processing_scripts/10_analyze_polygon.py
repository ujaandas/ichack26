import sys
import os

# Set GDAL environment variable before importing rasterio
os.environ['GDAL_MEM_ENABLE_OPEN'] = 'YES'

import rasterio
from rasterio.warp import transform
from rasterio.features import geometry_mask
from shapely.geometry import Polygon
import numpy as np
import json

# Define paths
current_dir = os.path.dirname(os.path.abspath(__file__))
repo_root = os.path.abspath(os.path.join(current_dir, ".."))
TIF_PATH = os.path.join(repo_root, "data", "sequestration_rate__mean__aboveground__full_extent__Mg_C_ha_yr.tif")

def analyze_polygon(coordinates):
    """
    Analyzes carbon potential within a polygon defined by Lat/Lon coordinates.
    coordinates: List of [Lon, Lat] pairs defining the polygon vertices.
    """
    print(f"Analyzing Polygon with {len(coordinates)} vertices...")
    
    if not os.path.exists(TIF_PATH):
        print(f"Error: TIF file not found at {TIF_PATH}")
        return

    try:
        with rasterio.open(TIF_PATH) as src:
            # 1. Create Shapely Polygon (in Lat/Lon EPSG:4326)
            poly_geo = Polygon(coordinates)
            
            # 2. Transform Polygon to Map CRS if needed
            if src.crs != 'EPSG:4326':
                # Separate x and y
                lons = [c[0] for c in coordinates]
                lats = [c[1] for c in coordinates]
                
                # Transform vertices
                xs, ys = transform('EPSG:4326', src.crs, lons, lats)
                
                # Reconstruct polygon in map projection
                poly_proj = Polygon(list(zip(xs, ys)))
            else:
                poly_proj = poly_geo

            # 3. Create a Window to read only the relevant part of the raster
            # Get bounding box of polygon
            minx, miny, maxx, maxy = poly_proj.bounds
            
            # Convert bounds to pixel indices
            row_start, col_start = src.index(minx, maxy) # Top-Left
            row_stop, col_stop = src.index(maxx, miny)   # Bottom-Right
            
            # Handle bounds checking/clipping
            row_start = max(0, row_start)
            col_start = max(0, col_start)
            row_stop = min(src.height, row_stop + 1) # +1 to include the edge
            col_stop = min(src.width, col_stop + 1)
            
            # Define window
            window = rasterio.windows.Window.from_slices((row_start, row_stop), (col_start, col_stop))
            
            # Read data within window
            data = src.read(1, window=window)
            
            # Get affine transform for the window
            window_transform = src.window_transform(window)
            
            # 4. Create a Mask for the Polygon
            # geometry_mask returns True OUTSIDE the shape, False INSIDE
            # We want False (0) for inside to keep data, True (1) for outside to mask
            mask = geometry_mask(
                [poly_proj],
                out_shape=data.shape,
                transform=window_transform,
                invert=True # Invert so True is inside the polygon
            )
            
            # 5. Extract values within the polygon
            # Apply mask: keep data where mask is True
            values_inside = data[mask]
            
            # Filter out NoData/NaN
            valid_values = values_inside[~np.isnan(values_inside)]
            if src.nodata is not None:
                valid_values = valid_values[valid_values != src.nodata]
            
            if len(valid_values) == 0:
                print("Result: No valid data found within this polygon.")
                return

            # 6. Compute Statistics
            mean_rate = np.mean(valid_values)
            total_pixels = len(valid_values)
            min_rate = np.min(valid_values)
            max_rate = np.max(valid_values)
            std_dev = np.std(valid_values)
            
            # Estimate Area
            # The map is in EPSG:4326 (degrees), so pixel area varies by latitude.
            # We need to calculate the area of the polygon to convert per-hectare rate to total tonnes.
            
            # Project polygon to an equal-area projection (e.g. Mollweide) for accurate area calc
            from shapely.ops import transform as shapely_transform
            import pyproj
            
            # Define projection from WGS84 (Lat/Lon) to Mollweide (Equal Area)
            wgs84 = pyproj.CRS('EPSG:4326')
            mollweide = pyproj.CRS('ESRI:54009')
            project = pyproj.Transformer.from_crs(wgs84, mollweide, always_xy=True).transform
            
            poly_area_m2 = shapely_transform(project, poly_geo).area
            poly_area_ha = poly_area_m2 / 10000.0
            
            # Total Carbon = Mean Rate * Area in Hectares
            total_carbon_yr = mean_rate * poly_area_ha
            
            print("\n" + "="*40)
            print("POLYGON ANALYSIS REPORT")
            print("="*40)
            print(f"Area Analyzed: {poly_area_ha:.2f} hectares")
            print(f"Valid Pixels Analyzed: {total_pixels}")
            print("-" * 40)
            print(f"MEAN RATE (Per Hectare):")
            print(f"  {mean_rate:.4f} Mg C ha-1 yr-1")
            print("-" * 40)
            print(f"TOTAL CARBON POTENTIAL (For this Area):")
            print(f"  {total_carbon_yr:.2f} Mg C yr-1 (Tonnes/Year)")
            print("-" * 40)
            print(f"Statistics (Rate):")
            print(f"  Min: {min_rate:.4f}")
            print(f"  Max: {max_rate:.4f}")
            print(f"  Std Dev: {std_dev:.4f}")
            print("="*40)
            
            # Return dict for integration
            return {
                "total_carbon_yr": float(total_carbon_yr),
                "area_ha": float(poly_area_ha),
                "mean_rate": float(mean_rate),
                "min_rate": float(min_rate),
                "max_rate": float(max_rate),
                "std_dev": float(std_dev),
                "valid_pixels": int(total_pixels)
            }

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Example: A small box around the London point
    # [Lon, Lat]
    example_poly = [
        [-0.40, 51.55], # Bottom-Left
        [-0.30, 51.55], # Bottom-Right
        [-0.30, 51.65], # Top-Right
        [-0.40, 51.65], # Top-Left
        [-0.40, 51.55]  # Close loop
    ]
    
    # Check for command line args (JSON string)
    if len(sys.argv) > 1:
        try:
            input_coords = json.loads(sys.argv[1])
            analyze_polygon(input_coords)
        except json.JSONDecodeError:
            print("Error: Invalid JSON string for coordinates.")
    else:
        print("Running example polygon (London area)...")
        analyze_polygon(example_poly)
