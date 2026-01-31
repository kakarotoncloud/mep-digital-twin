"""
API Routes Module

This module contains all API endpoint implementations organized by function:
- ingest.py: Data ingestion endpoints
- health.py: Health score endpoints
- query.py: Data query endpoints
- scenarios.py: Scenario generation endpoints

All routers are combined in main.py to create the complete API.
"""

from .ingest import router as ingest_router
from .health import router as health_router
from .query import router as query_router
from .scenarios import router as scenarios_router

__all__ = [
    "ingest_router",
    "health_router", 
    "query_router",
    "scenarios_router",
]
