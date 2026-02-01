# Docker Setup Guide

This project uses Docker Compose to orchestrate three services for soil erosion analysis.

## Project Architecture

- **Frontend** (Port 5173): React + Vite application with Cesium 3D mapping
- **Middleware** (Port 8000): FastAPI orchestration layer handling requests and coordinating services
- **Backend** (Port 8001): RUSLE computation engine with ML models for erosion prediction

### Service Flow
```
Frontend → Middleware → Backend (RUSLE + ML)
                    ↓
                Sentinel Hub API (Satellite data)
                Crop Prediction Models
                Carbon Sequestration Models
```

## Prerequisites

- Docker Desktop installed
- Docker Compose installed

## Getting Started

### 1. Create Environment File

Create a `.env` file in the `middleware/` directory:

```bash
# Example .env file
SENTINEL_API_KEY=your_sentinel_api_key_here
# Add other environment variables as needed
```

### 2. Build and Start Services

From the `infra/` directory:

```bash
# Build and start all services
docker-compose up --build

# Or run in detached mode
docker-compose up -d --build
```

### 3. Access the Applications

- **Frontend**: http://localhost:5173
- **Middleware API**: http://localhost:8000
- **Middleware Docs**: http://localhost:8000/docs
- **Backend API**: http://localhost:8001
- **Backend Docs**: http://localhost:8001/docs

## Services Overview

### Backend (Port 8001)
The RUSLE computation engine handles:
- **R Factor**: Rainfall erosivity calculation
- **K Factor**: Soil erodibility from SoilGrids API
- **LS Factor**: Topographic slope/length analysis
- **C Factor**: Land cover and vegetation
- **P Factor**: Conservation practices (optional)
- **ML Models**: Hotspot detection and classification

Key endpoints:
- `POST /api/rusle/compute` - RUSLE factor computation
- `POST /api/ml/hotspots` - ML-based erosion hotspot detection

### Middleware (Port 8000)
Orchestration layer that:
- Validates and parses polygon coordinates
- Coordinates parallel API calls to backend and external services
- Fetches satellite imagery from Sentinel Hub
- Runs crop yield predictions using ML models
- Estimates carbon sequestration potential
- Aggregates all results into unified response

Key endpoint:
- `POST /api/rusle` - Main endpoint for erosion analysis

### Frontend (Port 5173)
Interactive web application featuring:
- Cesium 3D globe for polygon drawing
- Real-time erosion visualization
- Satellite imagery overlay
- Crop yield and carbon sequestration estimates
- Factor analysis and hotspot mapping

## Docker Commands

### View Running Containers
```bash
docker-compose ps
```

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f middleware
docker-compose logs -f frontend
```

### Stop Services
```bash
docker-compose down
```

### Rebuild a Specific Service
```bash
docker-compose up -d --build backend
docker-compose up -d --build middleware
docker-compose up -d --build frontend
```

### Enter a Container Shell
```bash
docker exec -it hackathon_backend bash
docker exec -it hackathon_middleware bash
docker exec -it hackathon_frontend sh
```

## Development Workflow

The docker-compose setup includes volume mounts for hot-reloading:

- **Backend**: Changes to Python files trigger uvicorn auto-reload (port 8001)
- **Middleware**: Changes to Python files trigger uvicorn auto-reload (port 8000)
- **Frontend**: Changes to `src/`, `public/`, and `index.html` trigger Vite hot reload (port 5173)

### Testing the APIs

You can test the backend directly:
```bash
curl http://localhost:8001/health
curl http://localhost:8001
```

Or test the full flow through middleware:
```bash
curl http://localhost:8000/health
curl http://localhost:8000
```

## Troubleshooting

### Containers Crash on Startup

**NumPy Compatibility Issue (FIXED)**
If you see `AttributeError: _ARRAY_API not found` or `numpy.core.multiarray failed to import`:
- This was caused by NumPy 2.x incompatibility with Shapely
- Fixed by pinning `numpy<2.0.0` in both middleware and backend requirements.txt
- Rebuild: `docker-compose up --build`

### Backend Service Issues

**Backend not starting:**
- Check logs: `docker-compose logs backend`
- Verify compute_rusle.py module is present in backend directory
- Ensure all Python dependencies are installed

**Backend healthcheck failing:**
- The middleware waits for backend to be healthy before starting
- Check backend logs for errors
- Verify port 8001 is not in use: `lsof -i :8001`

### Port Already in Use
If ports 5173 or 8000 are already in use, modify the port mappings in `docker-compose.yml`:

```yaml
ports:
  - "3000:5173"  # Map host port 3000 to container port 5173
```

### Frontend Not Loading
- Check if the middleware is running: `docker-compose logs middleware`
- Verify the API URL in frontend environment variables

### Module Not Found Errors
- Rebuild the containers: `docker-compose up --build`
- Clear Docker cache: `docker-compose build --no-cache`

### Permission Issues
On Linux, you may need to fix file permissions:
```bash
sudo chown -R $USER:$USER .
```

## Clean Up

To remove all containers, volumes, and images:

```bash
docker-compose down -v
docker system prune -a
```
