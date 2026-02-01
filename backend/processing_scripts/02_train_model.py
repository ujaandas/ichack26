import sys
import os
import pandas as pd
import pickle

# Add repo root to path to import MappingGlobalCarbon
current_dir = os.path.dirname(os.path.abspath(__file__))
repo_root = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.append(repo_root)

# Mock GDAL since we don't need it for training and it's hard to install
from unittest.mock import MagicMock
sys.modules['gdal'] = MagicMock()
sys.modules['osgeo'] = MagicMock()
sys.modules['osgeo.gdal'] = MagicMock()
sys.modules['rasterio'] = MagicMock()

from MappingGlobalCarbon.gfw_forestlearn.fl_regression import ForestLearn

def train_model():
    print("Loading training data...")
    data_path = os.path.join(repo_root, "outputs", "training_data_basic.csv")
    df = pd.read_csv(data_path)
    
    print(f"Data loaded: {len(df)} records")
    
    # Define features
    predictors = ['AMT', 'AMP', 'soil.classification']
    y_column = 'accumulation_rate'
    xy = ['long_dec', 'lat_dec']
    one_hot_feats = ['soil.classification']
    
    print("Initializing ForestLearn...")
    # Initialize ForestLearn
    fl = ForestLearn(
        predictors=predictors,
        y_column=y_column,
        xy=xy,
        one_hot_feats=one_hot_feats
    )
    
    # Setup model pipeline (Random Forest with Scaling)
    print("Setting up model pipeline...")
    fl.setup_rf_model_scale()
    
    # Train model
    print("Training model (this may take a moment)...")
    # We can use fit_model_with_params directly if we don't want to tune
    # But let's try a simple fit first. 
    # The class doesn't have a simple 'fit' method exposed directly in the same way as 'tune',
    # but 'fit_model_with_params' fits the model.
    # However, it expects 'in_params' or 'in_modelfilename'. 
    # Let's look at the code for 'fit_model_with_params':
    # if (in_params is None) and (in_modelfilename is None): sys.exit...
    
    # So we need to provide params. 
    # Or we can use 'tune_param_set' to find best params.
    
    # Let's define a small param grid to tune (or just one set to be fast)
    params = {
        'learn__n_estimators': [100],
        'learn__max_depth': [10, None]
    }
    
    model_output = os.path.join(repo_root, "outputs", "groa_model.pkl")
    cv_results = os.path.join(repo_root, "outputs", "cv_results.csv")
    
    print("Tuning and fitting...")
    fl.tune_param_set(
        train=df,
        params=params,
        out_modelfilename=model_output,
        cv_results_filename=cv_results,
        k=3, # 3-fold CV
        n_jobs=1 # Use 1 job to avoid multiprocessing issues in this environment
    )
    
    print(f"Model saved to {model_output}")
    print(f"Best params: {fl.best_params}")

if __name__ == "__main__":
    train_model()
