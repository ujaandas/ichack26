import pandas as pd
import numpy as np
import joblib
from math import radians, cos, sin, asin, sqrt
import os


def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate distance between two geographic coordinates in kilometers
    """
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    km = 6371 * c
    return km


def find_nearest_points(df, latitude, longitude, n_points=5):
    """
    Find the nearest n points to the given coordinates
    
    Args:
        df: DataFrame containing TH_LAT and TH_LONG fields
        latitude: Target latitude
        longitude: Target longitude
        n_points: Number of nearest points to find
        
    Returns:
        DataFrame of the nearest n points
    """
    df = df.copy()
    df['distance'] = df.apply(
        lambda row: haversine(row['TH_LONG'], row['TH_LAT'], longitude, latitude),
        axis=1
    )
    
    nearest_points = df.nsmallest(n_points, 'distance')
    return nearest_points


def extract_band_features(nearest_points):
    """
    Extract average band features from nearest points
    
    Args:
        nearest_points: DataFrame of nearest points
        
    Returns:
        Dictionary of average band features
    """
    band_cols = ['B01', 'B02', 'B03', 'B04', 'B05', 
                 'B06', 'B07', 'B08', 'B8A', 'B09', 
                 'B11', 'B12']
    
    band_features = {}
    for band in band_cols:
        if band in nearest_points.columns:
            band_features[band] = nearest_points[band].mean()
        else:
            band_features[band] = 0
            
    return band_features

def predict_yield(longitude, latitude, week, crop_name, 
                  model_path="src/model/rf_model.joblib",
                  le_path="src/model/label_encoder.joblib",
                  data_path="src/Model_A.csv",
                  feature_path="src/model/features.txt"):
    """
    Predict crop yield
    
    Args:
        longitude: Longitude
        latitude: Latitude
        week: Week of the year
        crop_name: Crop name
        model_path: Path to trained model
        le_path: Path to label encoder
        data_path: Path to Model_A data
        feature_path: Path to features list
        
    Returns:
        Predicted yield value
    """
    try:
        model = joblib.load(model_path)
        label_encoder = joblib.load(le_path)
    except FileNotFoundError as e:
        return None
    
    try:
        with open(feature_path, 'r') as f:
            feature_cols = [line.strip() for line in f.readlines()]
    except FileNotFoundError:
        feature_cols = ['B01', 'B02', 'B03', 'B04', 'B05', 
                        'B06', 'B07', 'B08', 'B8A', 'B09', 
                        'B11', 'B12', 'WEEK', 'CROP_NAME_ENCODED']
    
    try:
        df = pd.read_csv(data_path)
    except FileNotFoundError:
        return None
    
    nearest_points = find_nearest_points(df, latitude, longitude, n_points=5)
    
    band_features = extract_band_features(nearest_points)
    
    try:
        crop_encoded = label_encoder.transform([crop_name])[0]
    except ValueError:
        crop_encoded = 0
    
    input_features = {}
    for band in ['B01', 'B02', 'B03', 'B04', 'B05', 
                 'B06', 'B07', 'B08', 'B8A', 'B09', 
                 'B11', 'B12']:
        if band in feature_cols:
            input_features[band] = band_features.get(band, 0)
    
    input_features['WEEK'] = week
    input_features['CROP_NAME_ENCODED'] = crop_encoded
    
    feature_vector = []
    for feat in feature_cols:
        feature_vector.append(input_features.get(feat, 0))
    
    X = np.array([feature_vector])
    
    prediction = model.predict(X)[0]
    
    return prediction

if __name__ == "__main__":
    # 1. Description:
    # The function retrieves feature data for a given location by
    #  extracting historical data from a local dataset. The 
    # features are computed as the average of the five nearest 
    # points to the specified latitude and longitude.
    # Note that, due to data limitations, only historical data are
    #  currently available; real-time data cannot be accessed. In 
    # addition, the dataset only covers Europe. For this reason, 
    # the appropriate latitude–longitude resolution needs to be 
    # tested (e.g., 0.1 × 0.1 degree grids, 0.01 × 0.01 degree 
    # grids, or other resolutions), as the spatial density of the
    #  local dataset is currently uncertain.

    # 2. Week parameter:
    # A week parameter can be provided, representing the week 
    # number of the current year. Since most of the training data
    #  fall between weeks 20 and 30, it is recommended to use 
    # values within this range.

    # 3. crop_name can be "Soft wheat", "Durum wheat", "Total wheat"

    # 4. The latitude and longitude accepted by this function should represent the center of a region.

    # 5. The output is a single numerical value, with units of tonnes per hectare.
    
    prediction_1 = predict_yield(
        longitude=-0.125,
        latitude=51.519,
        week=21,
        crop_name="Soft wheat",
        model_path="crop_predict/model/rf_model.joblib",
        le_path="crop_predict/model/label_encoder.joblib",
        data_path="crop_predict/Model_A.csv",
        feature_path="crop_predict/model/features.txt"
    )

    print("Test Input 1 Prediction:", prediction_1)