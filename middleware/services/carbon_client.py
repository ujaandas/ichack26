"""
Carbon Sequestration Client Service
Calls the GROA (Global Reforestation Opportunity Assessment) model
for carbon accumulation potential predictions
"""

import sys
import os
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Add backend/app to Python path to import groa-mapping
BACKEND_APP_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../backend/app"))
if BACKEND_APP_PATH not in sys.path:
    sys.path.insert(0, BACKEND_APP_PATH)


async def predict_carbon_sequestration(
    centroid_lon: float,
    centroid_lat: float,
    polygon_coords: Optional[list] = None
) -> Optional[Dict]:
    """
    Predict carbon accumulation potential for forest regrowth
    Uses GeoTIFF raster data if available, falls back to GROA ML model
    
    Args:
        centroid_lon: Polygon centroid longitude
        centroid_lat: Polygon centroid latitude
        polygon_coords: Optional list of [lon, lat] coordinates for polygon analysis
    
    Returns:
        Dict with prediction results or None if prediction fails:
        {
            "carbon_rate_mg_ha_yr": float,  # Megagrams Carbon per hectare per year
            "location": [lon, lat],
            "climate": dict or None,
            "soil": dict or None,
            "coverage": str,  # "raster", "global", "fallback", or "error"
            "error": str  # if prediction failed
        }
    """
    try:
        logger.info(f"🌲 Predicting carbon sequestration at ({centroid_lat:.2f}, {centroid_lon:.2f})")
        
        # Try GeoTIFF raster analysis first (most accurate, pre-computed)
        if polygon_coords and len(polygon_coords) >= 3:
            try:
                sys.path.insert(0, "/app/backend/groa-mapping/processing_scripts")
                # Import from the actual filename
                import importlib.util
                spec = importlib.util.spec_from_file_location(
                    "analyze_polygon",
                    "/app/backend/groa-mapping/processing_scripts/10_analyze_polygon.py"
                )
                analyze_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(analyze_module)
                analyze_polygon = analyze_module.analyze_polygon
                
                logger.info("Using GeoTIFF raster data for carbon analysis...")
                result = analyze_polygon(polygon_coords)
                
                if result and "mean_rate" in result:
                    logger.info(f"✅ Carbon from raster: {result['mean_rate']:.4f} Mg C ha⁻¹ yr⁻¹ (area: {result.get('area_ha', 0):.2f} ha)")
                    return {
                        "carbon_rate_mg_ha_yr": result["mean_rate"],
                        "total_carbon_yr": result.get("total_carbon_yr"),
                        "area_ha": result.get("area_ha"),
                        "location": [centroid_lon, centroid_lat],
                        "climate": None,
                        "soil": None,
                        "error": None
                    }
            except Exception as e:
                logger.warning(f"GeoTIFF analysis failed, falling back to ML model: {e}")
        
        # Fallback to ML model prediction (point-based)
        import pandas as pd
        import pickle
        import json
        import urllib.request
        
        logger.info(f"🌲 Predicting carbon sequestration at ({centroid_lat:.2f}, {centroid_lon:.2f})")
        
        # Load model - backend is mounted at /app/backend in middleware container
        model_paths = [
            "/app/backend/groa-mapping/outputs/groa_model.pkl",  # Old location (pre-trained)
            "/app/backend/outputs/groa_model.pkl",  # New location
            "/app/backend/MappingGlobalCarbon/outputs/groa_model.pkl",  # Alternative
        ]
        
        model_path = None
        for path in model_paths:
            if os.path.exists(path):
                model_path = path
                logger.info(f"Found GROA model at: {path}")
                break
        
        if not model_path:
            logger.error(f"GROA model not found in any of: {model_paths}")
            return {
                "carbon_rate_mg_ha_yr": None,
                "total_carbon_yr": None,
                "area_ha": None,
                "location": [centroid_lon, centroid_lat],
                "climate": None,
                "soil": None,
                "error": "GROA model not found. Run training script first."
            }
        
        # Try to load model with error handling for sklearn/numpy version issues
        try:
            with open(model_path, 'rb') as f:
                model = pickle.load(f)
        except Exception as model_error:
            logger.error(f"Failed to load GROA model (sklearn/numpy version mismatch): {model_error}")
            return {
                "carbon_rate_mg_ha_yr": None,
                "total_carbon_yr": None,
                "area_ha": None,
                "location": [centroid_lon, centroid_lat],
                "climate": None,
                "soil": None,
                "error": f"Model loading failed: {str(model_error)}"
            }
        
        # Fetch real weather data from Open-Meteo API
        logger.info("Fetching climate data from Open-Meteo API...")
        start_date = "2014-01-01"
        end_date = "2023-12-31"
        weather_url = (
            f"https://archive-api.open-meteo.com/v1/archive?"
            f"latitude={centroid_lat}&longitude={centroid_lon}&"
            f"start_date={start_date}&end_date={end_date}&"
            f"daily=temperature_2m_mean,precipitation_sum&timezone=auto"
        )
        
        try:
            with urllib.request.urlopen(weather_url, timeout=10) as response:
                weather_data = json.loads(response.read().decode())
            
            temps = [t for t in weather_data["daily"]["temperature_2m_mean"] if t is not None]
            amt = sum(temps) / len(temps) if temps else (25 - 0.5 * abs(centroid_lat))
            
            precips = [p for p in weather_data["daily"]["precipitation_sum"] if p is not None]
            amp = sum(precips) / 10.0 if precips else 1000
            
            logger.info(f"✅ Climate data: {amt:.1f}°C, {amp:.0f}mm")
            
        except Exception as e:
            logger.warning(f"Weather API failed, using fallback: {e}")
            amt = 25 - 0.5 * abs(centroid_lat)
            amp = 1000
        
        # Fetch soil data from ISRIC SoilGrids API
        logger.info("Fetching soil data from ISRIC SoilGrids API...")
        soil_url = f"https://rest.isric.org/soilgrids/v2.0/classification/query?lon={centroid_lon}&lat={centroid_lat}&number_classes=1"
        
        try:
            with urllib.request.urlopen(soil_url, timeout=10) as response:
                soil_data = json.loads(response.read().decode())
            
            soil_type = soil_data.get("wrb_class_name", "Inceptisols")
            logger.info(f"✅ Soil type: {soil_type}")
            
        except Exception as e:
            logger.warning(f"Soil API failed, using fallback: {e}")
            soil_type = "Inceptisols"
        
        # Prepare input for model
        input_data = pd.DataFrame({
            'lat_dec': [centroid_lat],
            'long_dec': [centroid_lon],
            'AMT': [amt],
            'AMP': [amp],
            'soil.classification': [soil_type]
        })
        
        # Make prediction
        prediction = model.predict(input_data)[0]
        
        logger.info(f"✅ Carbon sequestration: {prediction:.4f} Mg C ha⁻¹ yr⁻¹")
        
        return {
            "carbon_rate_mg_ha_yr": round(float(prediction), 4),
            "total_carbon_yr": None,
            "area_ha": None,
            "location": [centroid_lon, centroid_lat],
            "climate": {
                "annual_mean_temp_c": round(amt, 1),
                "annual_mean_precip_mm": round(amp, 0)
            },
            "soil": {
                "classification": soil_type
            },
            "error": None
        }
        
    except ImportError as e:
        logger.error(f"Failed to import GROA dependencies: {e}")
        return {
            "carbon_rate_mg_ha_yr": None,
            "total_carbon_yr": None,
            "area_ha": None,
            "location": [centroid_lon, centroid_lat],
            "climate": None,
            "soil": None,
            "error": f"GROA module dependencies not available: {str(e)}"
        }
    
    except Exception as e:
        logger.error(f"Carbon prediction failed: {e}", exc_info=True)
        return {
            "carbon_rate_mg_ha_yr": None,
            "total_carbon_yr": None,
            "area_ha": None,
            "location": [centroid_lon, centroid_lat],
            "climate": None,
            "soil": None,
            "error": str(e)
        }
