# GROA Prediction Integration Guide

This guide explains how to integrate the Point Prediction functionality into backend services or other applications.

## Overview

The prediction module (`processing_scripts/06_predict_point.py`) allows you to get a Carbon Accumulation Potential prediction for any specific latitude and longitude.

Unlike the static global map, this script **fetches real-time environmental data** to ensure accuracy:
1.  **Weather**: Fetches 10-year historical average (2014-2023) for Temperature and Precipitation from the [Open-Meteo API](https://open-meteo.com/).
2.  **Soil**: Fetches the most probable soil classification from the [ISRIC SoilGrids API](https://rest.isric.org/).

## Method 1: Command Line Interface (CLI)

You can run the script as a subprocess. This is useful for quick testing or loosely coupled integrations.

### Usage
```bash
poetry run python processing_scripts/06_predict_point.py <LATITUDE> <LONGITUDE>
```

### Example
```bash
poetry run python processing_scripts/06_predict_point.py 51.60 -0.35
```

### Output Format
The script prints a human-readable report to `stdout`. You would need to parse this output if calling from another language.

```text
Analyzing Carbon Potential for: Lat 51.6, Lon -0.35...
Fetching real climate data from Open-Meteo API (2014-2023)...
Fetching real soil data from ISRIC SoilGrids API...

========================================
LOCATION REPORT: 51.6, -0.35
========================================
Climate Data (2014-2023 Average):
  - Annual Mean Temp:   10.9 °C
  - Annual Mean Precip: 741 mm
Soil Context:
  - Classification:     Luvisols
----------------------------------------
PREDICTED CARBON ACCUMULATION RATE:
  1.5514 Mg C ha-1 yr-1
========================================
```

## Method 2: Python Import (Recommended for Backend)

For a Python backend (e.g., FastAPI, Flask, Django), you should import the function directly to get structured data.

### 1. Ensure `groa-mapping` is in your Python Path
You may need to add the directory to `sys.path` or install the package in editable mode.

### 2. Import and Use
You can modify `processing_scripts/06_predict_point.py` to return a dictionary instead of printing, or wrap the logic as shown below:

```python
import sys
import os

# Add groa-mapping to path if necessary
sys.path.append("/path/to/groa-mapping")

from processing_scripts.06_predict_point import predict_for_location

# Note: Currently predict_for_location prints to stdout. 
# You may want to refactor the script to return a dict:

def get_carbon_prediction(lat, lon):
    # ... (logic from script) ...
    return {
        "latitude": lat,
        "longitude": lon,
        "climate": {
            "annual_mean_temp_c": real_amt,
            "annual_mean_precip_mm": real_amp
        },
        "soil": {
            "classification": soil_type
        },
        "prediction": {
            "rate_mg_c_ha_yr": prediction,
            "units": "Mg C ha-1 yr-1"
        }
    }
```

## External APIs Used

The accuracy of the point prediction depends on these external services:

| Data Point | Source | API Endpoint |
|------------|--------|--------------|
| **Temperature & Precip** | Open-Meteo | `https://archive-api.open-meteo.com/v1/archive` |
| **Soil Type** | ISRIC SoilGrids | `https://rest.isric.org/soilgrids/v2.0/classification/query` |

> **Note**: These APIs are free for non-commercial use but have rate limits. If integrating into a high-traffic production app, consider caching results or setting up your own data mirrors.
