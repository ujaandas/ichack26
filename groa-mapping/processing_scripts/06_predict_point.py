import sys
import os
import pandas as pd
import numpy as np
import pickle
import json
import urllib.request
from datetime import datetime
from sklearn.neighbors import NearestNeighbors

# Define paths
current_dir = os.path.dirname(os.path.abspath(__file__))
repo_root = os.path.abspath(os.path.join(current_dir, ".."))
OUTPUT_DIR = os.path.join(repo_root, "outputs")

def get_real_weather_data(lat, lon):
    """
    Fetches 10-year historical weather data from Open-Meteo API.
    """
    print("Fetching real climate data from Open-Meteo API (2014-2023)...")
    
    start_date = "2014-01-01"
    end_date = "2023-12-31"
    url = (f"https://archive-api.open-meteo.com/v1/archive?"
           f"latitude={lat}&longitude={lon}&"
           f"start_date={start_date}&end_date={end_date}&"
           f"daily=temperature_2m_mean,precipitation_sum&timezone=auto")
    
    try:
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())
            
        if "daily" not in data:
            print("Error: No daily data in API response.")
            return None, None
            
        temps = [t for t in data["daily"]["temperature_2m_mean"] if t is not None]
        amt = sum(temps) / len(temps) if temps else 0
        
        precips = [p for p in data["daily"]["precipitation_sum"] if p is not None]
        total_precip = sum(precips)
        amp = total_precip / 10.0 
        
        return amt, amp
        
    except Exception as e:
        print(f"Error fetching weather data: {e}")
        return None, None

def get_real_soil_data(lat, lon):
    """
    Fetches most probable soil type from ISRIC SoilGrids API.
    """
    print("Fetching real soil data from ISRIC SoilGrids API...")
    url = f"https://rest.isric.org/soilgrids/v2.0/classification/query?lon={lon}&lat={lat}&number_classes=1"
    
    try:
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())
            
        if "wrb_class_name" in data:
            return data["wrb_class_name"]
        else:
            print("Error: No soil class in API response.")
            return None
            
    except Exception as e:
        print(f"Error fetching soil data: {e}")
        return None

def predict_for_location(target_lat, target_lon):
    print(f"Analyzing Carbon Potential for: Lat {target_lat}, Lon {target_lon}...")
    
    # 1. Load the model
    model_path = os.path.join(repo_root, "outputs", "groa_model.pkl")
    if not os.path.exists(model_path):
        print("Error: Model not found. Run 02_train_model.py first.")
        return
        
    with open(model_path, 'rb') as f:
        model = pickle.load(f)

    # 2. Get Real Weather Data
    real_amt, real_amp = get_real_weather_data(target_lat, target_lon)
    if real_amt is None:
        real_amt = 25 - 0.5 * abs(target_lat)
        real_amp = 1000
    
    # 3. Get Real Soil Data
    real_soil = get_real_soil_data(target_lat, target_lon)
    
    if real_soil:
        soil_type = real_soil
    else:
        # Fallback to map lookup if API fails
        print("Using fallback soil from map...")
        map_path = os.path.join(OUTPUT_DIR, "global_map_predictions.csv")
        if os.path.exists(map_path):
            df_map = pd.read_csv(map_path)
            X = df_map[['lat_dec', 'long_dec']].values
            nbrs = NearestNeighbors(n_neighbors=1, algorithm='ball_tree').fit(X)
            distances, indices = nbrs.kneighbors([[target_lat, target_lon]])
            soil_type = df_map.iloc[indices[0][0]]['soil.classification']
        else:
            soil_type = 'Inceptisols'

    # 4. Prepare Input DataFrame
    input_data = pd.DataFrame({
        'lat_dec': [target_lat],
        'long_dec': [target_lon],
        'AMT': [real_amt],
        'AMP': [real_amp],
        'soil.classification': [soil_type]
    })
    
    # 5. Predict
    prediction = model.predict(input_data)[0]
    
    # 6. Output results
    print("\n" + "="*40)
    print(f"LOCATION REPORT: {target_lat}, {target_lon}")
    print("="*40)
    print(f"Climate Data (2014-2023 Average):")
    print(f"  - Annual Mean Temp:   {real_amt:.1f} °C")
    print(f"  - Annual Mean Precip: {real_amp:.0f} mm")
    print(f"Soil Context:")
    print(f"  - Classification:     {soil_type}")
    print("-" * 40)
    print(f"PREDICTED CARBON ACCUMULATION RATE:")
    print(f"  {prediction:.4f} Mg C ha-1 yr-1")
    print("="*40)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: poetry run python processing_scripts/06_predict_point.py <lat> <lon>")
    else:
        try:
            lat = float(sys.argv[1])
            lon = float(sys.argv[2])
            predict_for_location(lat, lon)
        except ValueError:
            print("Error: Latitude and Longitude must be numbers.")
