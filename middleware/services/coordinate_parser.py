"""
Coordinate Parser Service
Converts frontend coordinate arrays to GeoJSON format for backend/GEE processing
Handles buffering, area calculation, and coordinate transformations
"""

from shapely.geometry import Polygon, Point, mapping, shape
from shapely.ops import transform
from pyproj import Geod, Transformer
from typing import List, Dict, Tuple, Optional
import logging
import json

import schemas  # Import Coordinate model

logger = logging.getLogger(__name__)


# ========== CONFIGURATION ==========

# Default buffer in degrees (~1.1 km at equator for 0.01°)
DEFAULT_BUFFER_DEG = 0.01

# Geodesic calculator (WGS84 ellipsoid)
GEOD = Geod(ellps="WGS84")


# ========== CORE FUNCTIONS ==========

def parse_to_geojson(
    coords: List[schemas.Coordinate],
    buffer_deg: float = DEFAULT_BUFFER_DEG,
    include_properties: bool = True
) -> Dict:
    """
    Convert coordinate list to GeoJSON Feature with optional buffer
    
    The buffer ensures raster edge pixels are fully covered during GEE processing.
    Without buffer, edge pixels may be partially clipped leading to data loss.
    
    Args:
        coords: List of Coordinate objects from API request
        buffer_deg: Buffer distance in degrees (default 0.01° ≈ 1.1 km at equator)
        include_properties: Whether to calculate and include metadata properties
    
    Returns:
        GeoJSON Feature dict:
        {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[lon1, lat1], [lon2, lat2], ...]]
            },
            "properties": {
                "area_km2": 25.3,
                "centroid": [lon, lat],
                "bbox": [minx, miny, maxx, maxy],
                ...
            }
        }
    
    Example:
        >>> coords = [
        ...     Coordinate(longitude=0.28, latitude=51.50),
        ...     Coordinate(longitude=0.19, latitude=51.50),
        ...     Coordinate(longitude=0.39, latitude=51.52)
        ... ]
        >>> geojson = parse_to_geojson(coords)
        >>> print(geojson['properties']['area_km2'])
        25.3
    """
    logger.info(f"Parsing {len(coords)} coordinates to GeoJSON with {buffer_deg}° buffer")
    
    # Step 1: Extract lon/lat pairs (ignore height for 2D RUSLE)
    points = [(c.longitude, c.latitude) for c in coords]
    
    # Step 2: Create Shapely polygon
    try:
        poly = Polygon(points)
    except Exception as e:
        logger.error(f"Failed to create polygon: {e}")
        raise ValueError(f"Cannot create polygon from coordinates: {str(e)}")
    
    # Step 3: Apply buffer if specified
    if buffer_deg > 0:
        buffered_poly = poly.buffer(buffer_deg)
        logger.debug(f"Applied {buffer_deg}° buffer to polygon")
    else:
        buffered_poly = poly
    
    # Step 4: Convert to GeoJSON geometry
    geometry = mapping(buffered_poly)
    
    # Step 5: Calculate properties (metadata)
    properties = {}
    if include_properties:
        properties = calculate_polygon_properties(buffered_poly, buffer_deg)
    
    # Step 6: Construct GeoJSON Feature
    geojson = {
        "type": "Feature",
        "geometry": geometry,
        "properties": properties
    }
    
    logger.info(
        f"GeoJSON created: {properties.get('area_km2', 0):.2f} km², "
        f"{properties.get('num_vertices', 0)} vertices"
    )
    
    return geojson


def calculate_polygon_properties(poly: Polygon, buffer_applied: float = 0) -> Dict:
    """
    Calculate metadata properties for a polygon
    Includes area, centroid, bounding box, perimeter, etc.
    
    Args:
        poly: Shapely Polygon object
        buffer_applied: Buffer distance applied (for metadata)
    
    Returns:
        Dictionary of polygon properties
    """
    # Calculate geodesic area (accounts for Earth curvature)
    area_km2 = calculate_geodesic_area(poly)
    
    # Calculate perimeter
    area_m2, perimeter_m = GEOD.geometry_area_perimeter(poly)
    
    # Get centroid
    centroid = poly.centroid
    
    # Get bounding box
    minx, miny, maxx, maxy = poly.bounds
    
    # Count vertices
    num_vertices = len(poly.exterior.coords)
    
    properties = {
        # Area metrics
        "area_km2": round(area_km2, 4),
        "area_hectares": round(area_km2 * 100, 2),
        "area_m2": round(abs(area_m2), 2),
        
        # Perimeter
        "perimeter_km": round(perimeter_m / 1000, 3),
        "perimeter_m": round(perimeter_m, 2),
        
        # Centroid [longitude, latitude]
        "centroid": [round(centroid.x, 6), round(centroid.y, 6)],
        
        # Bounding box [minx, miny, maxx, maxy]
        "bbox": [round(minx, 6), round(miny, 6), round(maxx, 6), round(maxy, 6)],
        
        # Geometry info
        "num_vertices": num_vertices,
        "buffer_applied_deg": buffer_applied,
        "buffer_applied_km": round(buffer_applied * 111.32, 2),  # Approx km at equator
        
        # Coordinate reference system
        "crs": "EPSG:4326"  # WGS84
    }
    
    return properties


def calculate_geodesic_area(poly: Polygon) -> float:
    """
    Calculate accurate polygon area accounting for Earth's curvature
    Uses WGS84 ellipsoid model for geodesic calculations
    
    Args:
        poly: Shapely Polygon object
    
    Returns:
        Area in square kilometers
    
    Note:
        Simple poly.area gives planar area in degrees², which is inaccurate.
        Geodesic area accounts for meridian convergence and Earth's spheroid shape.
    """
    try:
        area_m2, _ = GEOD.geometry_area_perimeter(poly)
        area_km2 = abs(area_m2) / 1_000_000
        return area_km2
    except Exception as e:
        logger.warning(f"Geodesic area calculation failed, using planar fallback: {e}")
        # Fallback: rough approximation (inaccurate but better than crashing)
        return abs(poly.area) * 111.32 * 111.32  # Rough deg² to km² conversion


# ========== GEOMETRY CONVERSION FUNCTIONS ==========

def geojson_to_shapely(geojson: Dict) -> Polygon:
    """
    Convert GeoJSON geometry to Shapely Polygon
    
    Args:
        geojson: GeoJSON Feature or Geometry dict
    
    Returns:
        Shapely Polygon object
    
    Example:
        >>> geojson = {"type": "Feature", "geometry": {...}}
        >>> poly = geojson_to_shapely(geojson)
    """
    # Handle both Feature and Geometry input
    if geojson.get('type') == 'Feature':
        geometry = geojson['geometry']
    else:
        geometry = geojson
    
    return shape(geometry)


def geojson_to_ee_geometry(geojson: Dict):
    """
    Convert GeoJSON to Earth Engine Geometry object
    Used when passing polygons to backend/GEE
    
    Args:
        geojson: GeoJSON Feature or Geometry dict
    
    Returns:
        ee.Geometry object (requires earthengine-api installed in backend)
    
    Note:
        This is a helper for backend_client.py - actual ee import happens in /backend
        FastAPI doesn't need earthengine-api installed
    """
    # Extract geometry if Feature provided
    if geojson.get('type') == 'Feature':
        geometry = geojson['geometry']
    else:
        geometry = geojson
    
    # Return raw geometry dict - backend will convert to ee.Geometry
    return geometry


def coords_to_bbox(coords: List[schemas.Coordinate]) -> List[float]:
    """
    Extract bounding box from coordinate list
    
    Args:
        coords: List of Coordinate objects
    
    Returns:
        Bounding box [minx, miny, maxx, maxy]
    """
    lons = [c.longitude for c in coords]
    lats = [c.latitude for c in coords]
    
    return [min(lons), min(lats), max(lons), max(lats)]


def bbox_to_geojson(bbox: List[float], buffer_deg: float = 0) -> Dict:
    """
    Convert bounding box to GeoJSON polygon Feature
    Useful if frontend sends bbox instead of full polygon
    
    Args:
        bbox: Bounding box [minx, miny, maxx, maxy]
        buffer_deg: Optional buffer to apply
    
    Returns:
        GeoJSON Feature dict
    """
    minx, miny, maxx, maxy = bbox
    
    # Create rectangle polygon from bbox
    poly = Polygon([
        (minx, miny),
        (maxx, miny),
        (maxx, maxy),
        (minx, maxy),
        (minx, miny)  # Close polygon
    ])
    
    # Apply buffer if specified
    if buffer_deg > 0:
        poly = poly.buffer(buffer_deg)
    
    return {
        "type": "Feature",
        "geometry": mapping(poly),
        "properties": calculate_polygon_properties(poly, buffer_deg)
    }


# ========== COORDINATE TRANSFORMATION ==========

def transform_coordinates(
    coords: List[schemas.Coordinate],
    from_crs: str = "EPSG:4326",
    to_crs: str = "EPSG:3857"
) -> List[Tuple[float, float]]:
    """
    Transform coordinates between coordinate reference systems
    
    Args:
        coords: List of Coordinate objects
        from_crs: Source CRS (default: WGS84)
        to_crs: Target CRS (default: Web Mercator)
    
    Returns:
        List of transformed (x, y) tuples
    
    Example:
        >>> # Transform WGS84 to Web Mercator (for web mapping)
        >>> coords = [Coordinate(longitude=0, latitude=51.5)]
        >>> transformed = transform_coordinates(coords, "EPSG:4326", "EPSG:3857")
    """
    transformer = Transformer.from_crs(from_crs, to_crs, always_xy=True)
    
    transformed = []
    for coord in coords:
        x, y = transformer.transform(coord.longitude, coord.latitude)
        transformed.append((x, y))
    
    logger.debug(f"Transformed {len(coords)} coordinates from {from_crs} to {to_crs}")
    return transformed


def add_buffer_meters(poly: Polygon, buffer_meters: float) -> Polygon:
    """
    Add buffer in meters (instead of degrees) using equal-area projection
    More accurate than degree-based buffer for large areas or high latitudes
    
    Args:
        poly: Shapely Polygon in WGS84
        buffer_meters: Buffer distance in meters
    
    Returns:
        Buffered polygon in WGS84
    """
    # Get polygon centroid for choosing appropriate UTM zone
    centroid = poly.centroid
    lon, lat = centroid.x, centroid.y
    
    # Calculate UTM zone
    utm_zone = int((lon + 180) / 6) + 1
    utm_crs = f"EPSG:326{utm_zone}" if lat >= 0 else f"EPSG:327{utm_zone}"
    
    # Transform to UTM, buffer, transform back
    project_to_utm = Transformer.from_crs("EPSG:4326", utm_crs, always_xy=True).transform
    project_to_wgs84 = Transformer.from_crs(utm_crs, "EPSG:4326", always_xy=True).transform
    
    poly_utm = transform(project_to_utm, poly)
    buffered_utm = poly_utm.buffer(buffer_meters)
    buffered_wgs84 = transform(project_to_wgs84, buffered_utm)
    
    logger.debug(f"Applied {buffer_meters}m buffer using {utm_crs}")
    return buffered_wgs84


# ========== VALIDATION HELPERS ==========

def ensure_counterclockwise(coords: List[schemas.Coordinate]) -> List[schemas.Coordinate]:
    """
    Ensure polygon vertices are in counter-clockwise order (GeoJSON standard)
    
    Args:
        coords: List of Coordinate objects
    
    Returns:
        Reordered coordinates if needed
    """
    points = [(c.longitude, c.latitude) for c in coords]
    poly = Polygon(points)
    
    # Check orientation using signed area
    if not poly.exterior.is_ccw:
        logger.debug("Reversing polygon vertex order to counter-clockwise")
        coords = list(reversed(coords))
    
    return coords


def simplify_polygon_coords(
    coords: List[schemas.Coordinate],
    tolerance_deg: float = 0.0001
) -> List[schemas.Coordinate]:
    """
    Simplify polygon to reduce vertex count (Douglas-Peucker algorithm)
    
    Args:
        coords: List of Coordinate objects
        tolerance_deg: Simplification tolerance in degrees (0.0001 ≈ 11m)
    
    Returns:
        Simplified coordinate list
    """
    points = [(c.longitude, c.latitude) for c in coords]
    poly = Polygon(points)
    
    simplified_poly = poly.simplify(tolerance_deg, preserve_topology=True)
    
    # Convert back to Coordinate objects
    simplified_coords = [
        schemas.Coordinate(longitude=x, latitude=y)
        for x, y in simplified_poly.exterior.coords
    ]
    
    logger.debug(
        f"Simplified polygon from {len(coords)} to {len(simplified_coords)} vertices "
        f"(tolerance={tolerance_deg}°)"
    )
    
    return simplified_coords


# ========== EXPORT FUNCTIONS ==========

def geojson_to_string(geojson: Dict, pretty: bool = False) -> str:
    """
    Convert GeoJSON dict to JSON string
    
    Args:
        geojson: GeoJSON Feature dict
        pretty: Whether to format with indentation
    
    Returns:
        JSON string
    """
    if pretty:
        return json.dumps(geojson, indent=2)
    else:
        return json.dumps(geojson)


def save_geojson(geojson: Dict, filepath: str):
    """
    Save GeoJSON to file
    
    Args:
        geojson: GeoJSON Feature dict
        filepath: Output file path
    """
    with open(filepath, 'w') as f:
        json.dump(geojson, f, indent=2)
    
    logger.info(f"Saved GeoJSON to {filepath}")


# ========== DEBUGGING HELPERS ==========

def print_polygon_info(geojson: Dict):
    """
    Print polygon information for debugging
    
    Args:
        geojson: GeoJSON Feature dict
    """
    props = geojson.get('properties', {})
    
    print("\n" + "="*50)
    print("POLYGON INFORMATION")
    print("="*50)
    print(f"Area: {props.get('area_km2', 0):.2f} km² ({props.get('area_hectares', 0):.2f} ha)")
    print(f"Perimeter: {props.get('perimeter_km', 0):.2f} km")
    print(f"Centroid: {props.get('centroid', [])}")
    print(f"Bounding Box: {props.get('bbox', [])}")
    print(f"Vertices: {props.get('num_vertices', 0)}")
    print(f"Buffer Applied: {props.get('buffer_applied_deg', 0):.4f}° "
          f"(~{props.get('buffer_applied_km', 0):.2f} km)")
    print("="*50 + "\n")
