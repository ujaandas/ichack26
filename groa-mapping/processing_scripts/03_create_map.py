import sys
import os
import pandas as pd
import numpy as np
import pickle
from unittest.mock import MagicMock

# Add repo root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
repo_root = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.append(repo_root)

# Mock GDAL and Rasterio
sys.modules['gdal'] = MagicMock()
sys.modules['osgeo'] = MagicMock()
sys.modules['osgeo.gdal'] = MagicMock()
sys.modules['rasterio'] = MagicMock()

from MappingGlobalCarbon.gfw_forestlearn.fl_regression import ForestLearn
from global_land_mask import globe

def create_map():
    print("Generating synthetic global grid...")
    # Create a coarse grid (e.g. 1 degree resolution) for demonstration
    lats = np.arange(-50, 80, 1.0)
    lons = np.arange(-180, 180, 1.0)
    
    lon_grid, lat_grid = np.meshgrid(lons, lats)
    
    # Flatten
    df_grid = pd.DataFrame({
        'lat_dec': lat_grid.flatten(),
        'long_dec': lon_grid.flatten()
    })
    
    print(f"Total grid points before masking: {len(df_grid)}")
    
    # Filter for land points only
    print("Filtering for land points...")
    is_on_land = globe.is_land(df_grid['lat_dec'], df_grid['long_dec'])
    df_grid = df_grid[is_on_land].copy()
    
    print(f"Grid points on land: {len(df_grid)}")
    
    # Generate synthetic covariates based on training data ranges
    # In reality, we would read these from raster files
    
    # Simple synthetic logic:
    # Temp decreases with latitude
    df_grid['AMT'] = 25 - 0.5 * np.abs(df_grid['lat_dec']) + np.random.normal(0, 2, len(df_grid))
    
    # Precip is random but higher in tropics
    df_grid['AMP'] = np.where(np.abs(df_grid['lat_dec']) < 20, 
                              np.random.normal(2000, 500, len(df_grid)), 
                              np.random.normal(800, 300, len(df_grid)))
    df_grid['AMP'] = df_grid['AMP'].clip(lower=0)
    
    # Soil is random category
    soils = ['Acrisols', 'Alfisols', 'Inceptisols', 'Oxisols', 'Ultisols']
    df_grid['soil.classification'] = np.random.choice(soils, len(df_grid))
    
    print("Loading model...")
    model_path = os.path.join(repo_root, "outputs", "groa_model.pkl")
    
    # Load model
    with open(model_path, 'rb') as f:
        model = pickle.load(f)
        
    print("Predicting carbon accumulation rates...")
    # Predict
    # The model pipeline expects the columns in specific order/names?
    # The pipeline uses ColumnTransformer which selects by name.
    # So as long as dataframe has columns, it should work.
    
    # Predict
    predictions = model.predict(df_grid)
    
    df_grid['predicted_rate'] = predictions
    
    # Save
    output_path = os.path.join(repo_root, "outputs", "global_map_predictions.csv")
    df_grid.to_csv(output_path, index=False)
    
    print(f"Map predictions saved to {output_path}")
    print("Head of predictions:")
    print(df_grid.head())

if __name__ == "__main__":
    create_map()
