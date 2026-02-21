"""
Crop Prediction Client Service
Calls the crop_predict model in backend for crop yield forecasting
"""

import sys
import os
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Add backend to Python path to import crop_predict
# Backend is mounted at /app/backend in middleware container
BACKEND_PATH = "/app/backend"
if BACKEND_PATH not in sys.path:
    sys.path.insert(0, BACKEND_PATH)


async def predict_crop_yield(
    centroid_lon: float,
    centroid_lat: float,
    week: int = 25,
    crop_name: str = "Soft wheat"
) -> Optional[Dict]:
    """
    Predict crop yield for a polygon's centroid location
    
    Args:
        centroid_lon: Polygon centroid longitude
        centroid_lat: Polygon centroid latitude
        week: Week of year (20-30 recommended, default 25)
        crop_name: Crop type - "Soft wheat", "Durum wheat", or "Total wheat"
    
    Returns:
        Dict with prediction results or None if prediction fails:
        {
            "yield_t_ha": float,  # tonnes per hectare
            "crop_name": str,
            "location": [lon, lat],
            "error": str  # if prediction failed
        }
    """
    try:
        # Check if location is in Europe
        # Approximate Europe boundaries:
        # Latitude: 35°N to 71°N
        # Longitude: -10°W to 40°E
        if not (35 <= centroid_lat <= 71 and -10 <= centroid_lon <= 40):
            logger.info(f"🌾 Location ({centroid_lat:.2f}, {centroid_lon:.2f}) outside Europe - skipping crop prediction")
            return None
        
        # Import crop_predict module
        from crop_predict.predict import predict_yield
        
        logger.info(f"🌾 Predicting {crop_name} yield at ({centroid_lat:.2f}, {centroid_lon:.2f}), week {week}")
        
        # Backend is mounted at /app/backend in middleware container
        backend_base = "/app/backend"
        
        # Call prediction function with absolute paths
        prediction = predict_yield(
            longitude=centroid_lon,
            latitude=centroid_lat,
            week=week,
            crop_name=crop_name,
            model_path=os.path.join(backend_base, "crop_predict/model/rf_model.joblib"),
            le_path=os.path.join(backend_base, "crop_predict/model/label_encoder.joblib"),
            data_path=os.path.join(backend_base, "crop_predict/Model_A.csv"),
            feature_path=os.path.join(backend_base, "crop_predict/model/features.txt")
        )
        
        if prediction is None:
            logger.warning("Crop prediction returned None (out of coverage or model error)")
            return {
                "yield_t_ha": None,
                "crop_name": crop_name,
                "location": [centroid_lon, centroid_lat],
                "error": "Location outside Europe coverage or model files missing"
            }
        
        logger.info(f"✅ Crop yield prediction: {prediction:.2f} t/ha")
        
        return {
            "yield_t_ha": round(float(prediction), 2),
            "crop_name": crop_name,
            "location": [centroid_lon, centroid_lat],
            "error": None
        }
        
    except ImportError as e:
        logger.error(f"Failed to import crop_predict module: {e}")
        return {
            "yield_t_ha": None,
            "crop_name": crop_name,
            "location": [centroid_lon, centroid_lat],
            "error": f"Crop prediction module not available: {str(e)}"
        }
    
    except Exception as e:
        logger.error(f"Crop prediction failed: {e}", exc_info=True)
        return {
            "yield_t_ha": None,
            "crop_name": crop_name,
            "location": [centroid_lon, centroid_lat],
            "error": str(e)
        }
