"""
FastAPI Main Application - RUSLE Erosion Risk API (CORRECTED)
Middleware layer between frontend and backend/GEE processing
Fixed: imports, type conversions, response structure, validation pipeline
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import asyncio
import time
import os
import logging
from typing import Dict

# FIXED: Correct imports
import schemas
import validators
import services.coordinate_parser as coordinate_parser
import services.sentinel_client as sentinel_client
import services.backend_client as backend_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment configuration
FRONTEND_URL = os.getenv("FRONTEND_URL", "*")
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8001")
ENABLE_AUTH = os.getenv("ENABLE_AUTH", "false").lower() == "true"


# ========== LIFESPAN EVENTS ==========

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info("🚀 RUSLE API starting up...")
    logger.info(f"Frontend URL: {FRONTEND_URL}")
    logger.info(f"Backend URL: {BACKEND_URL}")
    
    # Test backend connectivity
    try:
        await backend_client.test_backend_connection()
        logger.info("✅ Backend connection successful")
    except Exception as e:
        logger.warning(f"⚠️  Backend connection failed: {e}")
    
    # Test Sentinel Hub connectivity (optional)
    try:
        await sentinel_client.test_sentinel_connection()
        logger.info("✅ Sentinel Hub connection successful")
    except Exception as e:
        logger.warning(f"⚠️  Sentinel Hub connection failed: {e}")
    
    yield
    
    # Shutdown
    logger.info("🛑 RUSLE API shutting down...")


# ========== APP INITIALIZATION ==========

app = FastAPI(
    title="RUSLE Erosion Risk API",
    description="Soil erosion prediction using RUSLE with global datasets",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)


# ========== MIDDLEWARE ==========

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL] if FRONTEND_URL != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"]
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests with timing"""
    start_time = time.time()
    logger.info(f"→ {request.method} {request.url.path}")
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    logger.info(f"← {request.method} {request.url.path} - {response.status_code} ({process_time:.2f}s)")
    
    return response


# ========== EXCEPTION HANDLERS ==========

@app.exception_handler(validators.PolygonValidationError)
async def polygon_validation_exception_handler(request: Request, exc: validators.PolygonValidationError):
    """Handle polygon validation errors"""
    logger.warning(f"Validation error: {str(exc)}")
    return JSONResponse(
        status_code=400,
        content=schemas.ErrorResponse(
            error="PolygonValidationError",
            detail=str(exc)
        ).dict()
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content=schemas.ErrorResponse(
            error=f"HTTP{exc.status_code}",
            detail=exc.detail
        ).dict()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Catch-all for unexpected errors"""
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=schemas.ErrorResponse(
            error="InternalServerError",
            detail="An unexpected error occurred. Please try again or contact support."
        ).dict()
    )


# ========== API ENDPOINTS ==========

@app.get("/")
async def root():
    """API root"""
    return {
        "service": "RUSLE Erosion Risk API",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs",
        "endpoints": {
            "compute": "POST /api/rusle",
            "health": "GET /health"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for deployment platforms"""
    return {
        "status": "healthy",
        "service": "RUSLE API",
        "timestamp": time.time()
    }


@app.post(
    "/api/rusle",
    response_model=schemas.RUSLEResponse,
    responses={
        400: {"model": schemas.ErrorResponse, "description": "Invalid polygon or parameters"},
        500: {"model": schemas.ErrorResponse, "description": "Server error"},
        504: {"model": schemas.ErrorResponse, "description": "Backend timeout"}
    }
)
async def compute_rusle(request: schemas.RUSLERequest) -> schemas.RUSLEResponse:
    """
    Main RUSLE computation endpoint
    FIXED: proper validation pipeline, type conversions, response structure
    """
    start_time = time.time()
    
    logger.info(f"Received RUSLE request with {len(request.coordinates)} coordinates")
    
    # ========== STEP 1: VALIDATE POLYGON (FIXED: now calling validators) ==========
    try:
        validation_metadata = validators.validate_full_polygon(request.coordinates)
        logger.info(
            f"Polygon validated: {validation_metadata['area_km2']:.2f} km², "
            f"{validation_metadata['num_vertices']} vertices"
        )
    except validators.PolygonValidationError as e:
        logger.warning(f"Polygon validation failed: {e}")
        # Re-raise the original PolygonValidationError so the specific
        # exception handler (polygon_validation_exception_handler) is used
        # and the API returns a structured ErrorResponse with error="PolygonValidationError".
        raise
    
    
    # ========== STEP 2: PARSE TO GEOJSON ==========
    try:
        geojson = coordinate_parser.parse_to_geojson(request.coordinates)
        logger.info(f"Converted to GeoJSON with buffer")
    except Exception as e:
        logger.error(f"GeoJSON conversion failed: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to parse coordinates: {str(e)}")
    
    
    # ========== STEP 3: PARALLEL EXECUTION ==========
    # FIXED: Convert Pydantic model to dict with correct field names
    backend_options = {
        "p_toggle": request.options.p_toggle,
        "threshold": request.options.threshold_t_ha_yr,  # FIXED: map threshold_t_ha_yr -> threshold
        "compute_sensitivities": request.options.compute_sensitivities
    }
    
    try:
        logger.info("Starting parallel tasks: satellite imagery + backend RUSLE/ML")
        
        # Create async tasks
        satellite_task = asyncio.create_task(
            sentinel_client.fetch_satellite_image(geojson, request.options.date_range)
        )

        backend_task = asyncio.create_task(
            backend_client.call_backend_rusle(geojson, backend_options)  # FIXED: pass dict, not Pydantic model
        )
        
        # Wait for both to complete
        satellite_result, backend_result = await asyncio.gather(
            satellite_task,
            backend_task,
            return_exceptions=False
        )
        
        logger.info("✅ Both parallel tasks completed successfully")
        
    except asyncio.TimeoutError:
        logger.error("Backend computation timed out")
        raise HTTPException(
            status_code=504,
            detail="Computation timed out (>120s). Try a smaller polygon area."
        )
    except Exception as e:
        logger.error(f"Parallel execution failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Computation failed: {str(e)}"
        )
    
    
    # ========== STEP 4: CONSTRUCT RESPONSE (FIXED: match RUSLEResponse schema exactly) ==========
    try:
        computation_time = time.time() - start_time
        
        # FIXED: Use "hotspots" consistently (backend_result returns "hotspots")
        hotspots_list = backend_result.get('hotspots', [])

        # Normalize tile_urls so values are strings (schema expects Dict[str, str]).
        tile_urls_input = backend_result.get('tile_urls') if backend_result else None
        tile_urls_normalized = None
        if tile_urls_input:
            import json
            tile_urls_normalized = {
                k: (json.dumps(v) if not isinstance(v, str) else v)
                for k, v in tile_urls_input.items()
            }
        
        # Build response matching schemas.RUSLEResponse structure exactly
        response = schemas.RUSLEResponse(
            # Required fields from schema
            success=True,
            computation_time_sec=round(computation_time, 2),
            # timestamp is auto-generated by schema default_factory
            
            # Polygon data
            polygon=geojson,
            polygon_metadata=schemas.PolygonMetadata(
                area_km2=validation_metadata['area_km2'],
                centroid=geojson['properties']['centroid'],
                bbox=geojson['properties']['bbox'],
                num_vertices=validation_metadata['num_vertices']
            ),
            
            # Satellite imagery
            satellite_image=satellite_result,
            
            # RUSLE results
            erosion=schemas.ErosionStats(**backend_result['erosion']),
            
            factors={
                factor_name: schemas.FactorStats(**factor_data)
                for factor_name, factor_data in backend_result['factors'].items()
            },
            
            # Hotspots (FIXED: map backend "hotspots" to schema "highlights")
            highlights=[
                schemas.Hotspot(**hotspot)
                for hotspot in hotspots_list
            ],
            num_hotspots=len(hotspots_list),
            
            # Validation (if computed)
            validation=schemas.ValidationMetrics(**backend_result['validation']) 
                if backend_result.get('validation') else None,
            
            # Optional tile URLs (normalized)
            tile_urls=tile_urls_normalized
        )
        
        logger.info(f"✅ RUSLE computation completed in {computation_time:.2f}s")
        logger.info(f"   Mean erosion: {response.erosion.mean:.1f} t/ha/yr")
        logger.info(f"   Hotspots: {response.num_hotspots}")
        
        return response
        
    except Exception as e:
        logger.error(f"Response construction failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to construct response: {str(e)}"
        )


# ========== UTILITY ENDPOINTS ==========

@app.get("/api/factors")
async def get_factor_info():
    """Get information about RUSLE factors"""
    return {
        "factors": {
            "R": {
                "name": "Rainfall Erosivity",
                "unit": "MJ mm ha⁻¹ h⁻¹ yr⁻¹",
                "source": "CHIRPS precipitation or ESDAC GloREDa"
            },
            "K": {
                "name": "Soil Erodibility",
                "unit": "t ha h ha⁻¹ MJ⁻¹ mm⁻¹",
                "source": "ESDAC Global K-factor (SoilGrids-derived)"
            },
            "LS": {
                "name": "Slope Length & Steepness",
                "unit": "dimensionless",
                "source": "SRTM 30m DEM"
            },
            "C": {
                "name": "Cover Management",
                "unit": "dimensionless (0-1)",
                "source": "ESA WorldCover + Sentinel-2 NDVI"
            },
            "P": {
                "name": "Support Practices",
                "unit": "dimensionless (0-1)",
                "source": "User configuration (default: 1.0)"
            }
        },
        "equation": "A = R × K × LS × C × P",
        "output_unit": "t/ha/yr"
    }


@app.get("/api/limits")
async def get_computation_limits():
    """Get API computation limits"""
    return {
        "max_polygon_area_km2": 1000,
        "max_vertices": 1000,
        "max_date_range_days": 730,
        "computation_timeout_sec": 120,
        "rate_limit": "100 requests/hour"
    }


# ========== SERVER STARTUP ==========

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=os.getenv("ENV", "production") == "development",
        log_level="info"
    )
