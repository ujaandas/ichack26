"""
Comprehensive API endpoint tests
Tests all endpoints, error handling, validation, and integration
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, Mock
import schemas


# ========== HEALTH & INFO ENDPOINTS ==========

class TestHealthEndpoints:
    """Test basic service endpoints"""
    
    def test_root_endpoint(self, client):
        """GET / returns service information"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "RUSLE Erosion Risk API"
        assert data["version"] == "1.0.0"
        assert data["status"] == "operational"
        assert "endpoints" in data
    
    def test_health_endpoint(self, client):
        """GET /health returns healthy status"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
    
    def test_factors_info_endpoint(self, client):
        """GET /api/factors returns RUSLE factor information"""
        response = client.get("/api/factors")
        assert response.status_code == 200
        data = response.json()
        
        assert "factors" in data
        assert "R" in data["factors"]
        assert "K" in data["factors"]
        assert "LS" in data["factors"]
        assert "C" in data["factors"]
        assert "P" in data["factors"]
        
        # Check factor details
        assert data["factors"]["R"]["name"] == "Rainfall Erosivity"
        assert "unit" in data["factors"]["R"]
        assert data["equation"] == "A = R × K × LS × C × P"
    
    def test_limits_endpoint(self, client):
        """GET /api/limits returns computation limits"""
        response = client.get("/api/limits")
        assert response.status_code == 200
        data = response.json()
        
        assert data["max_polygon_area_km2"] == 1000
        assert data["max_vertices"] == 1000
        assert data["computation_timeout_sec"] == 120


# ========== MAIN RUSLE ENDPOINT - SUCCESS CASES ==========

class TestRUSLEEndpointSuccess:
    """Test successful RUSLE computations"""
    
    def test_rusle_complete_success(
        self, 
        client, 
        valid_request_payload,
        mock_backend_response,
        mock_satellite_image
    ):
        """Test complete successful RUSLE computation with all services"""
        with patch('validators.validate_full_polygon') as mock_validator, \
             patch('services.backend_client.call_backend_rusle', new_callable=AsyncMock) as mock_backend, \
             patch('services.sentinel_client.fetch_satellite_image', new_callable=AsyncMock) as mock_sentinel:
            
            # Setup mocks
            mock_validator.return_value = {
                "valid": True,
                "area_km2": 25.3,
                "num_vertices": 4
            }
            mock_backend.return_value = mock_backend_response
            mock_sentinel.return_value = mock_satellite_image
            
            # Make request
            response = client.post("/api/rusle", json=valid_request_payload)
            
            # Check response status
            assert response.status_code == 200
            data = response.json()
            
            # Check required top-level fields
            assert data["success"] is True
            assert "computation_time_sec" in data
            assert "timestamp" in data
            assert data["computation_time_sec"] > 0
            
            # Check polygon data
            assert "polygon" in data
            assert "polygon_metadata" in data
            assert data["polygon_metadata"]["area_km2"] == 25.3
            assert data["polygon_metadata"]["num_vertices"] == 4
            
            # Check satellite image
            assert data["satellite_image"] == mock_satellite_image
            
            # Check erosion stats
            assert "erosion" in data
            assert data["erosion"]["mean"] == 12.4
            assert data["erosion"]["max"] == 45.2
            assert data["erosion"]["min"] == 0.3
            assert data["erosion"]["p95"] == 28.3
            
            # Check factors
            assert "factors" in data
            assert len(data["factors"]) == 5
            assert "R" in data["factors"]
            assert "K" in data["factors"]
            assert data["factors"]["R"]["mean"] == 1850.5
            assert data["factors"]["LS"]["unit"] == "dimensionless"
            
            # Check hotspots (called "highlights" in schema)
            assert "highlights" in data
            assert data["num_hotspots"] == 1
            assert len(data["highlights"]) == 1
            assert data["highlights"][0]["id"] == "hotspot_1"
            assert data["highlights"][0]["severity"] == "high"
            
            # Check validation
            assert "validation" in data
            assert data["validation"]["model_valid"] is True
            
            # Check tile URLs
            assert "tile_urls" in data
            
            # Verify mocks were called
            mock_validator.assert_called_once()
            mock_backend.assert_called_once()
            mock_sentinel.assert_called_once()
            
            # Verify backend was called with correct options
            backend_call_args = mock_backend.call_args
            assert backend_call_args[0][1]["p_toggle"] is False
            assert backend_call_args[0][1]["threshold"] == 20.0
    
    def test_rusle_with_custom_options(
        self,
        client,
        valid_coordinates,
        mock_backend_response,
        mock_satellite_image
    ):
        """Test RUSLE with custom user options"""
        payload = {
            "coordinates": [c.dict() for c in valid_coordinates],
            "options": {
                "p_toggle": True,
                "threshold_t_ha_yr": 15.0,
                "compute_sensitivities": False,
                "date_range": "2025-01-01/2025-06-30"
            }
        }
        
        with patch('validators.validate_full_polygon') as mock_validator, \
             patch('services.backend_client.call_backend_rusle', new_callable=AsyncMock) as mock_backend, \
             patch('services.sentinel_client.fetch_satellite_image', new_callable=AsyncMock) as mock_sentinel:
            
            mock_validator.return_value = {"valid": True, "area_km2": 25.3, "num_vertices": 4}
            mock_backend.return_value = mock_backend_response
            mock_sentinel.return_value = mock_satellite_image
            
            response = client.post("/api/rusle", json=payload)
            assert response.status_code == 200
            
            # Verify options were passed correctly
            backend_call = mock_backend.call_args[0][1]
            assert backend_call["p_toggle"] is True
            assert backend_call["threshold"] == 15.0
            assert backend_call["compute_sensitivities"] is False
            
            # Verify date range passed to Sentinel
            sentinel_call = mock_sentinel.call_args
            assert "2025-01-01/2025-06-30" in str(sentinel_call)
    
    def test_rusle_minimal_options(
        self,
        client,
        valid_coordinates,
        mock_backend_response,
        mock_satellite_image
    ):
        """Test RUSLE with only coordinates (default options)"""
        payload = {
            "coordinates": [c.dict() for c in valid_coordinates]
        }
        
        with patch('validators.validate_full_polygon') as mock_validator, \
             patch('services.backend_client.call_backend_rusle', new_callable=AsyncMock) as mock_backend, \
             patch('services.sentinel_client.fetch_satellite_image', new_callable=AsyncMock) as mock_sentinel:
            
            mock_validator.return_value = {"valid": True, "area_km2": 25.3, "num_vertices": 4}
            mock_backend.return_value = mock_backend_response
            mock_sentinel.return_value = mock_satellite_image
            
            response = client.post("/api/rusle", json=payload)
            assert response.status_code == 200
            
            # Verify defaults were used
            backend_call = mock_backend.call_args[0][1]
            assert backend_call["p_toggle"] is False
            assert backend_call["threshold"] == 20.0


# ========== VALIDATION ERRORS ==========

class TestRUSLEValidationErrors:
    """Test request validation and error handling"""
    
    def test_missing_coordinates(self, client):
        """Test request with no coordinates"""
        payload = {"options": {}}
        response = client.post("/api/rusle", json=payload)
        assert response.status_code == 422  # Pydantic validation error
    
    def test_too_few_coordinates(self, client):
        """Test polygon with < 3 points"""
        payload = {
            "coordinates": [
                {"longitude": 0, "latitude": 0},
                {"longitude": 1, "latitude": 1}
            ]
        }
        response = client.post("/api/rusle", json=payload)
        assert response.status_code == 422
    
    def test_invalid_longitude(self, client):
        """Test coordinate with longitude > 180"""
        payload = {
            "coordinates": [
                {"longitude": 200, "latitude": 0},
                {"longitude": 0, "latitude": 0},
                {"longitude": 1, "latitude": 1},
                {"longitude": 200, "latitude": 0}
            ]
        }
        response = client.post("/api/rusle", json=payload)
        assert response.status_code == 422
    
    def test_invalid_latitude(self, client):
        """Test coordinate with latitude > 90"""
        payload = {
            "coordinates": [
                {"longitude": 0, "latitude": 100},
                {"longitude": 0, "latitude": 0},
                {"longitude": 1, "latitude": 0},
                {"longitude": 0, "latitude": 100}
            ]
        }
        response = client.post("/api/rusle", json=payload)
        assert response.status_code == 422
    
    def test_polygon_validation_error(self, client, valid_request_payload):
        """Test polygon that fails geometry validation"""
        with patch('validators.validate_full_polygon') as mock_validator:
            from validators import PolygonValidationError
            mock_validator.side_effect = PolygonValidationError("Area too large (1500 km²)")
            
            response = client.post("/api/rusle", json=valid_request_payload)
            assert response.status_code == 400
            data = response.json()
            assert data["error"] == "PolygonValidationError"
            assert "Area too large" in data["detail"]
    
    def test_self_intersecting_polygon(self, client):
        """Test self-intersecting polygon"""
        payload = {
            "coordinates": [
                {"longitude": 0, "latitude": 0},
                {"longitude": 1, "latitude": 1},
                {"longitude": 1, "latitude": 0},
                {"longitude": 0, "latitude": 1},  # Crosses
                {"longitude": 0, "latitude": 0}
            ]
        }
        
        with patch('validators.validate_full_polygon') as mock_validator:
            from validators import PolygonValidationError
            mock_validator.side_effect = PolygonValidationError("Invalid polygon: self-intersection")
            
            response = client.post("/api/rusle", json=payload)
            assert response.status_code == 400
            assert "self-intersection" in response.json()["detail"]
    
    def test_invalid_date_range(self, client, valid_coordinates):
        """Test invalid date range format"""
        payload = {
            "coordinates": [c.dict() for c in valid_coordinates],
            "options": {
                "date_range": "invalid-format"
            }
        }
        response = client.post("/api/rusle", json=payload)
        assert response.status_code == 422


# ========== BACKEND SERVICE ERRORS ==========

class TestBackendServiceErrors:
    """Test handling of backend service failures"""
    
    def test_backend_timeout(self, client, valid_request_payload, mock_satellite_image):
        """Test backend computation timeout"""
        with patch('validators.validate_full_polygon') as mock_validator, \
             patch('services.backend_client.call_backend_rusle', new_callable=AsyncMock) as mock_backend, \
             patch('services.sentinel_client.fetch_satellite_image', new_callable=AsyncMock) as mock_sentinel:
            
            mock_validator.return_value = {"valid": True, "area_km2": 25.3, "num_vertices": 4}
            mock_backend.side_effect = Exception("Backend timeout")
            mock_sentinel.return_value = mock_satellite_image
            
            response = client.post("/api/rusle", json=valid_request_payload)
            assert response.status_code == 500
            assert "Computation failed" in response.json()["detail"]
    
    def test_backend_http_error(self, client, valid_request_payload, mock_satellite_image):
        """Test backend HTTP error"""
        with patch('validators.validate_full_polygon') as mock_validator, \
             patch('services.backend_client.call_backend_rusle', new_callable=AsyncMock) as mock_backend, \
             patch('services.sentinel_client.fetch_satellite_image', new_callable=AsyncMock) as mock_sentinel:
            
            mock_validator.return_value = {"valid": True, "area_km2": 25.3, "num_vertices": 4}
            mock_backend.side_effect = Exception("RUSLE service error (500)")
            mock_sentinel.return_value = mock_satellite_image
            
            response = client.post("/api/rusle", json=valid_request_payload)
            assert response.status_code == 500
    
    def test_sentinel_failure_continues(self, client, valid_request_payload, mock_backend_response):
        """Test that Sentinel failure doesn't block entire request"""
        with patch('validators.validate_full_polygon') as mock_validator, \
             patch('services.backend_client.call_backend_rusle', new_callable=AsyncMock) as mock_backend, \
             patch('services.sentinel_client.fetch_satellite_image', new_callable=AsyncMock) as mock_sentinel:
            
            mock_validator.return_value = {"valid": True, "area_km2": 25.3, "num_vertices": 4}
            mock_backend.return_value = mock_backend_response
            mock_sentinel.side_effect = Exception("Sentinel timeout")
            
            # Should fail because Sentinel is awaited
            response = client.post("/api/rusle", json=valid_request_payload)
            assert response.status_code == 500
    
    def test_coordinate_parser_error(self, client, valid_request_payload, mock_backend_response, mock_satellite_image):
        """Test coordinate parsing failure"""
        with patch('validators.validate_full_polygon') as mock_validator, \
             patch('services.coordinate_parser.parse_to_geojson') as mock_parser:
            
            mock_validator.return_value = {"valid": True, "area_km2": 25.3, "num_vertices": 4}
            mock_parser.side_effect = Exception("Invalid coordinates")
            
            response = client.post("/api/rusle", json=valid_request_payload)
            assert response.status_code == 400
            assert "Failed to parse coordinates" in response.json()["detail"]


# ========== RESPONSE STRUCTURE VALIDATION ==========

class TestResponseStructure:
    """Test response matches schema exactly"""
    
    def test_response_matches_schema(self, client, valid_request_payload, mock_backend_response, mock_satellite_image):
        """Test response structure matches RUSLEResponse schema"""
        with patch('validators.validate_full_polygon') as mock_validator, \
             patch('services.backend_client.call_backend_rusle', new_callable=AsyncMock) as mock_backend, \
             patch('services.sentinel_client.fetch_satellite_image', new_callable=AsyncMock) as mock_sentinel:
            
            mock_validator.return_value = {"valid": True, "area_km2": 25.3, "num_vertices": 4}
            mock_backend.return_value = mock_backend_response
            mock_sentinel.return_value = mock_satellite_image
            
            response = client.post("/api/rusle", json=valid_request_payload)
            assert response.status_code == 200
            data = response.json()
            
            # Validate with Pydantic schema
            rusle_response = schemas.RUSLEResponse(**data)
            assert rusle_response.success is True
            assert isinstance(rusle_response.erosion, schemas.ErosionStats)
            assert isinstance(rusle_response.polygon_metadata, schemas.PolygonMetadata)


# ========== INTEGRATION TESTS ==========

class TestIntegration:
    """Integration tests with realistic scenarios"""
    
    def test_small_urban_polygon(self, client, mock_backend_response, mock_satellite_image):
        """Test small urban area (London)"""
        payload = {
            "coordinates": [
                {"longitude": -0.1276, "latitude": 51.5074},
                {"longitude": -0.1200, "latitude": 51.5074},
                {"longitude": -0.1200, "latitude": 51.5100},
                {"longitude": -0.1276, "latitude": 51.5100},
                {"longitude": -0.1276, "latitude": 51.5074}
            ],
            "options": {
                "threshold_t_ha_yr": 25.0,
                "date_range": "2025-06-01/2025-09-30"
            }
        }
        
        with patch('validators.validate_full_polygon') as mock_validator, \
             patch('services.backend_client.call_backend_rusle', new_callable=AsyncMock) as mock_backend, \
             patch('services.sentinel_client.fetch_satellite_image', new_callable=AsyncMock) as mock_sentinel:
            
            mock_validator.return_value = {"valid": True, "area_km2": 1.2, "num_vertices": 5}
            mock_backend.return_value = mock_backend_response
            mock_sentinel.return_value = mock_satellite_image
            
            response = client.post("/api/rusle", json=payload)
            assert response.status_code == 200
            assert response.json()["polygon_metadata"]["area_km2"] == 1.2
    
    def test_large_rural_polygon(self, client, mock_backend_response, mock_satellite_image):
        """Test large rural area"""
        payload = {
            "coordinates": [
                {"longitude": 0, "latitude": 50},
                {"longitude": 1, "latitude": 50},
                {"longitude": 1, "latitude": 51},
                {"longitude": 0, "latitude": 51},
                {"longitude": 0, "latitude": 50}
            ],
            "options": {
                "p_toggle": True,
                "compute_sensitivities": True
            }
        }
        
        with patch('validators.validate_full_polygon') as mock_validator, \
             patch('services.backend_client.call_backend_rusle', new_callable=AsyncMock) as mock_backend, \
             patch('services.sentinel_client.fetch_satellite_image', new_callable=AsyncMock) as mock_sentinel:
            
            mock_validator.return_value = {"valid": True, "area_km2": 500.0, "num_vertices": 5}
            mock_backend.return_value = mock_backend_response
            mock_sentinel.return_value = mock_satellite_image
            
            response = client.post("/api/rusle", json=payload)
            assert response.status_code == 200
            
            # Verify P toggle was passed
            backend_call = mock_backend.call_args[0][1]
            assert backend_call["p_toggle"] is True
    