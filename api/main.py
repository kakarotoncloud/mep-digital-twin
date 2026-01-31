"""
MEP Digital Twin - FastAPI Application

This is the main entry point for the FastAPI backend.
It combines all route modules and provides system-wide endpoints.

Features:
- Physics-validated data ingestion
- Real-time health scoring
- Historical data queries
- Synthetic scenario generation
- Interactive API documentation (Swagger/OpenAPI)

Access Points:
- API Root: http://localhost:8000
- Swagger Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json
"""

import os
import logging
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.database import check_database_health, init_database
from api.routes import ingest_router, health_router, query_router, scenarios_router
from api.models import SystemHealth, ErrorResponse

# =========================================
# Logging Configuration
# =========================================

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# =========================================
# Application Lifespan
# =========================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    
    Runs on startup and shutdown to manage resources.
    """
    # Startup
    logger.info("🚀 Starting MEP Digital Twin API...")
    
    try:
        # Check database connection
        db_health = check_database_health()
        if db_health["status"] == "healthy":
            logger.info("✅ Database connection verified")
            logger.info(f"   TimescaleDB version: {db_health.get('timescaledb_version', 'N/A')}")
        else:
            logger.warning(f"⚠️ Database health check failed: {db_health}")
        
        # Initialize database if needed
        init_database()
        
    except Exception as e:
        logger.error(f"❌ Startup error: {e}")
        # Don't prevent startup - database might come up later
    
    logger.info("✅ MEP Digital Twin API started successfully")
    logger.info("📚 API Documentation: http://localhost:8000/docs")
    
    yield  # Application runs here
    
    # Shutdown
    logger.info("👋 Shutting down MEP Digital Twin API...")


# =========================================
# FastAPI Application
# =========================================

app = FastAPI(
    title="MEP Digital Twin API",
    description="""
## Physics-Aware MEP Digital Twin & Predictive Maintenance

This API provides predictive maintenance capabilities for MEP (Mechanical, Electrical, Plumbing) 
systems, with a focus on water-cooled chiller plants.

### Key Features

- **Physics-Guard Validation**: Sensor data is validated against physical laws before storage
- **Real-time Health Scoring**: Continuous health assessment with explainable breakdowns
- **Synthetic Data Generation**: Generate realistic failure scenarios for testing and demos
- **Time-Series Storage**: Efficient storage and querying with TimescaleDB

### Core Concepts

#### Physics Validation
Data that violates physical laws (e.g., return water colder than supply) is rejected 
automatically, catching sensor errors before they corrupt your analytics.

#### Health Score (0-100)
A composite score based on:
- **Vibration** (35%): Leading indicator for mechanical issues
- **Approach Temperature** (25%): Heat transfer efficiency  
- **Phase Imbalance** (20%): Electrical health
- **kW/Ton** (15%): Energy efficiency
- **Delta-T** (5%): System balance

### Quick Start

1. **Check API health**: `GET /health`
2. **Generate demo data**: `POST /api/v1/scenarios/demo/setup`
3. **View health score**: `GET /api/v1/health/CH-001`
4. **Get latest readings**: `GET /api/v1/query/latest/CH-001`
    """,
    version="0.1.0",
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT"
    },
    contact={
        "name": "MEP Digital Twin Team",
        "url": "https://github.com/yourusername/mep-digital-twin"
    },
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)


# =========================================
# CORS Middleware
# =========================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",  # Streamlit
        "http://localhost:3000",  # React dev
        "http://127.0.0.1:8501",
        "http://127.0.0.1:3000",
        "*"  # Allow all for development - restrict in production
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================
# Exception Handlers
# =========================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions with consistent format."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle unexpected exceptions."""
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": True,
            "message": "An unexpected error occurred",
            "detail": str(exc) if os.getenv("DEBUG", "false").lower() == "true" else None,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


# =========================================
# Include Routers
# =========================================

# API v1 routes
app.include_router(ingest_router, prefix="/api/v1")
app.include_router(health_router, prefix="/api/v1")
app.include_router(query_router, prefix="/api/v1")
app.include_router(scenarios_router, prefix="/api/v1")


# =========================================
# Root Endpoints
# =========================================

@app.get(
    "/",
    tags=["System"],
    summary="API Root",
    description="Welcome endpoint with API information"
)
async def root():
    """API root endpoint."""
    return {
        "name": "MEP Digital Twin API",
        "version": "0.1.0",
        "description": "Physics-Aware Predictive Maintenance for MEP Systems",
        "documentation": "/docs",
        "health_check": "/health",
        "api_base": "/api/v1"
    }


@app.get(
    "/health",
    response_model=SystemHealth,
    tags=["System"],
    summary="System Health Check",
    description="Check the health status of the API and its dependencies"
)
async def health_check():
    """System health check endpoint."""
    db_health = check_database_health()
    
    overall_status = "ok" if db_health["status"] == "healthy" else "degraded"
    
    return SystemHealth(
        status=overall_status,
        version="0.1.0",
        timestamp=datetime.utcnow(),
        database=db_health["status"],
        components={
            "api": "ok",
            "database": db_health["status"],
            "timescaledb": "ok" if db_health.get("timescaledb_version") else "not_detected",
            "physics_engine": "ok",
            "health_engine": "ok"
        }
    )


@app.get(
    "/info",
    tags=["System"],
    summary="System Information",
    description="Get detailed system information"
)
async def system_info():
    """Get system information."""
    db_health = check_database_health()
    
    return {
        "api": {
            "name": "MEP Digital Twin API",
            "version": "0.1.0",
            "environment": os.getenv("ENVIRONMENT", "development")
        },
        "database": {
            "status": db_health["status"],
            "type": "TimescaleDB (PostgreSQL)",
            "timescaledb_version": db_health.get("timescaledb_version"),
            "sensor_table_ready": db_health.get("sensor_table_exists", False)
        },
        "features": {
            "physics_validation": True,
            "health_scoring": True,
            "scenario_generation": True,
            "time_series_storage": True
        },
        "endpoints": {
            "ingest": "/api/v1/ingest",
            "health": "/api/v1/health/{asset_id}",
            "query": "/api/v1/query/latest/{asset_id}",
            "scenarios": "/api/v1/scenarios"
        },
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc",
            "openapi": "/openapi.json"
        }
    }


@app.get(
    "/ready",
    tags=["System"],
    summary="Readiness Check",
    description="Check if the API is ready to receive traffic"
)
async def readiness_check():
    """Kubernetes-style readiness probe."""
    db_health = check_database_health()
    
    if db_health["status"] != "healthy":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not ready"
        )
    
    return {"ready": True}


@app.get(
    "/live",
    tags=["System"],
    summary="Liveness Check",
    description="Check if the API process is alive"
)
async def liveness_check():
    """Kubernetes-style liveness probe."""
    return {"alive": True}


# =========================================
# Development/Debug Endpoints
# =========================================

if os.getenv("DEBUG", "false").lower() == "true":
    
    @app.get("/debug/config", tags=["Debug"])
    async def debug_config():
        """Show configuration (debug only)."""
        return {
            "database_url": os.getenv("DATABASE_URL", "not set")[:50] + "...",
            "log_level": os.getenv("LOG_LEVEL", "INFO"),
            "physics_strict_mode": os.getenv("PHYSICS_STRICT_MODE", "false"),
            "debug": os.getenv("DEBUG", "false")
        }


# =========================================
# Run with Uvicorn (for development)
# =========================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "api.main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", 8000)),
        reload=os.getenv("API_RELOAD", "true").lower() == "true",
        log_level=os.getenv("LOG_LEVEL", "info").lower()
)
