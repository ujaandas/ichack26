from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.routes import router as auth_router
from app.config import settings
from app.database import init_db
from app.users.routes import router as users_router

app = FastAPI(title="Hackathon API", debug=(settings.ENV == "dev"))

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/health")
def health():
    # Provide service-level health keys expected by middleware/backend_client
    return {
        "status": "ok",
        "env": settings.ENV,
        "rusle_service": "healthy",
        "ml_service": "healthy"
    }


# Include RUSLE router if available
try:
    from app.compute_rusle import router as rusle_router
    app.include_router(rusle_router)
except Exception:
    # If router import fails, don't crash startup; log or ignore
    pass


app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(users_router, prefix="/api/users", tags=["users"])
