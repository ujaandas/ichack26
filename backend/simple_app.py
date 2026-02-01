"""
Lightweight backend app that exposes only the compute router.
This avoids importing the full `app.main` which depends on newer Python and DB packages.
"""
from fastapi import FastAPI

import app.compute_rusle as compute_mod

app = FastAPI(title="Backend - compute only")
app.include_router(compute_mod.router)

@app.get("/health")
def health_simple():
    return {"status": "ok", "rusle_service": "healthy", "ml_service": "healthy"}
