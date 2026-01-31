"""
Backend Client Service
Communicates with /backend service for RUSLE computation and ML model inference
Handles two separate API calls:
1. /backend/api/rusle/compute - RUSLE factor computation and erosion stats
2. /backend/api/ml/hotspots - ML model for hotspot flagging and classification
Merges both responses into unified result for FastAPI
"""

import httpx
import os
import asyncio
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


# ========== CONFIGURATION ==========

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8001")
RUSLE_ENDPOINT = f"{BACKEND_URL}/api/rusle/compute"
ML_ENDPOINT = f"{BACKEND_URL}/api/ml/hotspots"
HEALTH_ENDPOINT = f"{BACKEND_URL}/health"

# Timeouts (in seconds)
RUSLE_TIMEOUT = 120.0  # RUSLE can take 1-2 minutes for GEE processing
ML_TIMEOUT = 30.0      # ML inference should be faster
HEALTH_TIMEOUT = 5.0

# Retry configuration
MAX_RETRIES = 2
RETRY_BACKOFF = 2.0  # seconds


# ========== MAIN FUNCTION ==========

async def call_backend_rusle(geojson: Dict, options: Dict) -> Dict:
    """
    Call backend RUSLE and ML services, merge results
    
    Makes two parallel requests:
    1. RUSLE computation service (GEE-based factor calculation)
    2. ML model service (hotspot classification and reason flagging)
    
    Args:
        geojson: Parsed polygon GeoJSON from coordinate_parser
        options: User options dict:
            {
                "p_toggle": bool,
                "threshold": float,
                "compute_sensitivities": bool
            }
    
    Returns:
        Merged result dict:
        {
            "erosion": {...},           # From RUSLE service
            "factors": {...},           # From RUSLE service
            "validation": {...},        # From RUSLE service
            "tile_urls": {...},         # From RUSLE service
            "hotspots": [...],          # From ML service
            "hotspot_summary": {...}    # From ML service
        }
    
    Raises:
        HTTPException: If either service fails
    """
    logger.info(f"Calling backend services at {BACKEND_URL}")
    
    # Prepare payloads for both services
    rusle_payload = {
        "geojson": geojson,
        "options": {
            "p_toggle": options.get("p_toggle", False),
            "compute_sensitivities": options.get("compute_sensitivities", True)
        }
    }
    
    ml_payload = {
        "geojson": geojson,
        "threshold_t_ha_yr": options.get("threshold", 20.0)
    }
    
    # Execute both calls in parallel
    try:
        rusle_task = asyncio.create_task(
            call_rusle_service(rusle_payload)
        )
        
        ml_task = asyncio.create_task(
            call_ml_service(ml_payload)
        )
        
        logger.info("Waiting for RUSLE and ML services to complete...")
        
        # Wait for both (raises first exception if any fail)
        rusle_result, ml_result = await asyncio.gather(
            rusle_task,
            ml_task,
            return_exceptions=False
        )
        
        logger.info("✅ Both backend services completed successfully")
        
    except Exception as e:
        logger.error(f"Backend service call failed: {e}")
        raise
    
    # Merge results
    merged_result = merge_results(rusle_result, ml_result, geojson)
    
    logger.info(
        f"Merged results: "
        f"mean_erosion={merged_result['erosion']['mean']:.2f} t/ha/yr, "
        f"hotspots={len(merged_result['hotspots'])}"
    )
    
    return merged_result


# ========== INDIVIDUAL SERVICE CALLS ==========

async def call_rusle_service(payload: Dict) -> Dict:
    """
    Call RUSLE computation service
    Returns erosion stats, factor data, and validation metrics
    
    Args:
        payload: Request payload with geojson and options
    
    Returns:
        RUSLE service response:
        {
            "erosion": {
                "mean": 12.4,
                "max": 45.2,
                "min": 0.3,
                "stddev": 8.7,
                "p50": 9.1,
                "p95": 28.3
            },
            "factors": {
                "R": {"mean": 1850, "stddev": 120, "min": 1620, "max": 2100, "unit": "..."},
                "K": {...},
                "LS": {...},
                "C": {...},
                "P": {...}
            },
            "validation": {
                "high_veg_reduction_pct": 68.2,
                "flat_terrain_reduction_pct": 85.1,
                "bare_soil_increase_pct": 230.5,
                "model_valid": true
            },
            "tile_urls": {
                "erosion_risk": "https://earthengine.googleapis.com/...",
                "factors": {...}
            }
        }
    """
    logger.info("Calling RUSLE computation service...")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                RUSLE_ENDPOINT,
                json=payload,
                timeout=RUSLE_TIMEOUT
            )
            
            # Handle errors
            if response.status_code == 504:
                raise Exception(
                    "RUSLE computation timed out. Try a smaller polygon or shorter date range."
                )
            
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"✅ RUSLE service completed: mean erosion = {result['erosion']['mean']:.2f} t/ha/yr")
            
            return result
            
    except httpx.TimeoutException:
        logger.error(f"RUSLE service timeout after {RUSLE_TIMEOUT}s")
        raise Exception(
            f"RUSLE computation timed out after {RUSLE_TIMEOUT}s. "
            f"The polygon may be too large or GEE is slow. Try reducing area."
        )
    
    except httpx.HTTPStatusError as e:
        logger.error(f"RUSLE service HTTP error {e.response.status_code}: {e.response.text}")
        raise Exception(
            f"RUSLE service error ({e.response.status_code}): {e.response.text}"
        )
    
    except Exception as e:
        logger.error(f"RUSLE service call failed: {e}")
        raise Exception(f"Failed to call RUSLE service: {str(e)}")


async def call_ml_service(payload: Dict) -> Dict:
    """
    Call ML hotspot classification service
    Returns flagged high-risk areas with reasons
    
    Args:
        payload: Request payload with geojson and threshold
    
    Returns:
        ML service response:
        {
            "hotspots": [
                {
                    "id": "hotspot_1",
                    "geometry": {"type": "Polygon", "coordinates": [...]},
                    "properties": {
                        "area_ha": 3.2,
                        "mean_erosion": 38.5,
                        "max_erosion": 52.1,
                        "dominant_factor": "LS"
                    },
                    "reason": "Steep slope (LS > 10) + Low vegetation cover (C > 0.15)",
                    "severity": "high",
                    "confidence": 0.89
                },
                ...
            ],
            "summary": {
                "total_hotspots": 3,
                "total_high_risk_area_ha": 8.7,
                "severity_distribution": {
                    "low": 0,
                    "moderate": 1,
                    "high": 2,
                    "critical": 0
                },
                "dominant_factors": ["LS", "C", "R"]
            }
        }
    """
    logger.info("Calling ML hotspot classification service...")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                ML_ENDPOINT,
                json=payload,
                timeout=ML_TIMEOUT
            )
            
            response.raise_for_status()
            
            result = response.json()
            num_hotspots = len(result.get('hotspots', []))
            logger.info(f"✅ ML service completed: {num_hotspots} hotspots identified")
            
            return result
            
    except httpx.TimeoutException:
        logger.error(f"ML service timeout after {ML_TIMEOUT}s")
        # ML is optional - return empty result instead of failing
        logger.warning("Continuing without ML hotspot flagging")
        return {
            "hotspots": [],
            "summary": {
                "total_hotspots": 0,
                "error": "ML service timeout"
            }
        }
    
    except httpx.HTTPStatusError as e:
        logger.error(f"ML service HTTP error {e.response.status_code}: {e.response.text}")
        # ML is optional - return empty result
        logger.warning("Continuing without ML hotspot flagging")
        return {
            "hotspots": [],
            "summary": {
                "total_hotspots": 0,
                "error": f"ML service error: {e.response.status_code}"
            }
        }
    
    except Exception as e:
        logger.error(f"ML service call failed: {e}")
        # ML is optional - return empty result
        logger.warning("Continuing without ML hotspot flagging")
        return {
            "hotspots": [],
            "summary": {
                "total_hotspots": 0,
                "error": str(e)
            }
        }


# ========== RESULT MERGING ==========

def merge_results(rusle_result: Dict, ml_result: Dict, geojson: Dict) -> Dict:
    """
    Merge RUSLE and ML service results into unified response
    
    Args:
        rusle_result: Response from RUSLE service
        ml_result: Response from ML service
        geojson: Original polygon GeoJSON (for metadata)
    
    Returns:
        Merged result dictionary
    """
    logger.debug("Merging RUSLE and ML results...")
    
    # Start with RUSLE results
    merged = {
        "erosion": rusle_result.get("erosion", {}),
        "factors": rusle_result.get("factors", {}),
        "validation": rusle_result.get("validation"),
        "tile_urls": rusle_result.get("tile_urls"),
    }
    
    # Add ML results
    merged["hotspots"] = ml_result.get("hotspots", [])
    merged["hotspot_summary"] = ml_result.get("summary", {})
    
    # Enrich hotspots with RUSLE factor data if needed
    merged["hotspots"] = enrich_hotspots_with_factors(
        hotspots=merged["hotspots"],
        factors=merged["factors"]
    )
    
    # Add cross-validation (check if hotspots align with high RUSLE values)
    merged["cross_validation"] = validate_hotspots_against_rusle(
        hotspots=merged["hotspots"],
        erosion_stats=merged["erosion"]
    )
    
    return merged


def enrich_hotspots_with_factors(hotspots: List[Dict], factors: Dict) -> List[Dict]:
    """
    Add RUSLE factor context to each hotspot
    Helps explain why ML flagged each area
    
    Args:
        hotspots: List of hotspot dicts from ML service
        factors: Factor statistics from RUSLE service
    
    Returns:
        Enriched hotspot list
    """
    if not hotspots or not factors:
        return hotspots
    
    # Add global factor context to each hotspot
    for hotspot in hotspots:
        # Compare hotspot's dominant factor to overall mean
        dominant = hotspot.get("properties", {}).get("dominant_factor")
        if dominant and dominant in factors:
            factor_mean = factors[dominant].get("mean", 0)
            hotspot["factor_context"] = {
                "dominant_factor": dominant,
                "global_mean": factor_mean,
                "description": get_factor_description(dominant)
            }
    
    return hotspots


def get_factor_description(factor_code: str) -> str:
    """Get human-readable description for RUSLE factor"""
    descriptions = {
        "R": "High rainfall intensity",
        "K": "Erodible soil type",
        "LS": "Steep or long slope",
        "C": "Low vegetation cover",
        "P": "No conservation practices"
    }
    return descriptions.get(factor_code, "Unknown factor")


def validate_hotspots_against_rusle(hotspots: List[Dict], erosion_stats: Dict) -> Dict:
    """
    Cross-validate ML hotspots against RUSLE statistics
    Checks if ML-flagged areas actually have high erosion in RUSLE output
    
    Args:
        hotspots: List of ML-identified hotspots
        erosion_stats: Overall erosion statistics from RUSLE
    
    Returns:
        Validation metrics dict
    """
    if not hotspots:
        return {
            "validated": True,
            "notes": "No hotspots to validate"
        }
    
    p95_threshold = erosion_stats.get("p95", 20)
    
    # Check if hotspot erosion values are actually high
    validated_count = 0
    for hotspot in hotspots:
        mean_erosion = hotspot.get("properties", {}).get("mean_erosion", 0)
        if mean_erosion >= p95_threshold * 0.8:  # At least 80% of p95
            validated_count += 1
    
    validation_rate = validated_count / len(hotspots) if hotspots else 0
    
    return {
        "validated": validation_rate >= 0.7,  # At least 70% should validate
        "validation_rate": round(validation_rate, 2),
        "validated_count": validated_count,
        "total_count": len(hotspots),
        "notes": f"{validated_count}/{len(hotspots)} hotspots have erosion >= {p95_threshold*0.8:.1f} t/ha/yr"
    }


# ========== RETRY LOGIC ==========

async def call_with_retry(
    func,
    *args,
    max_retries: int = MAX_RETRIES,
    backoff: float = RETRY_BACKOFF,
    **kwargs
):
    """
    Call async function with exponential backoff retry
    
    Args:
        func: Async function to call
        args: Positional arguments
        max_retries: Maximum retry attempts
        backoff: Initial backoff time in seconds
        kwargs: Keyword arguments
    
    Returns:
        Function result
    
    Raises:
        Exception: If all retries fail
    """
    for attempt in range(max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            if attempt == max_retries:
                logger.error(f"All {max_retries} retry attempts failed")
                raise
            
            wait_time = backoff * (2 ** attempt)
            logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
            await asyncio.sleep(wait_time)


# ========== HEALTH CHECK ==========

async def test_backend_connection() -> bool:
    """
    Test backend connectivity on FastAPI startup
    Checks both RUSLE and ML service health endpoints
    
    Returns:
        True if both services are healthy
    
    Raises:
        Exception: If connection fails
    """
    logger.info("Testing backend service connectivity...")
    
    try:
        async with httpx.AsyncClient() as client:
            # Check main health endpoint
            response = await client.get(
                HEALTH_ENDPOINT,
                timeout=HEALTH_TIMEOUT
            )
            response.raise_for_status()
            
            health_data = response.json()
            logger.info(f"✅ Backend health check passed: {health_data}")
            
            # Check if both services are reported as healthy
            if health_data.get("rusle_service") == "healthy" and \
               health_data.get("ml_service") == "healthy":
                logger.info("✅ Both RUSLE and ML services are healthy")
                return True
            else:
                logger.warning("⚠️  Some backend services may be unavailable")
                logger.warning(f"   RUSLE: {health_data.get('rusle_service', 'unknown')}")
                logger.warning(f"   ML: {health_data.get('ml_service', 'unknown')}")
                return True  # Don't fail startup, just warn
            
    except httpx.TimeoutException:
        logger.error(f"Backend health check timed out after {HEALTH_TIMEOUT}s")
        raise Exception(
            f"Backend not responding at {BACKEND_URL}. "
            f"Ensure backend service is running."
        )
    
    except httpx.HTTPStatusError as e:
        logger.error(f"Backend health check failed: {e.response.status_code}")
        raise Exception(
            f"Backend health check failed ({e.response.status_code}). "
            f"Backend may be starting up or misconfigured."
        )
    
    except Exception as e:
        logger.error(f"Backend connection test failed: {e}")
        raise Exception(f"Cannot connect to backend at {BACKEND_URL}: {str(e)}")


# ========== UTILITY FUNCTIONS ==========

def get_backend_info() -> Dict:
    """
    Get backend service information (for debugging)
    
    Returns:
        Backend configuration dict
    """
    return {
        "backend_url": BACKEND_URL,
        "rusle_endpoint": RUSLE_ENDPOINT,
        "ml_endpoint": ML_ENDPOINT,
        "rusle_timeout": RUSLE_TIMEOUT,
        "ml_timeout": ML_TIMEOUT,
        "max_retries": MAX_RETRIES
    }


async def get_backend_status() -> Dict:
    """
    Get detailed backend service status
    Can be exposed via FastAPI endpoint for monitoring
    
    Returns:
        Status dict with service health
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BACKEND_URL}/status",
                timeout=HEALTH_TIMEOUT
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
