"""
API Module - FastAPI Backend

This module provides the REST API for the MEP Digital Twin system.
It handles data ingestion, validation, storage, and health queries.

Key Components:
- main.py: FastAPI application and root endpoints
- models.py: Pydantic schemas for request/response validation
- database.py: TimescaleDB connection management
- routes/: API endpoint implementations

Endpoints:
- POST /api/v1/ingest: Ingest sensor data with physics validation
- GET /api/v1/health/{asset_id}: Get current health score
- GET /api/v1/latest/{asset_id}: Get latest sensor readings
- GET /api/v1/history/{asset_id}: Get historical data
- POST /api/v1/scenarios/generate: Generate synthetic data
"""

__version__ = "0.1.0"
