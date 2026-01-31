import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, Mock
import os
import sys

# Add parent directory to Python path so we can import main, schemas, etc.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Set test environment variables BEFORE importing app
os.environ["BACKEND_URL"] = "http://test-backend:8001"
os.environ["CDSE_CLIENT_ID"] = "test_client_id"
os.environ["CDSE_CLIENT_SECRET"] = "test_client_secret"
os.environ["FRONTEND_URL"] = "*"
os.environ["ENABLE_AUTH"] = "false"
os.environ["ENV"] = "test"

# NOW import after path is set and env configured
from main import app
import schemas

# ========== TEST CLIENT ==========

@pytest.fixture
def client():
    """FastAPI test client"""
    with TestClient(app) as c:
        yield c

# ========== COORDINATE FIXTURES ==========

@pytest.fixture
def valid_coordinates():
    """Valid polygon coordinates (London area)"""
    return [
        schemas.Coordinate(longitude=0.28, latitude=51.50),
        schemas.Coordinate(longitude=0.19, latitude=51.50),
        schemas.Coordinate(longitude=0.39, latitude=51.52),
        schemas.Coordinate(longitude=0.28, latitude=51.52),
        schemas.Coordinate(longitude=0.28, latitude=51.50)  # Closed
    ]

@pytest.fixture
def valid_coordinates_open():
    """Valid polygon coordinates (not closed)"""
    return [
        schemas.Coordinate(longitude=0.28, latitude=51.50),
        schemas.Coordinate(longitude=0.19, latitude=51.50),
        schemas.Coordinate(longitude=0.39, latitude=51.52),
        schemas.Coordinate(longitude=0.28, latitude=51.52)
    ]

@pytest.fixture
def small_valid_coordinates():
    """Small valid polygon (just above minimum area)"""
    return [
        schemas.Coordinate(longitude=0.0, latitude=0.0),
        schemas.Coordinate(longitude=0.015, latitude=0.0),
        schemas.Coordinate(longitude=0.015, latitude=0.015),
        schemas.Coordinate(longitude=0.0, latitude=0.015),
        schemas.Coordinate(longitude=0.0, latitude=0.0)
    ]

@pytest.fixture
def invalid_coordinates_too_few():
    """Invalid: only 2 points"""
    return [
        schemas.Coordinate(longitude=0.0, latitude=0.0),
        schemas.Coordinate(longitude=1.0, latitude=1.0)
    ]

@pytest.fixture
def invalid_coordinates_out_of_range():
    """Invalid: longitude out of range"""
    return [
        schemas.Coordinate(longitude=200.0, latitude=0.0),
        schemas.Coordinate(longitude=0.0, latitude=0.0),
        schemas.Coordinate(longitude=1.0, latitude=1.0),
        schemas.Coordinate(longitude=200.0, latitude=0.0)
    ]

@pytest.fixture
def invalid_coordinates_self_intersecting():
    """Invalid: self-intersecting polygon (bow-tie)"""
    return [
        schemas.Coordinate(longitude=0.0, latitude=0.0),
        schemas.Coordinate(longitude=1.0, latitude=1.0),
        schemas.Coordinate(longitude=1.0, latitude=0.0),
        schemas.Coordinate(longitude=0.0, latitude=1.0),
        schemas.Coordinate(longitude=0.0, latitude=0.0)
    ]

@pytest.fixture
def invalid_coordinates_collinear():
    """Invalid: all points on same line (no area)"""
    return [
        schemas.Coordinate(longitude=0.0, latitude=0.0),
        schemas.Coordinate(longitude=1.0, latitude=1.0),
        schemas.Coordinate(longitude=2.0, latitude=2.0),
        schemas.Coordinate(longitude=0.0, latitude=0.0)
    ]

# ========== REQUEST PAYLOAD FIXTURES ==========

@pytest.fixture
def valid_request_payload(valid_coordinates):
    """Valid complete RUSLE request payload"""
    return {
        "coordinates": [c.dict() for c in valid_coordinates],
        "options": {
            "p_toggle": False,
            "threshold_t_ha_yr": 20.0,
            "compute_sensitivities": True,
            "date_range": "2025-01-01/2025-12-31"
        }
    }

@pytest.fixture
def minimal_request_payload(valid_coordinates):
    """Minimal request (coordinates only, default options)"""
    return {
        "coordinates": [c.dict() for c in valid_coordinates]
    }

# ========== MOCK SERVICE RESPONSES ==========

@pytest.fixture
def mock_backend_response():
    """Mock response from backend RUSLE/ML service"""
    return {
        "erosion": {
            "mean": 12.4,
            "max": 45.2,
            "min": 0.3,
            "stddev": 8.7,
            "p50": 9.1,
            "p95": 28.3,
            "p99": 38.5,
            "unit": "t/ha/yr"
        },
        "factors": {
            "R": {
                "mean": 1850.5,
                "stddev": 120.3,
                "min": 1620.0,
                "max": 2100.0,
                "unit": "MJ mm ha⁻¹ h⁻¹ yr⁻¹",
                "source": "CHIRPS"
            },
            "K": {
                "mean": 0.028,
                "stddev": 0.005,
                "min": 0.020,
                "max": 0.035,
                "unit": "t ha h ha⁻¹ MJ⁻¹ mm⁻¹",
                "source": "SoilGrids"
            },
            "LS": {
                "mean": 4.2,
                "stddev": 2.1,
                "min": 0.5,
                "max": 12.8,
                "unit": "dimensionless",
                "source": "SRTM 30m"
            },
            "C": {
                "mean": 0.08,
                "stddev": 0.04,
                "min": 0.01,
                "max": 0.25,
                "unit": "dimensionless",
                "source": "ESA WorldCover + Sentinel-2 NDVI"
            },
            "P": {
                "mean": 1.0,
                "stddev": 0.0,
                "min": 1.0,
                "max": 1.0,
                "unit": "dimensionless",
                "source": "User configuration"
            }
        },
        "validation": {
            "high_veg_reduction_pct": 68.2,
            "flat_terrain_reduction_pct": 85.1,
            "bare_soil_increase_pct": 230.5,
            "model_valid": True,
            "notes": "All sanity checks passed"
        },
        "hotspots": [
            {
                "id": "hotspot_1",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[0.25, 51.51], [0.26, 51.51], [0.26, 51.52], [0.25, 51.52], [0.25, 51.51]]]
                },
                "properties": {
                    "area_ha": 3.2,
                    "mean_erosion": 38.5,
                    "max_erosion": 52.1,
                    "dominant_factor": "LS"
                },
                "reason": "Steep slope (LS > 10) + Low vegetation cover (C > 0.15)",
                "severity": "high",
                "confidence": 0.89
            }
        ],
        "summary": {
            "total_hotspots": 1,
            "total_high_risk_area_ha": 3.2,
            "severity_distribution": {
                "low": 0,
                "moderate": 0,
                "high": 1,
                "critical": 0
            },
            "dominant_factors": ["LS", "C"]
        },
        "tile_urls": {
            "erosion_risk": "https://earthengine.googleapis.com/v1/test/tiles",
            "factors": {
                "R": "https://earthengine.googleapis.com/v1/test/tiles/R",
                "LS": "https://earthengine.googleapis.com/v1/test/tiles/LS"
            }
        }
    }

@pytest.fixture
def mock_satellite_image():
    """Mock base64 satellite image response"""
    return "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

@pytest.fixture
def mock_geojson():
    """Mock GeoJSON polygon"""
    return {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[0.28, 51.50], [0.19, 51.50], [0.39, 51.52], [0.28, 51.52], [0.28, 51.50]]]
        },
        "properties": {
            "area_km2": 25.34,
            "area_hectares": 2534.0,
            "centroid": [0.29, 51.51],
            "bbox": [0.19, 51.50, 0.39, 51.52],
            "num_vertices": 5,
            "perimeter_km": 22.5
        }
    }

# ========== VALIDATION METADATA FIXTURES ==========

@pytest.fixture
def mock_validation_metadata():
    """Mock polygon validation metadata"""
    return {
        "valid": True,
        "area_km2": 25.34,
        "area_hectares": 2534.0,
        "centroid": [0.29, 51.51],
        "bbox": [0.19, 51.50, 0.39, 51.52],
        "num_vertices": 5,
        "perimeter_km": 22.5
    }

# ========== MOCK ASYNC FUNCTIONS ==========

@pytest.fixture
def mock_async_backend_call(mock_backend_response):
    """AsyncMock for backend_client.call_backend_rusle"""
    mock = AsyncMock(return_value=mock_backend_response)
    return mock

@pytest.fixture
def mock_async_sentinel_call(mock_satellite_image):
    """AsyncMock for sentinel_client.fetch_satellite_image"""
    mock = AsyncMock(return_value=mock_satellite_image)
    return mock

# ========== ERROR RESPONSE FIXTURES ==========

@pytest.fixture
def backend_timeout_response():
    """Mock backend timeout error"""
    return {
        "error": "TimeoutError",
        "detail": "Backend computation timed out after 120s"
    }

@pytest.fixture
def backend_error_response():
    """Mock backend service error"""
    return {
        "error": "BackendError",
        "detail": "RUSLE service error (500): Internal computation failed"
    }

# ========== PYTEST CONFIGURATION ==========

def pytest_configure(config):
    """Configure pytest"""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test requiring external services"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )

@pytest.fixture(autouse=True)
def reset_environment():
    """Reset environment variables after each test"""
    original_env = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(original_env)
