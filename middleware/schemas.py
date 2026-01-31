"""
Pydantic schemas for RUSLE API request/response validation
Defines data contracts between frontend and FastAPI middleware
"""

from pydantic import BaseModel, Field, validator, model_validator
from typing import List, Dict, Optional, Any
from datetime import datetime


# ========== REQUEST MODELS (Frontend → FastAPI) ==========

class Coordinate(BaseModel):
    """
    Single coordinate point from frontend polygon selector
    Height is optional and ignored for 2D RUSLE computations
    """
    # NOTE: we intentionally do not enforce ge/le bounds here so unit tests
    # can construct Coordinate objects with out-of-range values. Request-level
    # validation (in RUSLERequest) will enforce ranges and produce a 422.
    longitude: float = Field(
        ...,
        description="Longitude in decimal degrees",
        example=0.2866
    )
    latitude: float = Field(
        ...,
        description="Latitude in decimal degrees",
        example=51.5074
    )
    height: Optional[float] = Field(
        None,
        description="Height/elevation (ignored in current implementation)"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "longitude": 0.2866,
                "latitude": 51.5074,
                "height": 0
            }
        }


class RUSLEOptions(BaseModel):
    """
    User-configurable computation parameters
    Allows frontend to customize RUSLE calculation
    """
    p_toggle: bool = Field(
        False,
        description="Enable support practices factor adjustment (reduces P for cropland on slopes)"
    )
    date_range: str = Field(
        "2025-01-01/2025-12-31",
        description="Date range for Sentinel-2 imagery and NDVI (ISO format: YYYY-MM-DD/YYYY-MM-DD)",
        pattern=r'^\d{4}-\d{2}-\d{2}/\d{4}-\d{2}-\d{2}$'
    )
    threshold_t_ha_yr: float = Field(
        20.0,
        gt=0,
        le=100,
        description="Erosion threshold for hotspot flagging (t/ha/yr)"
    )
    compute_sensitivities: bool = Field(
        True,
        description="Run sensitivity validation tests (adds 10-20s to computation)"
    )
    
    @validator('date_range')
    def validate_date_range(cls, v):
        """Ensure end date is after start date"""
        try:
            start, end = v.split('/')
            start_date = datetime.strptime(start, '%Y-%m-%d')
            end_date = datetime.strptime(end, '%Y-%m-%d')
            
            if end_date <= start_date:
                raise ValueError("End date must be after start date")
            
            # Warn if range is too long (>2 years)
            days_diff = (end_date - start_date).days
            if days_diff > 730:
                raise ValueError("Date range too long (max 2 years)")
                
        except Exception as e:
            raise ValueError(f"Invalid date_range format: {str(e)}")
        
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "p_toggle": False,
                "date_range": "2025-07-01/2025-12-31",
                "threshold_t_ha_yr": 20.0,
                "compute_sensitivities": True
            }
        }


class RUSLERequest(BaseModel):
    """
    Complete POST request body from frontend
    Contains polygon coordinates and computation options
    """
    coordinates: List[Coordinate] = Field(
        ...,
        min_items=3,
        description="List of polygon vertices (minimum 3 points)"
    )
    options: RUSLEOptions = Field(
        default_factory=RUSLEOptions,
        description="Optional computation parameters (uses defaults if omitted)"
    )
    
    @validator('coordinates')
    def validate_and_close_polygon(cls, coords):
        """
        Ensure polygon is closed (first point == last point)
        Auto-closes if needed
        """
        if len(coords) < 3:
            raise ValueError("Polygon requires at least 3 vertices")
        
        first = coords[0]
        last = coords[-1]
        
        # Check if already closed
        if (first.longitude != last.longitude) or (first.latitude != last.latitude):
            # Auto-close by appending first point
            coords.append(first)
        
        return coords
    
    @model_validator(mode='after')
    def validate_polygon_size(cls, model):
        """
        Quick check for obviously invalid polygons
        Detailed validation happens in validators.py
        Note: in Pydantic v2 the model_validator in 'after' mode receives the model
        instance (not a dict), so access attributes directly.
        """
        coords = getattr(model, 'coordinates', []) or []

        if len(coords) > 1000:
            raise ValueError("Polygon too complex (max 1000 vertices)")

        # Enforce coordinate ranges at the request level so incoming JSON
        # payloads with out-of-range values raise a Pydantic ValidationError
        # and FastAPI returns HTTP 422 as expected by API tests.
        for i, c in enumerate(coords):
            if not (-180 <= c.longitude <= 180):
                raise ValueError(f"Point {i+1}: Longitude {c.longitude} out of valid range [-180, 180]")
            if not (-90 <= c.latitude <= 90):
                raise ValueError(f"Point {i+1}: Latitude {c.latitude} out of valid range [-90, 90]")

        return model
    
    class Config:
        schema_extra = {
            "example": {
                "coordinates": [
                    {"longitude": 0.2866, "latitude": 51.5074, "height": 0},
                    {"longitude": 0.1933, "latitude": 51.5074, "height": 0},
                    {"longitude": 0.3970, "latitude": 51.5200, "height": 0},
                    {"longitude": 0.2866, "latitude": 51.5074, "height": 0}
                ],
                "options": {
                    "p_toggle": False,
                    "date_range": "2025-07-01/2025-12-31",
                    "threshold_t_ha_yr": 20.0
                }
            }
        }


# ========== RESPONSE MODELS (FastAPI → Frontend) ==========

class PolygonMetadata(BaseModel):
    """
    Metadata about the processed polygon
    """
    area_km2: float = Field(..., description="Polygon area in square kilometers")
    centroid: List[float] = Field(..., description="Centroid coordinates [lon, lat]")
    bbox: List[float] = Field(..., description="Bounding box [minx, miny, maxx, maxy]")
    num_vertices: int = Field(..., description="Number of polygon vertices")


class ErosionStats(BaseModel):
    """
    Statistical summary of erosion rates across polygon
    All values in tonnes per hectare per year (t/ha/yr)
    """
    mean: float = Field(..., description="Mean erosion rate", ge=0)
    max: float = Field(..., description="Maximum erosion rate", ge=0)
    min: float = Field(..., description="Minimum erosion rate", ge=0)
    stddev: float = Field(..., description="Standard deviation", ge=0)
    p50: float = Field(..., description="Median (50th percentile)", ge=0)
    p95: float = Field(..., description="95th percentile", ge=0)
    total_soil_loss_tonnes: Optional[float] = Field(
        None,
        description="Total estimated soil loss for entire polygon (optional)"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "mean": 12.4,
                "max": 45.2,
                "min": 0.3,
                "stddev": 8.7,
                "p50": 9.1,
                "p95": 28.3,
                "total_soil_loss_tonnes": 1250.5
            }
        }


class FactorStats(BaseModel):
    """
    Statistics for a single RUSLE factor (R, K, LS, C, or P)
    """
    mean: float = Field(..., description="Mean factor value")
    stddev: float = Field(..., description="Standard deviation")
    min: float = Field(..., description="Minimum value")
    max: float = Field(..., description="Maximum value")
    unit: str = Field(..., description="Factor unit (e.g., 'MJ mm ha⁻¹ h⁻¹ yr⁻¹' for R)")
    contribution_pct: Optional[float] = Field(
        None,
        description="Relative contribution to overall erosion variability (%)"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "mean": 1850.5,
                "stddev": 120.3,
                "min": 1620.0,
                "max": 2100.0,
                "unit": "MJ mm ha⁻¹ h⁻¹ yr⁻¹",
                "contribution_pct": 35.2
            }
        }


class HotspotProperties(BaseModel):
    """
    Properties of a high-risk hotspot area
    """
    area_ha: float = Field(..., description="Hotspot area in hectares", ge=0)
    mean_erosion: float = Field(..., description="Mean erosion rate (t/ha/yr)", ge=0)
    max_erosion: float = Field(..., description="Max erosion rate (t/ha/yr)", ge=0)
    dominant_factor: str = Field(
        ...,
        description="Primary factor driving high erosion (e.g., 'LS', 'C')"
    )


class Hotspot(BaseModel):
    """
    Single highlighted high-risk area with ML-flagged reason
    Contains GeoJSON polygon for frontend map overlay
    """
    id: str = Field(..., description="Unique hotspot identifier")
    geometry: Dict[str, Any] = Field(
        ...,
        description="GeoJSON Polygon geometry"
    )
    properties: HotspotProperties
    reason: str = Field(
        ...,
        description="Human-readable explanation for flagging",
        example="Steep slope (LS > 10) + Low vegetation cover (C > 0.15)"
    )
    severity: str = Field(
        ...,
        description="Risk severity level",
        pattern="^(low|moderate|high|critical)$"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "id": "hotspot_1",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[0.28, 51.50], [0.29, 51.50], [0.29, 51.51], [0.28, 51.51], [0.28, 51.50]]]
                },
                "properties": {
                    "area_ha": 3.2,
                    "mean_erosion": 38.5,
                    "max_erosion": 52.1,
                    "dominant_factor": "LS"
                },
                "reason": "Steep slope (LS > 10) + Low vegetation cover (C > 0.15)",
                "severity": "high"
            }
        }


class ValidationMetrics(BaseModel):
    """
    Model sensitivity validation results
    Shows % change in output when inputs are modified
    """
    high_veg_reduction_pct: float = Field(
        ...,
        description="% reduction in erosion when vegetation cover increased (expected: 50-80%)"
    )
    flat_terrain_reduction_pct: float = Field(
        ...,
        description="% reduction in erosion when terrain flattened (expected: >80%)"
    )
    bare_soil_increase_pct: float = Field(
        ...,
        description="% increase in erosion when vegetation removed (expected: >100%)"
    )
    model_valid: bool = Field(
        ...,
        description="Overall model validity (True if all checks pass thresholds)"
    )
    notes: Optional[str] = Field(
        None,
        description="Additional validation notes or warnings"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "high_veg_reduction_pct": 68.2,
                "flat_terrain_reduction_pct": 85.1,
                "bare_soil_increase_pct": 230.5,
                "model_valid": True,
                "notes": "All sensitivity tests passed expected ranges"
            }
        }


class RUSLEResponse(BaseModel):
    """
    Complete JSON response to frontend
    Contains all computation results, satellite imagery, and validation
    """
    success: bool = Field(True, description="Request success status")
    computation_time_sec: float = Field(..., description="Total processing time", ge=0)
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="Response timestamp (UTC)"
    )
    
    # Input polygon metadata
    polygon: Dict[str, Any] = Field(..., description="Input polygon GeoJSON")
    polygon_metadata: PolygonMetadata
    
    # Satellite imagery
    satellite_image: str = Field(
        ...,
        description="Base64-encoded PNG or tile URL for satellite background"
    )
    
    # RUSLE results
    erosion: ErosionStats
    factors: Dict[str, FactorStats] = Field(
        ...,
        description="Individual RUSLE factors (R, K, LS, C, P)"
    )
    
    # Highlighted areas
    highlights: List[Hotspot] = Field(
        default_factory=list,
        description="High-risk areas flagged by ML (empty list if none found)"
    )
    num_hotspots: int = Field(..., description="Total number of hotspots identified")
    
    # Validation
    validation: Optional[ValidationMetrics] = Field(
        None,
        description="Sensitivity validation metrics (null if compute_sensitivities=False)"
    )
    
    # Optional tile URLs for interactive map layers
    tile_urls: Optional[Dict[str, str]] = Field(
        None,
        description="Map tile URLs for erosion risk overlay (GEE getMapId)"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "computation_time_sec": 42.3,
                "timestamp": "2026-01-31T19:15:00.000Z",
                "polygon": {"type": "Feature", "geometry": {...}},
                "polygon_metadata": {
                    "area_km2": 25.3,
                    "centroid": [0.28, 51.51],
                    "bbox": [0.19, 51.50, 0.40, 51.52],
                    "num_vertices": 4
                },
                "satellite_image": "data:image/png;base64,iVBORw0KG...",
                "erosion": {
                    "mean": 12.4,
                    "max": 45.2,
                    "min": 0.3,
                    "stddev": 8.7,
                    "p50": 9.1,
                    "p95": 28.3
                },
                "factors": {
                    "R": {"mean": 1850, "stddev": 120, "unit": "MJ mm ha⁻¹ h⁻¹ yr⁻¹"},
                    "K": {"mean": 0.032, "stddev": 0.008, "unit": "t ha h ha⁻¹ MJ⁻¹ mm⁻¹"}
                },
                "highlights": [],
                "num_hotspots": 3,
                "validation": {
                    "high_veg_reduction_pct": 68.2,
                    "flat_terrain_reduction_pct": 85.1,
                    "bare_soil_increase_pct": 230.5,
                    "model_valid": True
                }
            }
        }


# ========== ERROR RESPONSE MODEL ==========

class ErrorResponse(BaseModel):
    """
    Standardized error response for failed requests
    """
    success: bool = Field(False, description="Request success status")
    error: str = Field(..., description="Error type/category")
    detail: str = Field(..., description="Human-readable error message")
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="Error timestamp (UTC)"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "success": False,
                "error": "ValidationError",
                "detail": "Polygon area (1250 km²) exceeds limit (1000 km²). Select a smaller area.",
                "timestamp": "2026-01-31T19:15:00.000Z"
            }
        }
