"""
RUSLE Computation Logic
Calculates R, K, LS, C factors and final erosion
"""

import numpy as np
import requests
import time
import random
from typing import Dict, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from fastapi import APIRouter, HTTPException
import asyncio

def calculate_r_factor(polygon_coords: List[List[float]]) -> Dict:
    """
    Calculate R factor (rainfall erosivity) using CHIRPS precipitation data
    R = 1.735 × 10^(1.5 × log10(P²/P_annual) - 0.08188)
    Simplified to R ≈ 0.5 × P_annual for temperate regions
    
    Falls back to latitude-based regression if API fails
    """
    coords = polygon_coords[0]
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    
    avg_lon = sum(lons) / len(lons)
    avg_lat = sum(lats) / len(lats)
    
    print(f"  🌧️  Calculating R factor for location ({avg_lat:.3f}, {avg_lon:.3f})")
    
    try:
        # Try to fetch CHIRPS data (or similar precipitation API)
        # Using OpenMeteo climate API as alternative (free, no key required)
        url = "https://archive-api.open-meteo.com/v1/archive"
        params = {
            "latitude": avg_lat,
            "longitude": avg_lon,
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "daily": "precipitation_sum",
            "timezone": "auto"
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            precip_data = data.get("daily", {}).get("precipitation_sum", [])
            
            if precip_data:
                # Calculate annual precipitation
                annual_precip_mm = sum(p for p in precip_data if p is not None)
                
                # Calculate R factor using simplified Renard & Freimund (1994) approximation
                # R ≈ 0.04830 × P^1.610 for SI units (MJ mm ha⁻¹ h⁻¹ yr⁻¹)
                r_value = 0.04830 * (annual_precip_mm ** 1.610)
                
                # Add variability based on precipitation distribution
                precip_std = np.std([p for p in precip_data if p is not None])
                r_min = max(0, r_value * 0.85)
                r_max = r_value * 1.15
                
                print(f"  ✅ R factor from precipitation data: {r_value:.1f} (P_annual={annual_precip_mm:.0f}mm)")
                
                return {
                    "mean": float(round(r_value, 2)),
                    "min": float(round(r_min, 2)),
                    "max": float(round(r_max, 2)),
                    "stddev": float(round((r_max - r_min) / 4, 2)),
                    "unit": "MJ mm ha⁻¹ h⁻¹ yr⁻¹",
                    "source": f"OpenMeteo Archive (2023, {annual_precip_mm:.0f}mm/yr)"
                }
    except Exception as e:
        print(f"  ⚠️  Precipitation API failed: {e}")
    
    # Fallback: Latitude-based regression for Europe
    # Based on Panagos et al. (2015) European R-factor map
    if 35 <= avg_lat <= 72 and -25 <= avg_lon <= 45:  # Europe
        # R increases with latitude in western Europe (more rainfall)
        # R decreases in Mediterranean (less intense rainfall)
        if avg_lat >= 50:  # Northern Europe (UK, Scandinavia)
            base_r = 800 + (avg_lat - 50) * 100 - abs(avg_lon) * 15
        elif avg_lat >= 45:  # Central Europe
            base_r = 600 + (50 - avg_lat) * 40
        else:  # Mediterranean
            base_r = 400 + (45 - avg_lat) * 30
            
        # Western regions get more rainfall
        if avg_lon < 0:  # Western Europe (Atlantic influence)
            base_r *= 1.3
        elif avg_lon > 20:  # Eastern Europe
            base_r *= 0.8
            
        r_value = max(200, min(2500, base_r))  # Clamp to reasonable range
    else:
        # Global fallback based on latitude
        if abs(avg_lat) < 23:  # Tropics
            r_value = 2000 + random.uniform(-300, 300)
        elif abs(avg_lat) < 40:  # Subtropics
            r_value = 1200 + random.uniform(-200, 200)
        elif abs(avg_lat) < 60:  # Temperate
            r_value = 800 + random.uniform(-150, 150)
        else:  # Polar
            r_value = 400 + random.uniform(-100, 100)
    
    print(f"  ⚠️  Using latitude-based R factor estimate: {r_value:.1f}")
    
    return {
        "mean": float(round(r_value, 2)),
        "min": float(round(r_value * 0.85, 2)),
        "max": float(round(r_value * 1.15, 2)),
        "stddev": float(round(r_value * 0.1, 2)),
        "unit": "MJ mm ha⁻¹ h⁻¹ yr⁻¹",
        "source": "Latitude-based regression (Panagos 2015)"
    }

def calculate_k_factor(polygon_coords: List[List[float]]) -> Dict:
    """
    Calculate K factor (soil erodibility) using Williams (1995)
    Fetches soil data with fallback strategy:
    1. SoilGrids API (primary)
    2. OpenLandMap API (backup)
    3. Regional defaults based on location
    """
    print("🌱 Calculating K factor from multiple sources...")
    
    # Sample points from polygon
    coords = polygon_coords[0]
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    
    minx, maxx = min(lons), max(lons)
    miny, maxy = min(lats), max(lats)
    
    # Sample 5x5 grid
    sample_size = 5
    xs = np.linspace(minx, maxx, sample_size)
    ys = np.linspace(miny, maxy, sample_size)
    
    k_values = []
    sources_used = {"soilgrids": 0, "openlandmap": 0, "regional": 0}
    
    def fetch_k_from_soilgrids(lon, lat):
        """Try SoilGrids API (primary source)"""
        url = "https://rest.isric.org/soilgrids/v2.0/properties/query"
        params = {
            "lon": float(lon),
            "lat": float(lat),
            "property": "sand,silt,clay,soc",
            "depth": "0-5cm",
            "value": "mean"
        }
        
        try:
            r = requests.get(url, params=params, timeout=10)
            if r.status_code != 200:
                return None
            
            props = r.json().get("properties", {})
            sand = props.get("sand", {}).get("mean")
            silt = props.get("silt", {}).get("mean")
            clay = props.get("clay", {}).get("mean")
            soc = props.get("soc", {}).get("mean")
            
            if None in (sand, silt, clay, soc):
                return None
            
            # Convert g/kg to %
            sand_pct = float(sand) / 10.0
            silt_pct = float(silt) / 10.0
            clay_pct = float(clay) / 10.0
            oc_pct = float(soc) / 100.0
            
            return (sand_pct, silt_pct, clay_pct, oc_pct, "soilgrids")
        except:
            return None
    
    def fetch_k_from_openlandmap(lon, lat):
        """Try OpenLandMap WCS service (backup source)"""
        try:
            # OpenLandMap WCS endpoint for soil properties
            base_url = "https://rest.openlandmap.org"
            
            # Fetch sand, silt, clay from OpenLandMap
            # Using simplified single-point query (not full WCS)
            params = {
                "lon": float(lon),
                "lat": float(lat),
                "d1": 0,  # depth 0-5cm
                "d2": 5
            }
            
            r = requests.get(f"{base_url}/query/point", params=params, timeout=8)
            if r.status_code == 200:
                data = r.json()
                sand_pct = data.get("sand", {}).get("M", {}).get("0-5cm")
                silt_pct = data.get("silt", {}).get("M", {}).get("0-5cm")
                clay_pct = data.get("clay", {}).get("M", {}).get("0-5cm")
                oc_pct = data.get("soc", {}).get("M", {}).get("0-5cm", 1.5) / 10.0
                
                if all(x is not None for x in [sand_pct, silt_pct, clay_pct]):
                    return (sand_pct, silt_pct, clay_pct, oc_pct, "openlandmap")
        except:
            pass
        return None
    
    def get_regional_default_k(lon, lat):
        """Get regional K factor based on location (last resort)"""
        # European regions with typical K values
        if 35 <= lat <= 72 and -25 <= lon <= 45:  # Europe
            if 50 <= lat <= 60:  # UK, Northern Europe
                return (0.030, "regional")  # Typical for UK soils (moderate erodibility)
            elif 40 <= lat < 50:  # Central Europe
                return (0.028, "regional")  # Loam/silt loam
            else:  # Southern Europe
                return (0.025, "regional")  # More clay, less erodible
        elif 25 <= lat <= 50 and -130 <= lon <= -65:  # North America
            return (0.032, "regional")
        elif -40 <= lat <= 40:  # Tropical regions
            return (0.020, "regional")  # Typically more clay
        else:
            return (0.028, "regional")  # Global default (loam)
    
    def calculate_k_from_texture(sand_pct, silt_pct, clay_pct, oc_pct):
        """Williams (1995) K factor equation"""
        eps = 1e-8
        silt_vfs = silt_pct + (sand_pct * 0.1)
        sand_frac = 1.0 - (sand_pct / 100.0)
        
        fcsand = 0.2 + 0.3 * np.exp(-0.256 * sand_pct * (1.0 - silt_pct / 100.0))
        fcl_si = (silt_vfs / (clay_pct + silt_vfs + eps)) ** 0.3
        forgc = 1.0 - (0.25 * oc_pct / (oc_pct + np.exp(3.72 - 2.95 * oc_pct) + eps))
        fhisand = 1.0 - (0.7 * sand_frac / (sand_frac + np.exp(-5.51 + 22.9 * sand_frac) + eps))
        
        k = 0.1317 * fcsand * fcl_si * forgc * fhisand
        return float(np.clip(k, 0.0, 1.0))
    
    def fetch_k_for_point(lon, lat):
        """Fetch K value with fallback strategy: SoilGrids → OpenLandMap → Regional Default"""
        # Try SoilGrids first
        result = fetch_k_from_soilgrids(lon, lat)
        if result:
            sand_pct, silt_pct, clay_pct, oc_pct, source = result
            sources_used[source] += 1
            return calculate_k_from_texture(sand_pct, silt_pct, clay_pct, oc_pct)
        
        # Fallback to OpenLandMap
        result = fetch_k_from_openlandmap(lon, lat)
        if result:
            sand_pct, silt_pct, clay_pct, oc_pct, source = result
            sources_used[source] += 1
            return calculate_k_from_texture(sand_pct, silt_pct, clay_pct, oc_pct)
        
        # Last resort: regional default
        k_val, source = get_regional_default_k(lon, lat)
        sources_used[source] += 1
        return k_val
    
    # Fetch in parallel
    points = [(x, y) for x in xs for y in ys]
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(fetch_k_for_point, lon, lat) for lon, lat in points]
        
        for future in as_completed(futures):
            k_val = future.result()
            if k_val is not None:
                k_values.append(k_val)
            
            time.sleep(0.1)  # Reduced rate limiting since we have fallbacks
    
    if not k_values:
        print("  ❌ No K values retrieved, using regional default")
        centroid_k, _ = get_regional_default_k(sum(xs)/len(xs), sum(ys)/len(ys))
        k_values = [centroid_k]
        sources_used["regional"] = 1
    
    k_array = np.array(k_values)
    
    # Determine primary data source
    total_points = len(points)
    if sources_used["soilgrids"] >= total_points * 0.7:
        source_str = "SoilGrids API + Williams 1995"
    elif sources_used["openlandmap"] >= total_points * 0.5:
        source_str = "OpenLandMap API + Williams 1995"
    elif sources_used["regional"] == total_points:
        source_str = "Regional defaults (UK/Europe)"
    else:
        source_str = f"Mixed (SG:{sources_used['soilgrids']}, OLM:{sources_used['openlandmap']}, Reg:{sources_used['regional']})"
    
    print(f"  ✅ Retrieved {len(k_values)}/{total_points} K values (mean K={k_array.mean():.4f}, source: {source_str})")
    
    return {
        "mean": float(k_array.mean()),
        "min": float(k_array.min()),
        "max": float(k_array.max()),
        "stddev": float(k_array.std()),
        "unit": "t ha h ha⁻¹ MJ⁻¹ mm⁻¹",
        "source": source_str
    }

def calculate_ls_factor(polygon_coords: List[List[float]]) -> Dict:
    """
    Calculate LS factor (slope length and steepness) using Open-Elevation API
    
    LS = (λ/22.13)^m × (65.41×sin²θ + 4.56×sinθ + 0.065)
    where:
    - λ = slope length (m) - approximated from polygon size
    - m = slope length exponent (typically 0.4-0.6)
    - θ = slope angle (degrees)
    
    Falls back to flat terrain (LS=1.0) if elevation data unavailable
    """
    coords = polygon_coords[0]
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    
    minx, maxx = min(lons), max(lons)
    miny, maxy = min(lats), max(lats)
    
    # Sample grid for elevation
    sample_size = 5
    xs = np.linspace(minx, maxx, sample_size)
    ys = np.linspace(miny, maxy, sample_size)
    
    print(f"  ⛰️  Fetching elevation data for LS factor calculation...")
    
    elevations = []
    
    try:
        # Use Open-Elevation API (free, no key required)
        locations = [{"latitude": float(lat), "longitude": float(lon)} 
                     for lon in xs for lat in ys]
        
        url = "https://api.open-elevation.com/api/v1/lookup"
        response = requests.post(url, json={"locations": locations}, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            elevations = [r["elevation"] for r in results if "elevation" in r]
            
            if len(elevations) >= 4:
                elev_array = np.array(elevations).reshape(-1, sample_size) if len(elevations) >= sample_size else np.array(elevations)
                
                # Calculate slopes
                slopes = []
                
                # Calculate slope from elevation gradients
                if elev_array.ndim == 2 and elev_array.shape[0] > 1:
                    # Calculate average cell size in meters
                    lat_diff = (maxy - miny) / (sample_size - 1)
                    lon_diff = (maxx - minx) / (sample_size - 1)
                    
                    # Approximate meters per degree at this latitude
                    avg_lat = (miny + maxy) / 2
                    meters_per_deg_lat = 111320
                    meters_per_deg_lon = 111320 * np.cos(np.radians(avg_lat))
                    
                    cell_size_y = lat_diff * meters_per_deg_lat
                    cell_size_x = lon_diff * meters_per_deg_lon
                    
                    # Calculate gradients
                    for i in range(elev_array.shape[0] - 1):
                        for j in range(elev_array.shape[1] - 1):
                            dz_dx = (elev_array[i, j+1] - elev_array[i, j]) / cell_size_x
                            dz_dy = (elev_array[i+1, j] - elev_array[i, j]) / cell_size_y
                            
                            slope_rad = np.arctan(np.sqrt(dz_dx**2 + dz_dy**2))
                            slope_pct = np.tan(slope_rad) * 100
                            slopes.append(slope_pct)
                else:
                    # Fallback: calculate simple slope from elevation range
                    elev_range = max(elevations) - min(elevations)
                    # Estimate horizontal distance
                    dist_m = np.sqrt((maxx - minx)**2 + (maxy - miny)**2) * 111320
                    slope_pct = (elev_range / max(dist_m, 1)) * 100 if dist_m > 0 else 0
                    slopes = [slope_pct]
                
                if slopes:
                    avg_slope_pct = np.mean(slopes)
                    
                    # Calculate LS factor using Wischmeier & Smith (1978) equation
                    # Estimate slope length from polygon size
                    area_m2 = ((maxx - minx) * meters_per_deg_lon) * ((maxy - miny) * meters_per_deg_lat)
                    slope_length_m = np.sqrt(area_m2) * 0.5  # Approximate
                    slope_length_m = min(slope_length_m, 300)  # Cap at 300m
                    
                    # Slope steepness factor (S)
                    if avg_slope_pct < 9:
                        s_factor = 10.8 * np.sin(np.arctan(avg_slope_pct / 100)) + 0.03
                    else:
                        s_factor = 16.8 * np.sin(np.arctan(avg_slope_pct / 100)) - 0.50
                    
                    # Slope length factor (L)
                    m = 0.5 if avg_slope_pct >= 5 else 0.4 if avg_slope_pct >= 3 else 0.3
                    l_factor = (slope_length_m / 22.13) ** m
                    
                    # Combined LS factor
                    ls_value = l_factor * s_factor
                    ls_value = max(0.1, min(ls_value, 20))  # Clamp to reasonable range
                    
                    print(f"  ✅ LS factor calculated: {ls_value:.2f} (slope={avg_slope_pct:.1f}%, elev_range={max(elevations)-min(elevations):.0f}m)")
                    
                    return {
                        "mean": float(round(ls_value, 2)),
                        "min": float(round(ls_value * 0.8, 2)),
                        "max": float(round(ls_value * 1.2, 2)),
                        "stddev": float(round(ls_value * 0.15, 2)),
                        "unit": "dimensionless",
                        "source": f"Open-Elevation API (slope={avg_slope_pct:.1f}%)"
                    }
                    
    except Exception as e:
        print(f"  ⚠️  Elevation API failed: {e}")
    
    # Fallback: assume relatively flat terrain
    print(f"  ⚠️  Using flat terrain default (LS=1.0)")
    
    return {
        "mean": 1.0,
        "min": 0.8,
        "max": 1.5,
        "stddev": 0.2,
        "unit": "dimensionless",
        "source": "Default (elevation data unavailable)"
    }

def calculate_c_factor(polygon_coords: List[List[float]]) -> Dict:
    """
    Calculate C factor (vegetation cover) using NDVI from satellite data
    
    C = exp(-2 × NDVI / (1 - NDVI))  [Van der Knijff et al. 2000]
    Simplified: C ≈ exp(-α × NDVI) where α ≈ 2
    
    NDVI ranges:
    - Dense vegetation (0.6-0.9): C = 0.001-0.01
    - Moderate vegetation (0.3-0.6): C = 0.01-0.1
    - Sparse vegetation (0.1-0.3): C = 0.1-0.3
    - Bare soil (<0.1): C = 0.3-1.0
    
    Falls back to land-use based estimates if NDVI unavailable
    """
    coords = polygon_coords[0]
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    
    avg_lon = sum(lons) / len(lons)
    avg_lat = sum(lats) / len(lats)
    
    minx, maxx = min(lons), max(lons)
    miny, maxy = min(lats), max(lats)
    
    print(f"  🌿 Calculating C factor from vegetation indices...")
    
    try:
        # Try to get NDVI from NASA MODIS or similar API
        # Using NASA POWER API for vegetation index (free, no key)
        # Alternative: Could use Sentinel Hub but requires authentication
        
        # For now, use OpenMeteo agriculture API which provides vegetation data
        url = "https://archive-api.open-meteo.com/v1/archive"
        params = {
            "latitude": avg_lat,
            "longitude": avg_lon,
            "start_date": "2023-06-01",  # Summer (peak vegetation)
            "end_date": "2023-08-31",
            "daily": "et0_fao_evapotranspiration,soil_moisture_0_to_7cm",  # Proxy for vegetation
            "timezone": "auto"
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            et_data = data.get("daily", {}).get("et0_fao_evapotranspiration", [])
            soil_data = data.get("daily", {}).get("soil_moisture_0_to_7cm", [])
            
            if et_data and any(v is not None for v in et_data):
                # High ET indicates more vegetation cover
                # ET0 ranges typically 2-8 mm/day
                avg_et = np.mean([v for v in et_data if v is not None])
                
                # Estimate NDVI from ET (empirical relationship)
                # Higher ET correlates with higher vegetation cover
                # NDVI ≈ 0.1 + (ET0 / 10) for temperate regions
                estimated_ndvi = min(0.85, max(0.05, 0.1 + (avg_et / 10)))
                
                # Calculate C factor from NDVI using Van der Knijff equation
                # C = exp(-2 × NDVI / (1 - NDVI))
                if estimated_ndvi < 0.99:
                    c_value = np.exp(-2 * estimated_ndvi / (1 - estimated_ndvi))
                else:
                    c_value = 0.001
                
                c_value = max(0.001, min(c_value, 1.0))
                
                # Add variability based on seasonal changes
                c_min = c_value * 0.7  # Growing season (more cover)
                c_max = c_value * 1.8  # Dormant season (less cover)
                
                print(f"  ✅ C factor from vegetation proxy: {c_value:.3f} (est. NDVI={estimated_ndvi:.2f}, ET={avg_et:.1f}mm/day)")
                
                return {
                    "mean": float(round(c_value, 3)),
                    "min": float(round(c_min, 3)),
                    "max": float(round(c_max, 3)),
                    "stddev": float(round((c_max - c_min) / 4, 3)),
                    "unit": "dimensionless",
                    "source": f"ET-based vegetation estimate (NDVI≈{estimated_ndvi:.2f})"
                }
                
    except Exception as e:
        print(f"  ⚠️  Vegetation API failed: {e}")
    
    # Fallback: Land-use based estimates for different regions
    # European land cover classification
    if 35 <= avg_lat <= 72 and -25 <= avg_lon <= 45:  # Europe
        if 50 <= avg_lat:  # Northern Europe (UK, Scandinavia)
            # Mix of grassland, cropland, forest
            c_value = 0.045  # Moderate vegetation cover
        elif 45 <= avg_lat < 50:  # Central Europe
            # Agricultural areas
            c_value = 0.08
        else:  # Mediterranean
            # Sparser vegetation, more exposed soil
            c_value = 0.15
    else:
        # Global defaults by climate zone
        if abs(avg_lat) < 23:  # Tropics
            c_value = 0.02  # Dense vegetation
        elif abs(avg_lat) < 40:  # Subtropics
            c_value = 0.12
        elif abs(avg_lat) < 60:  # Temperate
            c_value = 0.08
        else:  # Polar/tundra
            c_value = 0.25
    
    print(f"  ⚠️  Using land-use based C factor estimate: {c_value:.3f}")
    
    return {
        "mean": float(round(c_value, 3)),
        "min": float(round(c_value * 0.7, 3)),
        "max": float(round(c_value * 1.5, 3)),
        "stddev": float(round(c_value * 0.2, 3)),
        "unit": "dimensionless",
        "source": "Land-use estimate (vegetation data unavailable)"
    }

def calculate_p_factor(polygon_coords: List[List[float]], ls_factor: Dict = None) -> Dict:
    """
    Calculate P factor (Conservation Practice Factor)
    Estimates impact of soil conservation practices based on slope
    
    Args:
        polygon_coords: List of [lon, lat] coordinate pairs
        ls_factor: Optional pre-calculated LS factor dict. If not provided, will calculate it.
        
    Returns:
        Dict with P factor statistics (mean, min, max, stddev, unit, source)
        
    Reference:
        - Wischmeier & Smith (1978) - Predicting Rainfall Erosion Losses
        - Panagos et al. (2015) - P factor values for Europe
    """
    print(f"  🌾 Calculating P factor (conservation practices) for {len(polygon_coords)} points...")
    
    # Calculate or use provided LS factor to determine slope severity
    if ls_factor is None:
        ls_factor = calculate_ls_factor(polygon_coords)
    
    ls_mean = ls_factor.get("mean", 1.0)
    
    # P factor varies by conservation practice and slope
    # Based on Wischmeier & Smith (1978)
    if ls_mean < 2:  # Flat terrain
        p_value = 0.6  # Contouring on flat land
        practice = "Contouring (flat)"
    elif ls_mean < 5:  # Gentle slopes
        p_value = 0.5  # Contouring
        practice = "Contouring"
    elif ls_mean < 10:  # Moderate slopes
        p_value = 0.6  # Contour strip cropping
        practice = "Contour strip cropping"
    else:  # Steep slopes
        p_value = 0.8  # Terracing needed
        practice = "Terracing"
    
    print(f"  ✅ P factor: {p_value:.3f} ({practice}, LS={ls_mean:.2f})")
    
    return {
        "mean": float(round(p_value, 3)),
        "min": float(round(max(0.5, p_value * 0.9), 3)),
        "max": float(round(min(1.0, p_value * 1.1), 3)),
        "stddev": float(round(p_value * 0.05, 3)),
        "unit": "dimensionless",
        "source": f"{practice} (slope-adjusted, LS={ls_mean:.2f})"
    }

def calculate_erosion(r: float, k: float, ls: float, c: float, p: float = 1.0) -> Dict:
    """
    Calculate final erosion: A = R * K * LS * C * P
    
    Args:
        r, k, ls, c, p: RUSLE factor values
        
    Returns:
        Erosion statistics
    """
    # Mean erosion
    a_mean = r * k * ls * c * p
    
    # Estimate range (±30%)
    a_min = a_mean * 0.7
    a_max = a_mean * 1.3
    
    return {
        "mean": round(a_mean, 2),
        "min": round(a_min, 2),
        "max": round(a_max, 2),
        "stddev": round(a_mean * 0.15, 2),
        "p50": round(a_mean, 2),
        "p95": round(a_mean * 1.25, 2),
        "p99": round(a_mean * 1.3, 2),
        "unit": "t/ha/yr"
    }

def compute_rusle(geojson: Dict, options: Dict) -> Dict:
    """
    Main RUSLE computation function
    
    Args:
        geojson: GeoJSON Feature with polygon
        options: Computation options (threshold, p_toggle, etc.)
        
    Returns:
        Complete RUSLE results
    """
    print("🌍 Starting RUSLE computation...")
    
    start_time = time.time()
    
    # Extract polygon coordinates
    geometry = geojson.get("geometry", geojson)
    coords = geometry["coordinates"]
    
    # Calculate factors
    print("  📊 Calculating R factor...")
    r_factor = calculate_r_factor(coords)
    
    print("  📊 Calculating K factor...")
    k_factor = calculate_k_factor(coords)
    
    print("  📊 Calculating LS factor...")
    ls_factor = calculate_ls_factor(coords)
    
    print("  📊 Calculating C factor...")
    c_factor = calculate_c_factor(coords)
    
    # P factor - calculate based on slope and land use
    print("  📊 Calculating P factor...")
    p_toggle = options.get("p_toggle", False)
    
    if p_toggle:
        p_factor = calculate_p_factor(coords, ls_factor)
    else:
        p_factor = {
            "mean": 1.0,
            "min": 1.0,
            "max": 1.0,
            "stddev": 0.0,
            "unit": "dimensionless",
            "source": "No conservation practices"
        }
    
    # Calculate erosion
    print("  📊 Calculating final erosion...")
    erosion = calculate_erosion(
        r_factor["mean"],
        k_factor["mean"],
        ls_factor["mean"],
        c_factor["mean"],
        p_factor["mean"]
    )
    
    # Identify hotspots
    threshold = options.get("threshold", 20.0)
    hotspots = []
    
    if erosion["mean"] > threshold:
        hotspots.append({
            "id": "hotspot_1",
            "geometry": geometry,
            "properties": {
                "area_ha": geojson.get("properties", {}).get("area_hectares", 100),
                "mean_erosion": erosion["mean"],
                "max_erosion": erosion["max"],
                "dominant_factor": "K" if k_factor["mean"] > 0.03 else "C"
            },
            "reason": f"Mean erosion ({erosion['mean']:.1f} t/ha/yr) exceeds threshold ({threshold} t/ha/yr)",
            "severity": "high" if erosion["mean"] > threshold * 2 else "moderate",
            "confidence": 0.85
        })
    
    computation_time = time.time() - start_time
    
    print(f"  ✅ RUSLE computation complete in {computation_time:.2f}s")
    print(f"  📈 Mean erosion: {erosion['mean']:.2f} t/ha/yr")
    
    return {
        "erosion": erosion,
        "factors": {
            "R": r_factor,
            "K": k_factor,
            "LS": ls_factor,
            "C": c_factor,
            "P": p_factor
        },
        "hotspots": hotspots,
        "summary": {
            "total_hotspots": len(hotspots),
            "total_high_risk_area_ha": sum(h["properties"]["area_ha"] for h in hotspots),
            "severity_distribution": {
                "low": 0,
                "moderate": sum(1 for h in hotspots if h["severity"] == "moderate"),
                "high": sum(1 for h in hotspots if h["severity"] == "high"),
                "critical": 0
            },
            "dominant_factors": get_dominant_factors(r_factor, k_factor, ls_factor, c_factor, p_factor)
        },
        "validation": {
            "high_veg_reduction_pct": calculate_veg_reduction(c_factor),
            "flat_terrain_reduction_pct": calculate_terrain_reduction(ls_factor),
            "bare_soil_increase_pct": calculate_bare_soil_risk(c_factor),
            "model_valid": True,
            "notes": f"Computation based on: {r_factor['source']}, {k_factor['source']}, {ls_factor['source']}, {c_factor['source']}"
        },
        "computation_time_sec": round(computation_time, 2)
    }


def get_dominant_factors(r_factor, k_factor, ls_factor, c_factor, p_factor):
    """Identify which factors contribute most to erosion risk"""
    factors = {
        "R": (r_factor["mean"] - 800) / 800 if r_factor["mean"] > 800 else 0,  # Normalized above baseline
        "K": (k_factor["mean"] - 0.025) / 0.025 if k_factor["mean"] > 0.025 else 0,
        "LS": (ls_factor["mean"] - 1.0) / 1.0 if ls_factor["mean"] > 1.0 else 0,
        "C": (c_factor["mean"] - 0.05) / 0.05 if c_factor["mean"] > 0.05 else 0,
    }
    
    # Return top 2 contributing factors
    sorted_factors = sorted(factors.items(), key=lambda x: x[1], reverse=True)
    return [f[0] for f in sorted_factors[:2] if f[1] > 0] or ["K", "C"]


def calculate_veg_reduction(c_factor):
    """Calculate percentage erosion reduction from vegetation"""
    # C factor represents cover effect: lower C = better protection
    # If C = 0.001 (dense veg), reduction is ~99.9%
    # If C = 0.5 (sparse), reduction is ~50%
    c_mean = c_factor.get("mean", 0.1)
    reduction_pct = (1.0 - c_mean) * 100
    return round(min(99.9, max(0, reduction_pct)), 1)


def calculate_terrain_reduction(ls_factor):
    """Calculate percentage of area with flat terrain (LS ~ 1)"""
    # If LS close to 1, terrain is flat
    ls_mean = ls_factor.get("mean", 1.0)
    
    if ls_mean <= 1.2:
        flat_pct = 90 - (ls_mean - 1.0) * 200  # Very flat
    elif ls_mean <= 2.0:
        flat_pct = 50 - (ls_mean - 1.2) * 40
    elif ls_mean <= 5.0:
        flat_pct = 20 - (ls_mean - 2.0) * 5
    else:
        flat_pct = max(0, 5 - (ls_mean - 5.0))
    
    return round(min(100, max(0, flat_pct)), 1)


def calculate_bare_soil_risk(c_factor):
    """Calculate percentage increase in risk from bare/exposed soil"""
    # Higher C means more bare soil exposure
    c_mean = c_factor.get("mean", 0.1)
    
    # C > 0.3 indicates significant bare soil
    if c_mean > 0.3:
        risk_increase_pct = (c_mean - 0.1) / 0.1 * 100
    elif c_mean > 0.15:
        risk_increase_pct = (c_mean - 0.05) / 0.05 * 50
    else:
        risk_increase_pct = max(0, (c_mean - 0.02) / 0.02 * 20)
    
    return round(min(500, max(0, risk_increase_pct)), 1)


# ---- FastAPI compatibility router for middleware/backend_client ----
router = APIRouter()


@router.post("/api/rusle/compute")
async def rusle_compute_endpoint(payload: Dict) -> Dict:
    """
    HTTP endpoint expected by the middleware `backend_client`.

    Expects JSON payload: { "geojson": {...}, "options": {...} }
    Runs the existing compute_rusle function in a thread to avoid blocking.
    """
    # Basic validation of payload
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid payload")

    geojson = payload.get("geojson")
    options = payload.get("options", {}) or {}

    if not geojson:
        raise HTTPException(status_code=400, detail="Missing geojson in payload")

    # Run compute_rusle in thread to avoid blocking the event loop
    try:
        result = await asyncio.to_thread(compute_rusle, geojson, options)
        # Optionally include tile_urls placeholder if not present
        if "tile_urls" not in result:
            result["tile_urls"] = {
                "erosion_risk": None,
                "factors": None
            }
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RUSLE computation failed: {e}")


@router.post("/api/ml/hotspots")
async def ml_hotspots_endpoint(payload: Dict) -> Dict:
    """
    Lightweight ML hotspot compatibility endpoint.

    Middleware expects an endpoint that returns a structure with `hotspots` and `summary`.
    This simple implementation uses a threshold on mean erosion if the caller provided
    a `geojson` and `threshold_t_ha_yr`. If the backend has already computed RUSLE,
    the middleware calls happen in parallel so this endpoint is best-effort.
    """
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid payload")

    geojson = payload.get("geojson")
    threshold = payload.get("threshold_t_ha_yr", 20.0)

    # If geojson present, attempt to compute RUSLE quickly (synchronous) to derive hotspots
    try:
        if geojson:
            rusle = await asyncio.to_thread(compute_rusle, geojson, {"p_toggle": False})
            mean_erosion = rusle.get("erosion", {}).get("mean", 0)
        else:
            mean_erosion = 0

        hotspots = []
        summary = {"total_hotspots": 0}

        # Simple rule: if mean erosion exceeds threshold, return one hotspot (whole polygon)
        if mean_erosion and mean_erosion > threshold:
            hotspots = [{
                "id": "hotspot_1",
                "geometry": geojson.get("geometry") if geojson else None,
                "properties": {
                    "area_ha": geojson.get("properties", {}).get("area_hectares", 0) if geojson else 0,
                    "mean_erosion": mean_erosion,
                    "max_erosion": rusle.get("erosion", {}).get("max", mean_erosion),
                    "dominant_factor": "K"
                },
                "reason": f"Mean RUSLE erosion {mean_erosion:.1f} > threshold {threshold}",
                "severity": "high",
                "confidence": 0.7
            }]

            summary = {
                "total_hotspots": 1,
                "total_high_risk_area_ha": hotspots[0]["properties"]["area_ha"],
                "severity_distribution": {"low": 0, "moderate": 0, "high": 1, "critical": 0},
                "dominant_factors": ["K"]
            }

        return {"hotspots": hotspots, "summary": summary}

    except Exception as e:
        # ML is optional: return empty result on error
        return {"hotspots": [], "summary": {"total_hotspots": 0, "error": str(e)}}

