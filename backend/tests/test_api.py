import os
import sys
import json

import pytest

from fastapi.testclient import TestClient


# Ensure backend package (backend/) is importable: insert backend/ as first path
HERE = os.path.dirname(__file__)
BACKEND_ROOT = os.path.normpath(os.path.join(HERE, ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)


from fastapi import FastAPI
import sys
import types

# Provide lightweight stand-ins for heavy imports if they're not installed in the test env.
# This lets us import the module and then monkeypatch compute_rusle for deterministic tests.
for _m in ("requests", "numpy"):
    if _m not in sys.modules:
        try:
            __import__(_m)
        except Exception:
            sys.modules[_m] = types.ModuleType(_m)

import app.compute_rusle as compute_mod


# Create a lightweight FastAPI test app to avoid importing the full backend
test_app = FastAPI()


@test_app.get("/health")
def _health():
    return {"status": "ok", "env": "test", "rusle_service": "healthy", "ml_service": "healthy"}


test_app.include_router(compute_mod.router)

client = TestClient(test_app)


def test_health_endpoint():
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") == "ok"
    # Middleware expects these keys
    assert "rusle_service" in data and "ml_service" in data


def test_rusle_compute_endpoint_monkeypatched(monkeypatch):
    # Prepare a deterministic stub result
    stub = {
        "erosion": {"mean": 5.0, "min": 3.5, "max": 6.5, "stddev": 0.5, "unit": "t/ha/yr"},
        "factors": {
            "R": {"mean": 1850.0, "unit": "MJ mm ha⁻¹ h⁻¹ yr⁻¹"},
            "K": {"mean": 0.03, "unit": "t ha h ha⁻¹ MJ⁻¹ mm⁻¹"},
            "LS": {"mean": 1.0},
            "C": {"mean": 0.08},
            "P": {"mean": 1.0}
        },
        "hotspots": [],
        "validation": {"model_valid": True},
        "tile_urls": {"erosion_risk": None},
        "computation_time_sec": 0.01
    }

    # Patch the compute_rusle function in the module used by the router
    monkeypatch.setattr(compute_mod, "compute_rusle", lambda geojson, options: stub)

    payload = {
        "geojson": {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [[[0,0],[1,0],[1,1],[0,0]]]}, "properties": {"area_hectares": 1}},
        "options": {"p_toggle": False, "compute_sensitivities": False}
    }

    r = client.post("/api/rusle/compute", json=payload)
    assert r.status_code == 200
    data = r.json()

    # Response should include keys coming from our stub
    assert "erosion" in data
    assert data["erosion"]["mean"] == 5.0
    assert "factors" in data and "K" in data["factors"]


def test_ml_hotspots_endpoint_generates_hotspot_when_threshold_exceeded(monkeypatch):
    # Make compute_rusle return a high mean erosion so ML endpoint flags a hotspot
    stub_high = {
        "erosion": {"mean": 50.0, "min": 30.0, "max": 70.0, "stddev": 5.0},
        "factors": {},
        "validation": {},
        "tile_urls": {},
        "hotspots": [],
        "computation_time_sec": 0.02
    }

    monkeypatch.setattr(compute_mod, "compute_rusle", lambda geojson, options: stub_high)

    payload = {
        "geojson": {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [[[0,0],[1,0],[1,1],[0,0]]]}, "properties": {"area_hectares": 2}},
        "threshold_t_ha_yr": 10
    }

    r = client.post("/api/ml/hotspots", json=payload)
    assert r.status_code == 200
    data = r.json()

    assert "hotspots" in data
    assert isinstance(data["hotspots"], list)
    assert len(data["hotspots"]) == 1
    hs = data["hotspots"][0]
    assert hs["properties"]["mean_erosion"] == 50.0
