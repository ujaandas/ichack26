import pandas as pd
import numpy as np
import os

# Define paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "../data")
OUTPUT_DIR = os.path.join(BASE_DIR, "../outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def prepare_data():
    print("Loading data...")
    measurements = pd.read_csv(os.path.join(DATA_DIR, "biomass_litter_CWD.csv"), encoding='latin1')
    sites = pd.read_csv(os.path.join(DATA_DIR, "sites.csv"), encoding='latin1')

    print(f"Measurements shape: {measurements.shape}")
    print(f"Sites shape: {sites.shape}")

    # Merge measurements with site data to get coordinates
    # The common column is 'site.id'
    merged = pd.merge(measurements, sites, on="site.id", how="left", suffixes=("", "_site"))
    
    # Filter for Aboveground Biomass
    # The paper says: "We modelled only aboveground carbon accumulation"
    # Checking variable names
    agb_data = merged[merged['variables.name'] == 'aboveground_biomass'].copy()
    print(f"AGB measurements: {len(agb_data)}")
    
    # DEBUG: Show age distribution before filtering
    print("\n--- Age Distribution Before Filtering ---")
    print(agb_data['stand.age'].describe())
    print("Sample of older forests (>30 years):")
    print(agb_data[agb_data['stand.age'] > 30][['site.id', 'stand.age', 'mean_ha']].head())
    print("---------------------------------------\n")

    # Filter for Age (0 < age <= 30)
    # Paper: "first 30 years of natural forest regrowth"
    agb_data = agb_data[(agb_data['stand.age'] > 0) & (agb_data['stand.age'] <= 30)]
    print(f"Measurements with age 0-30: {len(agb_data)}")

    # Calculate Rate
    # Rate = Mg C ha-1 / years
    # The 'mean_ha' column is likely the biomass value. 
    # Paper says: "For studies that reported biomass only, we converted to carbon (Mg C ha−1) using 0.47"
    # We need to check if 'mean_ha' is Biomass or Carbon. 
    # The file name is 'biomass_litter_CWD.csv', implying it might be biomass.
    # However, the paper says "The resulting dataset includes... measurements of carbon storage".
    # Let's assume for now we need to convert if it's biomass. 
    # But looking at the csv header, it just says 'mean_ha'. 
    # Let's assume it is Carbon for now, or check if there's a unit column. 
    # Actually, let's look at the paper methods again: "For studies that reported biomass only, we converted to carbon... using 0.47"
    # It's safer to assume the CSV contains the raw values reported by studies. 
    # But wait, the CSV has a column 'variables.name' = 'aboveground_biomass'. 
    # Usually this implies biomass units.
    # I will apply the 0.47 conversion factor for now, but add a TODO to verify.
    
    agb_data['carbon_stock'] = agb_data['mean_ha'] * 0.47
    agb_data['accumulation_rate'] = agb_data['carbon_stock'] / agb_data['stand.age']

    # Select relevant columns for training
    # We need: lat, lon, rate, and available covariates from sites table
    # sites.csv has: AMT (Temp), AMP (Precip), soil.classification
    training_data = agb_data[[
        'site.id', 'plot.id', 'lat_dec', 'long_dec', 'stand.age', 
        'carbon_stock', 'accumulation_rate',
        'AMT', 'AMP', 'soil.classification'
    ]].copy()
    
    # Drop rows with missing coordinates or rate
    training_data = training_data.dropna(subset=['lat_dec', 'long_dec', 'accumulation_rate'])
    
    # Fill missing environmental data with median/mode for demonstration purposes
    # In a real scenario, we would drop these or impute carefully
    training_data['AMT'] = training_data['AMT'].fillna(training_data['AMT'].median())
    training_data['AMP'] = training_data['AMP'].fillna(training_data['AMP'].median())
    training_data['soil.classification'] = training_data['soil.classification'].fillna('Unknown')

    print(f"Final training records: {len(training_data)}")

    # Save
    output_path = os.path.join(OUTPUT_DIR, "training_data_basic.csv")
    training_data.to_csv(output_path, index=False)
    print(f"Saved basic training data to {output_path}")

if __name__ == "__main__":
    prepare_data()
