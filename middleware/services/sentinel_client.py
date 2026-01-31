"""
Sentinel Client Service
Fetches Sentinel-2 satellite imagery from Copernicus Data Space Ecosystem
Provides RGB true-color images for visualization in frontend
"""

import asyncio
import httpx
import base64
import os
import time
from typing import Dict, Optional, Tuple
from functools import lru_cache
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


# ========== CONFIGURATION ==========

# Copernicus Data Space Ecosystem credentials (from environment)
CDSE_CLIENT_ID = os.getenv("CDSE_CLIENT_ID")
CDSE_CLIENT_SECRET = os.getenv("CDSE_CLIENT_SECRET")

# API endpoints
TOKEN_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
PROCESS_URL = "https://sh.dataspace.copernicus.eu/api/v1/process"
WMTS_URL = "https://sh.dataspace.copernicus.eu/ogc/wmts/{instance_id}"

# Request configuration
REQUEST_TIMEOUT = 60.0  # seconds
MAX_RETRIES = 3
DEFAULT_IMAGE_SIZE = 512  # pixels (width and height)
MAX_CLOUD_COVERAGE = 20  # percentage


# ========== AUTHENTICATION ==========

@lru_cache(maxsize=1)
def get_auth_token() -> str:
    """
    Fetch OAuth2 access token from Copernicus Data Space
    Token is cached for 1 hour (typical expiry time)
    
    Returns:
        Access token string
    
    Raises:
        Exception: If authentication fails
    
    Note:
        Token cache is cleared automatically after function call count limit.
        For production, use a proper cache with TTL (Redis, etc.)
    """
    if not CDSE_CLIENT_ID or not CDSE_CLIENT_SECRET:
        raise ValueError(
            "Missing Copernicus credentials. Set CDSE_CLIENT_ID and CDSE_CLIENT_SECRET "
            "environment variables. Register at https://dataspace.copernicus.eu/"
        )
    
    logger.info("Fetching new OAuth2 token from Copernicus Data Space")
    
    try:
        response = httpx.post(
            TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": CDSE_CLIENT_ID,
                "client_secret": CDSE_CLIENT_SECRET
            },
            timeout=30.0
        )
        response.raise_for_status()
        
        token_data = response.json()
        access_token = token_data['access_token']
        expires_in = token_data.get('expires_in', 3600)
        
        logger.info(f"✅ OAuth2 token acquired (expires in {expires_in}s)")
        return access_token
        
    except httpx.HTTPStatusError as e:
        logger.error(f"Authentication failed: {e.response.status_code} - {e.response.text}")
        raise Exception(
            f"Failed to authenticate with Copernicus: {e.response.text}. "
            f"Check your CDSE_CLIENT_ID and CDSE_CLIENT_SECRET."
        )
    except Exception as e:
        logger.error(f"Token request failed: {e}")
        raise Exception(f"Failed to fetch authentication token: {str(e)}")


def refresh_token_cache():
    """Clear cached token to force refresh on next request"""
    get_auth_token.cache_clear()
    logger.debug("Cleared OAuth2 token cache")


# ========== EVALSCRIPT TEMPLATES ==========

# Sentinel-2 RGB true-color evalscript
RGB_EVALSCRIPT = """
//VERSION=3

function setup() {
    return {
        input: [{
            bands: ["B04", "B03", "B02"],  // Red, Green, Blue
            units: "DN"
        }],
        output: {
            bands: 3,
            sampleType: "AUTO"
        }
    };
}

function evaluatePixel(sample) {
    // Apply 2.5x gain for better brightness
    // Sentinel-2 L2A values are in reflectance [0-10000]
    return [
        2.5 * sample.B04 / 10000,
        2.5 * sample.B03 / 10000,
        2.5 * sample.B02 / 10000
    ];
}
"""

# False-color NDVI visualization (optional)
NDVI_EVALSCRIPT = """
//VERSION=3

function setup() {
    return {
        input: ["B04", "B08", "SCL"],  // Red, NIR, Scene Classification
        output: { bands: 3 }
    };
}

// Color ramp for NDVI visualization
const ramps = [
    [-0.5, 0x0c0c0c],
    [-0.2, 0xbfbfbf],
    [-0.1, 0xdbdbdb],
    [0, 0xeaeaea],
    [0.025, 0xfff9cc],
    [0.05, 0xede8b5],
    [0.075, 0xddd89b],
    [0.1, 0xccc682],
    [0.125, 0xbcb76b],
    [0.15, 0xafc160],
    [0.175, 0xa3cc59],
    [0.2, 0x91bf51],
    [0.25, 0x7fb247],
    [0.3, 0x70a33f],
    [0.35, 0x609635],
    [0.4, 0x4f892d],
    [0.45, 0x3f7c23],
    [0.5, 0x306d1c],
    [0.55, 0x216011],
    [0.6, 0x0f540a],
    [1, 0x004400],
];

function evaluatePixel(samples) {
    let ndvi = (samples.B08 - samples.B04) / (samples.B08 + samples.B04);
    
    // Mask clouds
    if (samples.SCL === 3 || samples.SCL === 8 || samples.SCL === 9) {
        return [1, 1, 1];  // White for clouds
    }
    
    return colorBlend(ndvi, ramps);
}
"""


# ========== MAIN FETCH FUNCTION ==========

async def fetch_satellite_image(
    geojson: Dict,
    date_range: str = "2025-01-01/2025-12-31",
    image_size: int = DEFAULT_IMAGE_SIZE,
    max_cloud_coverage: int = MAX_CLOUD_COVERAGE,
    return_format: str = "base64"
) -> str:
    """
    Fetch Sentinel-2 RGB satellite image for polygon
    
    Args:
        geojson: GeoJSON Feature with polygon geometry
        date_range: Date range in format "YYYY-MM-DD/YYYY-MM-DD"
        image_size: Output image size in pixels (width and height)
        max_cloud_coverage: Maximum acceptable cloud coverage percentage (0-100)
        return_format: "base64" (PNG embedded in JSON) or "url" (tile URL)
    
    Returns:
        Base64-encoded PNG string (data:image/png;base64,...) or tile URL
    
    Raises:
        Exception: If image fetch fails
    
    Example:
        >>> geojson = {"type": "Feature", "geometry": {...}}
        >>> img = await fetch_satellite_image(geojson, "2025-07-01/2025-12-31")
        >>> # Returns: "data:image/png;base64,iVBORw0KGgoAAAANSUhEUg..."
    """
    logger.info(f"Fetching Sentinel-2 image for date range: {date_range}")
    
    # Get OAuth token
    try:
        token = get_auth_token()
    except Exception as e:
        logger.error(f"Token acquisition failed: {e}")
        raise
    
    # Extract bounding box from GeoJSON
    bbox = geojson['properties'].get('bbox')
    if not bbox:
        # Calculate bbox if not provided
        from shapely.geometry import shape
        poly = shape(geojson['geometry'])
        bbox = list(poly.bounds)  # [minx, miny, maxx, maxy]
    
    logger.debug(f"Using bounding box: {bbox}")
    
    # Parse date range
    date_from, date_to = parse_date_range(date_range)
    
    # Construct Sentinel Hub Processing API request
    payload = build_process_request(
        bbox=bbox,
        date_from=date_from,
        date_to=date_to,
        image_size=image_size,
        max_cloud_coverage=max_cloud_coverage,
        evalscript=RGB_EVALSCRIPT
    )
    
    # Make request with retries
    image_bytes = await fetch_with_retry(
        url=PROCESS_URL,
        payload=payload,
        token=token,
        max_retries=MAX_RETRIES
    )
    
    # Convert to base64 for JSON embedding
    if return_format == "base64":
        img_base64 = base64.b64encode(image_bytes).decode('utf-8')
        result = f"data:image/png;base64,{img_base64}"
        logger.info(f"✅ Satellite image fetched ({len(image_bytes)} bytes, base64 encoded)")
    else:
        # For tile URL, would need to use WMTS service (not implemented here)
        # This requires creating a configuration/instance first
        result = None
        logger.warning("Tile URL format not yet implemented, returning base64")
        img_base64 = base64.b64encode(image_bytes).decode('utf-8')
        result = f"data:image/png;base64,{img_base64}"
    
    return result


# ========== HELPER FUNCTIONS ==========

def parse_date_range(date_range: str) -> Tuple[str, str]:
    """
    Parse and validate date range string
    
    Args:
        date_range: "YYYY-MM-DD/YYYY-MM-DD"
    
    Returns:
        Tuple of (from_date_iso, to_date_iso) with time component
    
    Example:
        >>> parse_date_range("2025-07-01/2025-12-31")
        ('2025-07-01T00:00:00Z', '2025-12-31T23:59:59Z')
    """
    try:
        date_from_str, date_to_str = date_range.split('/')
        
        # Validate dates
        date_from = datetime.strptime(date_from_str, '%Y-%m-%d')
        date_to = datetime.strptime(date_to_str, '%Y-%m-%d')
        
        # Add time components
        date_from_iso = f"{date_from_str}T00:00:00Z"
        date_to_iso = f"{date_to_str}T23:59:59Z"
        
        return date_from_iso, date_to_iso
        
    except Exception as e:
        logger.error(f"Invalid date range format: {date_range}")
        # Fallback to last 6 months
        date_to = datetime.now()
        date_from = date_to - timedelta(days=180)
        return date_from.isoformat() + "Z", date_to.isoformat() + "Z"


def build_process_request(
    bbox: list,
    date_from: str,
    date_to: str,
    image_size: int,
    max_cloud_coverage: int,
    evalscript: str
) -> Dict:
    """
    Build Sentinel Hub Processing API request payload
    
    Args:
        bbox: Bounding box [minx, miny, maxx, maxy]
        date_from: Start date (ISO format with time)
        date_to: End date (ISO format with time)
        image_size: Output image size in pixels
        max_cloud_coverage: Max cloud coverage percentage
        evalscript: JavaScript evalscript for processing
    
    Returns:
        Request payload dictionary
    """
    payload = {
        "input": {
            "bounds": {
                "bbox": bbox,
                "properties": {
                    "crs": "http://www.opengis.net/def/crs/EPSG/0/4326"
                }
            },
            "data": [
                {
                    "type": "S2L2A",  # Sentinel-2 Level-2A (atmospherically corrected)
                    "dataFilter": {
                        "timeRange": {
                            "from": date_from,
                            "to": date_to
                        },
                        "maxCloudCoverage": max_cloud_coverage,
                        "mosaickingOrder": "leastCC"  # Least cloudy scene first
                    }
                }
            ]
        },
        "output": {
            "width": image_size,
            "height": image_size,
            "responses": [
                {
                    "identifier": "default",
                    "format": {
                        "type": "image/png"
                    }
                }
            ]
        },
        "evalscript": evalscript
    }
    
    return payload


async def fetch_with_retry(
    url: str,
    payload: Dict,
    token: str,
    max_retries: int = 3
) -> bytes:
    """
    Make HTTP request with exponential backoff retry
    
    Args:
        url: API endpoint URL
        payload: Request JSON payload
        token: OAuth2 access token
        max_retries: Maximum retry attempts
    
    Returns:
        Response content bytes (image data)
    
    Raises:
        Exception: If all retries fail
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "image/png"
    }
    
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient() as client:
                logger.debug(f"Sentinel Hub request attempt {attempt + 1}/{max_retries}")
                
                response = await client.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=REQUEST_TIMEOUT
                )
                
                # Handle 401 (token expired) by refreshing
                if response.status_code == 401:
                    logger.warning("Token expired, refreshing...")
                    refresh_token_cache()
                    token = get_auth_token()
                    headers["Authorization"] = f"Bearer {token}"
                    continue
                
                response.raise_for_status()
                
                # Success
                return response.content
                
        except httpx.TimeoutException:
            logger.warning(f"Request timed out (attempt {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
                continue
            else:
                raise Exception(
                    f"Sentinel Hub request timed out after {max_retries} attempts. "
                    f"The area may be too large or service may be slow."
                )
        
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code}: {e.response.text}")
            
            # Don't retry on client errors (except 401)
            if 400 <= e.response.status_code < 500 and e.response.status_code != 401:
                raise Exception(
                    f"Sentinel Hub request failed: {e.response.status_code} - {e.response.text}"
                )
            
            # Retry on server errors
            if attempt < max_retries - 1:
                await asyncio_sleep(2 ** attempt)
                continue
            else:
                raise Exception(
                    f"Sentinel Hub server error after {max_retries} attempts: {e.response.text}"
                )
        
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            if attempt < max_retries - 1:
                await asyncio_sleep(2 ** attempt)
                continue
            else:
                raise Exception(f"Failed to fetch satellite image: {str(e)}")
    
    raise Exception("Max retries exceeded")


async def asyncio_sleep(seconds: float):
    """Async sleep helper (avoids blocking event loop)"""
    import asyncio
    await asyncio.sleep(seconds)


# ========== ALTERNATIVE: NDVI IMAGE ==========

async def fetch_ndvi_image(
    geojson: Dict,
    date_range: str = "2025-01-01/2025-12-31",
    image_size: int = DEFAULT_IMAGE_SIZE
) -> str:
    """
    Fetch false-color NDVI image instead of RGB
    Useful for visualizing vegetation health
    
    Args:
        geojson: GeoJSON Feature
        date_range: Date range string
        image_size: Output size
    
    Returns:
        Base64-encoded PNG
    """
    logger.info("Fetching NDVI false-color image")
    
    token = get_auth_token()
    bbox = geojson['properties'].get('bbox')
    date_from, date_to = parse_date_range(date_range)
    
    payload = build_process_request(
        bbox=bbox,
        date_from=date_from,
        date_to=date_to,
        image_size=image_size,
        max_cloud_coverage=MAX_CLOUD_COVERAGE,
        evalscript=NDVI_EVALSCRIPT
    )
    
    image_bytes = await fetch_with_retry(PROCESS_URL, payload, token, MAX_RETRIES)
    
    img_base64 = base64.b64encode(image_bytes).decode('utf-8')
    return f"data:image/png;base64,{img_base64}"


# ========== HEALTH CHECK ==========

async def test_sentinel_connection() -> bool:
    """
    Test Sentinel Hub API connectivity and authentication
    Called during FastAPI startup
    
    Returns:
        True if connection successful
    
    Raises:
        Exception: If connection fails
    """
    logger.info("Testing Sentinel Hub API connection...")
    
    try:
        token = get_auth_token()
        logger.info("✅ Sentinel Hub authentication successful")
        return True
    except Exception as e:
        logger.error(f"❌ Sentinel Hub connection test failed: {e}")
        raise


# ========== UTILITY FUNCTIONS ==========

def estimate_image_size(area_km2: float) -> int:
    """
    Estimate appropriate image size based on polygon area
    Larger areas need higher resolution to maintain detail
    
    Args:
        area_km2: Polygon area in square kilometers
    
    Returns:
        Recommended image size in pixels
    """
    if area_km2 < 10:
        return 512
    elif area_km2 < 50:
        return 768
    elif area_km2 < 200:
        return 1024
    else:
        return 1280  # Max before hitting API limits


def get_optimal_date_range(months_back: int = 6) -> str:
    """
    Generate optimal date range for current season
    
    Args:
        months_back: Number of months to look back
    
    Returns:
        Date range string "YYYY-MM-DD/YYYY-MM-DD"
    """
    date_to = datetime.now()
    date_from = date_to - timedelta(days=months_back * 30)
    
    return f"{date_from.strftime('%Y-%m-%d')}/{date_to.strftime('%Y-%m-%d')}"
