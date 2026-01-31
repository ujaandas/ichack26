"""
Comprehensive polygon validation tests
Tests all validation logic, edge cases, and error conditions
"""

import pytest
from validators import (
    validate_full_polygon,
    validate_coordinate_range,
    validate_minimum_points,
    validate_polygon_closed,
    validate_polygon_geometry,
    validate_polygon_complexity,
    validate_polygon_area,
    validate_aspect_ratio,
    calculate_geodesic_area,
    check_duplicate_points,
    get_polygon_metadata,
    PolygonValidationError
)
import schemas
from shapely.geometry import Polygon
from unittest.mock import patch, AsyncMock



# ========== COORDINATE RANGE VALIDATION ==========

class TestCoordinateRange:
    """Test coordinate range validation"""
    
    def test_valid_coordinates(self, valid_coordinates):
        """Test valid coordinate ranges"""
        assert validate_coordinate_range(valid_coordinates) is True
    
    def test_longitude_too_high(self):
        """Test longitude > 180"""
        coords = [
            schemas.Coordinate(longitude=200, latitude=0),
            schemas.Coordinate(longitude=0, latitude=0),
            schemas.Coordinate(longitude=0, latitude=1)
        ]
        with pytest.raises(PolygonValidationError, match="Longitude.*out of valid range"):
            validate_coordinate_range(coords)
    
    def test_longitude_too_low(self):
        """Test longitude < -180"""
        coords = [
            schemas.Coordinate(longitude=-200, latitude=0),
            schemas.Coordinate(longitude=0, latitude=0),
            schemas.Coordinate(longitude=0, latitude=1)
        ]
        with pytest.raises(PolygonValidationError, match="Longitude"):
            validate_coordinate_range(coords)
    
    def test_latitude_too_high(self):
        """Test latitude > 90"""
        coords = [
            schemas.Coordinate(longitude=0, latitude=100),
            schemas.Coordinate(longitude=0, latitude=0),
            schemas.Coordinate(longitude=1, latitude=0)
        ]
        with pytest.raises(PolygonValidationError, match="Latitude.*out of valid range"):
            validate_coordinate_range(coords)
    
    def test_latitude_too_low(self):
        """Test latitude < -90"""
        coords = [
            schemas.Coordinate(longitude=0, latitude=-100),
            schemas.Coordinate(longitude=0, latitude=0),
            schemas.Coordinate(longitude=1, latitude=0)
        ]
        with pytest.raises(PolygonValidationError, match="Latitude"):
            validate_coordinate_range(coords)
    
    def test_edge_coordinates(self):
        """Test coordinates at valid boundaries"""
        coords = [
            schemas.Coordinate(longitude=180, latitude=90),
            schemas.Coordinate(longitude=-180, latitude=-90),
            schemas.Coordinate(longitude=0, latitude=0),
            schemas.Coordinate(longitude=180, latitude=90)
        ]
        assert validate_coordinate_range(coords) is True


# ========== MINIMUM POINTS VALIDATION ==========

class TestMinimumPoints:
    """Test minimum points validation"""
    
    def test_valid_triangle(self):
        """Test 3 points (minimum for polygon)"""
        coords = [
            schemas.Coordinate(longitude=0, latitude=0),
            schemas.Coordinate(longitude=1, latitude=0),
            schemas.Coordinate(longitude=0, latitude=1)
        ]
        assert validate_minimum_points(coords) is True
    
    def test_too_few_points(self):
        """Test < 3 points"""
        coords = [
            schemas.Coordinate(longitude=0, latitude=0),
            schemas.Coordinate(longitude=1, latitude=1)
        ]
        with pytest.raises(PolygonValidationError, match="at least 3 vertices"):
            validate_minimum_points(coords)
    
    def test_one_point(self):
        """Test single point"""
        coords = [schemas.Coordinate(longitude=0, latitude=0)]
        with pytest.raises(PolygonValidationError):
            validate_minimum_points(coords)
    
    def test_many_points(self):
        """Test polygon with many vertices"""
        coords = [
            schemas.Coordinate(longitude=i*0.1, latitude=i*0.1)
            for i in range(100)
        ]
        assert validate_minimum_points(coords) is True


# ========== POLYGON CLOSING ==========

class TestPolygonClosing:
    """Test polygon auto-closing"""
    
    def test_already_closed(self, valid_coordinates):
        """Test polygon that's already closed"""
        result = validate_polygon_closed(valid_coordinates)
        assert len(result) == len(valid_coordinates)
    
    def test_auto_close_open_polygon(self):
        """Test auto-closing of open polygon"""
        coords = [
            schemas.Coordinate(longitude=0, latitude=0),
            schemas.Coordinate(longitude=1, latitude=0),
            schemas.Coordinate(longitude=1, latitude=1)
            # Not closed
        ]
        result = validate_polygon_closed(coords)
        assert len(result) == 4  # Should append first point
        assert result[0].longitude == result[-1].longitude
        assert result[0].latitude == result[-1].latitude


# ========== GEOMETRY VALIDATION ==========

class TestPolygonGeometry:
    """Test Shapely geometry validation"""
    
    def test_valid_polygon(self, valid_coordinates):
        """Test valid polygon passes"""
        poly = validate_polygon_geometry(valid_coordinates)
        assert isinstance(poly, Polygon)
        assert poly.is_valid
        assert not poly.is_empty
    
    def test_self_intersecting_polygon(self):
        """Test self-intersecting polygon fails"""
        coords = [
            schemas.Coordinate(longitude=0, latitude=0),
            schemas.Coordinate(longitude=1, latitude=1),
            schemas.Coordinate(longitude=1, latitude=0),
            schemas.Coordinate(longitude=0, latitude=1),  # Crosses previous edge
            schemas.Coordinate(longitude=0, latitude=0)
        ]
        with pytest.raises(PolygonValidationError, match="Invalid polygon"):
            validate_polygon_geometry(coords)
    
    def test_collinear_points(self):
        """Test collinear points (no area)"""
        coords = [
            schemas.Coordinate(longitude=0, latitude=0),
            schemas.Coordinate(longitude=1, latitude=1),
            schemas.Coordinate(longitude=2, latitude=2),
            schemas.Coordinate(longitude=0, latitude=0)
        ]
        with pytest.raises(PolygonValidationError, match="no area"):
            validate_polygon_geometry(coords)
    
    def test_duplicate_consecutive_points(self):
        """Test duplicate consecutive points"""
        coords = [
            schemas.Coordinate(longitude=0, latitude=0),
            schemas.Coordinate(longitude=1, latitude=0),
            schemas.Coordinate(longitude=1, latitude=0),  # Duplicate
            schemas.Coordinate(longitude=1, latitude=1),
            schemas.Coordinate(longitude=0, latitude=0)
        ]
        # Should still create valid polygon (Shapely handles duplicates)
        poly = validate_polygon_geometry(coords)
        assert poly.is_valid


# ========== COMPLEXITY VALIDATION ==========

class TestPolygonComplexity:
    """Test polygon complexity checks"""
    
    def test_simple_polygon(self, valid_coordinates):
        """Test simple polygon passes"""
        assert validate_polygon_complexity(valid_coordinates) is True
    
    def test_complex_polygon(self):
        """Test moderately complex polygon"""
        coords = [
            schemas.Coordinate(longitude=i*0.01, latitude=i*0.01)
            for i in range(100)
        ]
        assert validate_polygon_complexity(coords) is True
    
    def test_too_complex_polygon(self):
        """Test polygon exceeding vertex limit"""
        coords = [
            schemas.Coordinate(longitude=i*0.001, latitude=i*0.001)
            for i in range(1500)  # > MAX_VERTICES (1000)
        ]
        with pytest.raises(PolygonValidationError, match="too complex"):
            validate_polygon_complexity(coords)


# ========== AREA VALIDATION ==========

class TestPolygonArea:
    """Test polygon area calculations and limits"""
    
    def test_valid_area(self, valid_coordinates):
        """Test polygon with valid area"""
        points = [(c.longitude, c.latitude) for c in valid_coordinates]
        poly = Polygon(points)
        area = validate_polygon_area(poly)
        assert 0 < area < 1000
    
    def test_small_area(self):
        """Test small but valid area (1 hectare)"""
        coords = [
            schemas.Coordinate(longitude=0, latitude=0),
            schemas.Coordinate(longitude=0.01, latitude=0),
            schemas.Coordinate(longitude=0.01, latitude=0.01),
            schemas.Coordinate(longitude=0, latitude=0.01),
            schemas.Coordinate(longitude=0, latitude=0)
        ]
        points = [(c.longitude, c.latitude) for c in coords]
        poly = Polygon(points)
        area = validate_polygon_area(poly)
        assert area > 0
    
    def test_area_too_small(self):
        """Test area below minimum (< 0.01 km²)"""
        coords = [
            schemas.Coordinate(longitude=0, latitude=0),
            schemas.Coordinate(longitude=0.0001, latitude=0),
            schemas.Coordinate(longitude=0.0001, latitude=0.0001),
            schemas.Coordinate(longitude=0, latitude=0)
        ]
        points = [(c.longitude, c.latitude) for c in coords]
        poly = Polygon(points)
        with pytest.raises(PolygonValidationError, match="too small"):
            validate_polygon_area(poly)
    
    def test_area_too_large(self):
        """Test area exceeding maximum (> 1000 km²)"""
        coords = [
            schemas.Coordinate(longitude=0, latitude=0),
            schemas.Coordinate(longitude=2, latitude=0),
            schemas.Coordinate(longitude=2, latitude=2),
            schemas.Coordinate(longitude=0, latitude=2),
            schemas.Coordinate(longitude=0, latitude=0)
        ]
        points = [(c.longitude, c.latitude) for c in coords]
        poly = Polygon(points)
        with pytest.raises(PolygonValidationError, match="too large"):
            validate_polygon_area(poly)
    
    def test_geodesic_area_calculation(self, valid_coordinates):
        """Test geodesic area is different from planar"""
        points = [(c.longitude, c.latitude) for c in valid_coordinates]
        poly = Polygon(points)
        
        geodesic_area = calculate_geodesic_area(poly)
        planar_area = poly.area * 111.32 * 111.32  # Rough conversion
        
        # Should be similar but not identical
        assert abs(geodesic_area - planar_area) / planar_area < 0.1  # Within 10%


# ========== ASPECT RATIO VALIDATION ==========

class TestAspectRatio:
    """Test aspect ratio validation (no thin slivers)"""
    
    def test_square_polygon(self):
        """Test square polygon has aspect ratio ~1"""
        coords = [
            schemas.Coordinate(longitude=0, latitude=0),
            schemas.Coordinate(longitude=1, latitude=0),
            schemas.Coordinate(longitude=1, latitude=1),
            schemas.Coordinate(longitude=0, latitude=1),
            schemas.Coordinate(longitude=0, latitude=0)
        ]
        points = [(c.longitude, c.latitude) for c in coords]
        poly = Polygon(points)
        assert validate_aspect_ratio(poly) is True
    
    def test_reasonable_rectangle(self):
        """Test rectangle with aspect ratio < 100"""
        coords = [
            schemas.Coordinate(longitude=0, latitude=0),
            schemas.Coordinate(longitude=10, latitude=0),
            schemas.Coordinate(longitude=10, latitude=1),
            schemas.Coordinate(longitude=0, latitude=1),
            schemas.Coordinate(longitude=0, latitude=0)
        ]
        points = [(c.longitude, c.latitude) for c in coords]
        poly = Polygon(points)
        assert validate_aspect_ratio(poly) is True
    
    def test_thin_sliver(self):
        """Test thin sliver polygon fails"""
        coords = [
            schemas.Coordinate(longitude=0, latitude=0),
            schemas.Coordinate(longitude=200, latitude=0),
            schemas.Coordinate(longitude=200, latitude=0.1),
            schemas.Coordinate(longitude=0, latitude=0.1),
            schemas.Coordinate(longitude=0, latitude=0)
        ]
        points = [(c.longitude, c.latitude) for c in coords]
        poly = Polygon(points)
        with pytest.raises(PolygonValidationError, match="aspect ratio too extreme"):
            validate_aspect_ratio(poly)


# ========== DUPLICATE POINTS CHECK ==========

class TestDuplicatePoints:
    """Test duplicate point detection"""
    
    def test_no_duplicates(self, valid_coordinates):
        """Test polygon with no duplicates"""
        assert check_duplicate_points(valid_coordinates) is True
    
    def test_consecutive_duplicates(self):
        """Test detection of consecutive duplicate points"""
        coords = [
            schemas.Coordinate(longitude=0, latitude=0),
            schemas.Coordinate(longitude=1, latitude=0),
            schemas.Coordinate(longitude=1, latitude=0),  # Duplicate
            schemas.Coordinate(longitude=1, latitude=1),
            schemas.Coordinate(longitude=0, latitude=0)
        ]
        # Should warn but not fail
        assert check_duplicate_points(coords) is True


# ========== FULL VALIDATION PIPELINE ==========

class TestFullValidation:
    """Test complete validation pipeline"""
    
    def test_full_validation_success(self, valid_coordinates):
        """Test complete validation passes for valid polygon"""
        result = validate_full_polygon(valid_coordinates)
        
        assert result["valid"] is True
        assert "area_km2" in result
        assert "area_hectares" in result
        assert "centroid" in result
        assert "bbox" in result
        assert "num_vertices" in result
        assert "perimeter_km" in result
        
        assert result["area_km2"] > 0
        assert result["num_vertices"] >= 3
        assert len(result["centroid"]) == 2
        assert len(result["bbox"]) == 4
    
    def test_full_validation_all_checks(self):
        """Test all validation checks are executed"""
        coords = [
            schemas.Coordinate(longitude=0.28, latitude=51.50),
            schemas.Coordinate(longitude=0.19, latitude=51.50),
            schemas.Coordinate(longitude=0.39, latitude=51.52),
            schemas.Coordinate(longitude=0.28, latitude=51.50)
        ]
        
        result = validate_full_polygon(coords)
        
        # Check metadata completeness
        assert "area_km2" in result
        assert result["area_km2"] > 0
        assert result["area_km2"] < 1000
        assert result["num_vertices"] == 4
    
    def test_validation_failure_propagates(self):
        """Test that any validation failure stops pipeline"""
        # Out of range coordinates
        coords = [
            schemas.Coordinate(longitude=200, latitude=0),
            schemas.Coordinate(longitude=0, latitude=0),
            schemas.Coordinate(longitude=0, latitude=1)
        ]
        
        with pytest.raises(PolygonValidationError):
            validate_full_polygon(coords)
    
    def test_auto_close_in_pipeline(self):
        """Test polygon is auto-closed during validation"""
        coords = [
            schemas.Coordinate(longitude=0, latitude=0),
            schemas.Coordinate(longitude=1, latitude=0),
            schemas.Coordinate(longitude=1, latitude=1)
            # Open polygon
        ]
        
        result = validate_full_polygon(coords)
        assert result["valid"] is True
        # Polygon should have been closed
        assert result["num_vertices"] == 4


# ========== METADATA EXTRACTION ==========

class TestMetadataExtraction:
    """Test polygon metadata extraction"""
    
    def test_get_polygon_metadata(self, valid_coordinates):
        """Test metadata extraction"""
        points = [(c.longitude, c.latitude) for c in valid_coordinates]
        poly = Polygon(points)
        
        metadata = get_polygon_metadata(poly, valid_coordinates)
        
        assert "area_km2" in metadata
        assert "area_hectares" in metadata
        assert "centroid" in metadata
        assert "bbox" in metadata
        assert "num_vertices" in metadata
        assert "perimeter_km" in metadata
        
        assert metadata["area_hectares"] == metadata["area_km2"] * 100
        assert metadata["num_vertices"] == len(valid_coordinates)
        assert len(metadata["centroid"]) == 2
        assert len(metadata["bbox"]) == 4


# ========== EDGE CASES ==========

class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_polygon_at_dateline(self):
        """Test polygon crossing dateline (longitude ±180)"""
        coords = [
            schemas.Coordinate(longitude=179, latitude=0),
            schemas.Coordinate(longitude=-179, latitude=0),
            schemas.Coordinate(longitude=-179, latitude=1),
            schemas.Coordinate(longitude=179, latitude=1),
            schemas.Coordinate(longitude=179, latitude=0)
        ]
        
        # Should handle dateline crossing
        result = validate_full_polygon(coords)
        assert result["valid"] is True
    
    def test_polygon_at_poles(self):
        """Test polygon near poles"""
        coords = [
            schemas.Coordinate(longitude=0, latitude=89),
            schemas.Coordinate(longitude=90, latitude=89),
            schemas.Coordinate(longitude=90, latitude=89.5),
            schemas.Coordinate(longitude=0, latitude=89.5),
            schemas.Coordinate(longitude=0, latitude=89)
        ]
        
        result = validate_full_polygon(coords)
        assert result["valid"] is True
    
    def test_polygon_at_equator(self):
        """Test polygon at equator"""
        coords = [
            schemas.Coordinate(longitude=0, latitude=-1),
            schemas.Coordinate(longitude=1, latitude=-1),
            schemas.Coordinate(longitude=1, latitude=1),
            schemas.Coordinate(longitude=0, latitude=1),
            schemas.Coordinate(longitude=0, latitude=-1)
        ]
        
        result = validate_full_polygon(coords)
        assert result["valid"] is True
    
    def test_very_small_valid_polygon(self):
        """Test smallest valid polygon (just above minimum)"""
        coords = [
            schemas.Coordinate(longitude=0, latitude=0),
            schemas.Coordinate(longitude=0.015, latitude=0),
            schemas.Coordinate(longitude=0.015, latitude=0.015),
            schemas.Coordinate(longitude=0, latitude=0.015),
            schemas.Coordinate(longitude=0, latitude=0)
        ]
        
        result = validate_full_polygon(coords)
        assert result["valid"] is True
        assert result["area_km2"] >= 0.01
