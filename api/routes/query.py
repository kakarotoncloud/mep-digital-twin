"""
Data Query Endpoints

This module provides endpoints for querying sensor data and assets.
It supports various query patterns needed by the dashboard and
external integrations.

Key Features:
- Latest readings per asset
- Historical data with time range filtering
- Asset management
- Data aggregations
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from api.database import get_db, DatabaseManager
from api.models import (
    SensorReading,
    LatestReadingResponse,
    HistoryResponse,
    Asset,
    AssetListResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/query", tags=["Data Query"])


# =========================================
# Latest Data Endpoints
# =========================================

@router.get(
    "/latest/{asset_id}",
    response_model=LatestReadingResponse,
    summary="Get latest sensor reading",
    description="""
    Get the most recent sensor reading for a specific asset.
    
    Returns all sensor values, derived metrics, and health score
    from the latest data point.
    """
)
async def get_latest_reading(
    asset_id: str,
    db: Session = Depends(get_db)
):
    """Get latest reading for an asset."""
    with DatabaseManager(db) as db_manager:
        reading = db_manager.get_latest_reading(asset_id)
        
        if not reading:
            return LatestReadingResponse(
                asset_id=asset_id,
                reading=None,
                message=f"No data found for asset: {asset_id}"
            )
        
        # Convert to SensorReading model
        sensor_reading = SensorReading(
            time=reading["time"],
            asset_id=reading["asset_id"],
            chw_supply_temp=reading.get("chw_supply_temp"),
            chw_return_temp=reading.get("chw_return_temp"),
            cdw_inlet_temp=reading.get("cdw_inlet_temp"),
            cdw_outlet_temp=reading.get("cdw_outlet_temp"),
            ambient_temp=reading.get("ambient_temp"),
            vibration_rms=reading.get("vibration_rms"),
            vibration_freq=reading.get("vibration_freq"),
            runtime_hours=reading.get("runtime_hours"),
            start_stop_cycles=reading.get("start_stop_cycles"),
            current_r=reading.get("current_r"),
            current_y=reading.get("current_y"),
            current_b=reading.get("current_b"),
            power_kw=reading.get("power_kw"),
            load_percent=reading.get("load_percent"),
            operating_mode=reading.get("operating_mode"),
            alarm_status=reading.get("alarm_status"),
            chw_flow_gpm=reading.get("chw_flow_gpm"),
            delta_t=reading.get("delta_t"),
            kw_per_ton=reading.get("kw_per_ton"),
            approach_temp=reading.get("approach_temp"),
            phase_imbalance=reading.get("phase_imbalance"),
            cooling_tons=reading.get("cooling_tons"),
            cop=reading.get("cop"),
            health_score=reading.get("health_score"),
            health_breakdown=reading.get("health_breakdown"),
            validation_status=reading.get("validation_status"),
            validation_warnings=reading.get("validation_warnings"),
        )
        
        return LatestReadingResponse(
            asset_id=asset_id,
            reading=sensor_reading,
            message="Latest reading retrieved successfully"
        )


@router.get(
    "/latest",
    summary="Get latest readings for all assets",
    description="Get the most recent reading for each asset in the system."
)
async def get_all_latest_readings(
    db: Session = Depends(get_db)
):
    """Get latest readings for all assets."""
    with DatabaseManager(db) as db_manager:
        assets = db_manager.get_all_assets()
        
        results = []
        for asset in assets:
            reading = db_manager.get_latest_reading(asset["asset_id"])
            if reading:
                results.append({
                    "asset_id": asset["asset_id"],
                    "asset_name": asset.get("asset_name"),
                    "time": reading["time"],
                    "health_score": reading.get("health_score"),
                    "power_kw": reading.get("power_kw"),
                    "load_percent": reading.get("load_percent"),
                    "chw_supply_temp": reading.get("chw_supply_temp"),
                    "approach_temp": reading.get("approach_temp"),
                    "vibration_rms": reading.get("vibration_rms"),
                })
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "asset_count": len(results),
            "readings": results
        }


# =========================================
# Historical Data Endpoints
# =========================================

@router.get(
    "/history/{asset_id}",
    response_model=HistoryResponse,
    summary="Get historical sensor data",
    description="""
    Get historical sensor readings for an asset within a time range.
    
    **Parameters:**
    - `hours`: Number of hours of history (default: 24, max: 720 = 30 days)
    - `limit`: Maximum readings to return (default: 1000)
    
    **Use Cases:**
    - Dashboard trend charts
    - Analysis and reporting
    - Debugging sensor issues
    """
)
async def get_history(
    asset_id: str,
    hours: int = Query(default=24, ge=1, le=720, description="Hours of history"),
    limit: int = Query(default=1000, ge=1, le=10000, description="Max readings"),
    db: Session = Depends(get_db)
):
    """Get historical readings for an asset."""
    with DatabaseManager(db) as db_manager:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        readings = db_manager.get_readings_range(asset_id, start_time, end_time, limit)
        
        if not readings:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No data found for asset: {asset_id}"
            )
        
        # Convert to SensorReading models
        sensor_readings = []
        for r in readings:
            sensor_readings.append(SensorReading(
                time=r["time"],
                asset_id=r["asset_id"],
                chw_supply_temp=r.get("chw_supply_temp"),
                chw_return_temp=r.get("chw_return_temp"),
                cdw_inlet_temp=r.get("cdw_inlet_temp"),
                cdw_outlet_temp=r.get("cdw_outlet_temp"),
                ambient_temp=r.get("ambient_temp"),
                vibration_rms=r.get("vibration_rms"),
                power_kw=r.get("power_kw"),
                load_percent=r.get("load_percent"),
                delta_t=r.get("delta_t"),
                kw_per_ton=r.get("kw_per_ton"),
                approach_temp=r.get("approach_temp"),
                phase_imbalance=r.get("phase_imbalance"),
                health_score=r.get("health_score"),
            ))
        
        return HistoryResponse(
            asset_id=asset_id,
            start_time=start_time,
            end_time=end_time,
            reading_count=len(sensor_readings),
            readings=sensor_readings
        )


@router.get(
    "/history/{asset_id}/aggregated",
    summary="Get aggregated historical data",
    description="""
    Get pre-aggregated hourly data for efficient dashboard rendering.
    
    Uses TimescaleDB continuous aggregates for fast queries over
    large time ranges.
    """
)
async def get_aggregated_history(
    asset_id: str,
    days: int = Query(default=7, ge=1, le=90, description="Days of history"),
    db: Session = Depends(get_db)
):
    """Get aggregated historical data."""
    with DatabaseManager(db) as db_manager:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days)
        
        aggregates = db_manager.get_hourly_aggregates(asset_id, start_time, end_time)
        
        if not aggregates:
            # Fallback to raw data sampling
            readings = db_manager.get_readings_range(asset_id, start_time, end_time, limit=500)
            
            if not readings:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No data found for asset: {asset_id}"
                )
            
            # Sample every Nth reading for efficiency
            sample_rate = max(1, len(readings) // 200)
            sampled = readings[::sample_rate]
            
            return {
                "asset_id": asset_id,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "aggregation": "sampled",
                "data_points": len(sampled),
                "data": [
                    {
                        "time": r["time"],
                        "health_score": r.get("health_score"),
                        "approach_temp": r.get("approach_temp"),
                        "kw_per_ton": r.get("kw_per_ton"),
                        "vibration_rms": r.get("vibration_rms"),
                        "power_kw": r.get("power_kw"),
                        "load_percent": r.get("load_percent"),
                    }
                    for r in sampled
                ]
            }
        
        return {
            "asset_id": asset_id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "aggregation": "hourly",
            "data_points": len(aggregates),
            "data": [
                {
                    "time": a["bucket"],
                    "avg_health_score": a.get("avg_health_score"),
                    "min_health_score": a.get("min_health_score"),
                    "max_health_score": a.get("max_health_score"),
                    "avg_approach_temp": a.get("avg_approach_temp"),
                    "avg_kw_per_ton": a.get("avg_kw_per_ton"),
                    "avg_vibration_rms": a.get("avg_vibration_rms"),
                    "max_vibration_rms": a.get("max_vibration_rms"),
                    "avg_power_kw": a.get("avg_power_kw"),
                    "avg_load_percent": a.get("avg_load_percent"),
                    "reading_count": a.get("reading_count"),
                }
                for a in aggregates
            ]
        }


@router.get(
    "/trends/{asset_id}",
    summary="Get trend data for key metrics",
    description="""
    Get optimized trend data for dashboard charts.
    
    Returns time-series data for key metrics:
    - Health score
    - Approach temperature
    - kW/Ton efficiency
    - Vibration
    - Power consumption
    """
)
async def get_trends(
    asset_id: str,
    hours: int = Query(default=24, ge=1, le=168, description="Hours of data"),
    points: int = Query(default=100, ge=10, le=500, description="Data points to return"),
    db: Session = Depends(get_db)
):
    """Get trend data optimized for charts."""
    with DatabaseManager(db) as db_manager:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        # Get more readings than needed, then sample
        readings = db_manager.get_readings_range(
            asset_id, start_time, end_time, limit=points * 5
        )
        
        if not readings:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No data found for asset: {asset_id}"
            )
        
        # Sample to desired number of points
        sample_rate = max(1, len(readings) // points)
        sampled = readings[::sample_rate][:points]
        
        # Extract time series for each metric
        return {
            "asset_id": asset_id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "point_count": len(sampled),
            "metrics": {
                "health_score": {
                    "times": [r["time"].isoformat() for r in sampled],
                    "values": [r.get("health_score") for r in sampled]
                },
                "approach_temp": {
                    "times": [r["time"].isoformat() for r in sampled],
                    "values": [r.get("approach_temp") for r in sampled]
                },
                "kw_per_ton": {
                    "times": [r["time"].isoformat() for r in sampled],
                    "values": [r.get("kw_per_ton") for r in sampled]
                },
                "vibration_rms": {
                    "times": [r["time"].isoformat() for r in sampled],
                    "values": [r.get("vibration_rms") for r in sampled]
                },
                "power_kw": {
                    "times": [r["time"].isoformat() for r in sampled],
                    "values": [r.get("power_kw") for r in sampled]
                },
                "load_percent": {
                    "times": [r["time"].isoformat() for r in sampled],
                    "values": [r.get("load_percent") for r in sampled]
                },
                "delta_t": {
                    "times": [r["time"].isoformat() for r in sampled],
                    "values": [r.get("delta_t") for r in sampled]
                },
            }
        }


# =========================================
# Asset Management Endpoints
# =========================================

@router.get(
    "/assets",
    response_model=AssetListResponse,
    summary="List all assets",
    description="Get a list of all registered assets in the system."
)
async def list_assets(
    db: Session = Depends(get_db)
):
    """List all assets."""
    with DatabaseManager(db) as db_manager:
        assets = db_manager.get_all_assets()
        
        return AssetListResponse(
            count=len(assets),
            assets=[
                Asset(
                    asset_id=a["asset_id"],
                    asset_name=a.get("asset_name", a["asset_id"]),
                    asset_type=a.get("asset_type", "Unknown"),
                    location=a.get("location"),
                    manufacturer=a.get("manufacturer"),
                    model=a.get("model"),
                    capacity_tons=a.get("capacity_tons"),
                    install_date=a.get("install_date"),
                    last_maintenance=a.get("last_maintenance"),
                    status=a.get("status", "active"),
                )
                for a in assets
            ]
        )


@router.get(
    "/assets/{asset_id}",
    response_model=Asset,
    summary="Get asset details",
    description="Get detailed information about a specific asset."
)
async def get_asset(
    asset_id: str,
    db: Session = Depends(get_db)
):
    """Get asset details."""
    with DatabaseManager(db) as db_manager:
        asset = db_manager.get_asset(asset_id)
        
        if not asset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Asset not found: {asset_id}"
            )
        
        return Asset(
            asset_id=asset["asset_id"],
            asset_name=asset.get("asset_name", asset["asset_id"]),
            asset_type=asset.get("asset_type", "Unknown"),
            location=asset.get("location"),
            manufacturer=asset.get("manufacturer"),
            model=asset.get("model"),
            capacity_tons=asset.get("capacity_tons"),
            install_date=asset.get("install_date"),
            last_maintenance=asset.get("last_maintenance"),
            status=asset.get("status", "active"),
        )


@router.get(
    "/assets/{asset_id}/stats",
    summary="Get asset statistics",
    description="Get statistics about an asset's data."
)
async def get_asset_stats(
    asset_id: str,
    db: Session = Depends(get_db)
):
    """Get statistics for an asset."""
    with DatabaseManager(db) as db_manager:
        asset = db_manager.get_asset(asset_id)
        
        if not asset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Asset not found: {asset_id}"
            )
        
        # Get reading counts
        total_count = db_manager.get_reading_count(asset_id)
        
        # Get count for last 24 hours
        end_time = datetime.utcnow()
        start_time_24h = end_time - timedelta(hours=24)
        count_24h = db_manager.get_reading_count(asset_id, start_time_24h, end_time)
        
        # Get count for last 7 days
        start_time_7d = end_time - timedelta(days=7)
        count_7d = db_manager.get_reading_count(asset_id, start_time_7d, end_time)
        
        # Get latest reading
        latest = db_manager.get_latest_reading(asset_id)
        
        return {
            "asset_id": asset_id,
            "asset_name": asset.get("asset_name"),
            "statistics": {
                "total_readings": total_count,
                "readings_24h": count_24h,
                "readings_7d": count_7d,
                "latest_reading_time": latest["time"] if latest else None,
                "latest_health_score": latest.get("health_score") if latest else None,
            },
            "data_quality": {
                "readings_per_hour_24h": round(count_24h / 24, 1) if count_24h else 0,
                "expected_per_hour": 12,  # Every 5 minutes
                "data_completeness_24h": round(
                    min(100, (count_24h / (24 * 12)) * 100), 1
                ) if count_24h else 0
            }
        }


# =========================================
# Data Management Endpoints
# =========================================

@router.delete(
    "/data/{asset_id}",
    summary="Delete asset data",
    description="""
    Delete all sensor data for an asset.
    
    **Warning:** This action cannot be undone.
    """
)
async def delete_asset_data(
    asset_id: str,
    confirm: bool = Query(
        default=False,
        description="Must be true to confirm deletion"
    ),
    db: Session = Depends(get_db)
):
    """Delete all data for an asset."""
    if not confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must set confirm=true to delete data"
        )
    
    with DatabaseManager(db) as db_manager:
        deleted_count = db_manager.delete_asset_data(asset_id)
        
        return {
            "success": True,
            "asset_id": asset_id,
            "deleted_readings": deleted_count,
            "message": f"Deleted {deleted_count} readings for asset {asset_id}"
                }
