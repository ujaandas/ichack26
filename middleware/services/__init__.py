"""
Services Package
External API integrations and data transformation services

Modules:
- coordinate_parser: Convert frontend coordinates to GeoJSON
- sentinel_client: Fetch satellite imagery from Copernicus Sentinel Hub
- backend_client: Communicate with /backend RUSLE computation service
"""

from .coordinate_parser import (
    parse_to_geojson,
    calculate_geodesic_area,
    geojson_to_ee_geometry
)

from .sentinel_client import (
    fetch_satellite_image,
    get_auth_token
)

from .backend_client import (
    call_backend_rusle,
    test_backend_connection
)


# Public API - explicitly define what can be imported with `from services import *`
__all__ = [
    # Coordinate parsing
    'parse_to_geojson',
    'calculate_geodesic_area',
    'geojson_to_ee_geometry',
    
    # Satellite imagery
    'fetch_satellite_image',
    'get_auth_token',
    
    # Backend communication
    'call_backend_rusle',
    'test_backend_connection',
]


# Package metadata
__version__ = '1.0.0'
__author__ = 'RUSLE Team'
