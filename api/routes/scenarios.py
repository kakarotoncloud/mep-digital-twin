"""
Scenario Generation Endpoints

This module provides endpoints for generating synthetic data
with various failure scenarios. This is essential for:
- Testing and demonstration
- Training and education
- System validation
- Showcasing predictive maintenance capabilities

Key Features:
- List available failure scenarios
- Generate synthetic data with selected scenario
- Option to ingest directly or download
- Detailed scenario information with "failure stories"
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from api.database import get_db, DatabaseManager
from api.models import (
    ScenarioRequest,
    ScenarioResponse,
    ScenarioInfo,
    ScenarioListResponse,
    ScenarioType,
)
from engine.generator import ChillerDataGenerator, generate_scenario_data
from engine.failure_scenarios import ScenarioLibrary, FailureType
from core.physics import PhysicsCalculator
from core.validators import PhysicsGuard
from core.health_score import HealthScoreEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scenarios", tags=["Scenario Generation"])

# Initialize components
physics_calculator = PhysicsCalculator()
physics_guard = PhysicsGuard()
health_engine = HealthScoreEngine()


def scenario_type_to_failure_type(scenario_type: ScenarioType) -> FailureType:
    """Convert API ScenarioType to engine FailureType."""
    mapping = {
        ScenarioType.HEALTHY: FailureType.HEALTHY,
        ScenarioType.TUBE_FOULING: FailureType.TUBE_FOULING,
        ScenarioType.BEARING_WEAR: FailureType.BEARING_WEAR,
        ScenarioType.REFRIGERANT_LEAK: FailureType.REFRIGERANT_LEAK,
        ScenarioType.ELECTRICAL_ISSUE: FailureType.ELECTRICAL_ISSUE,
        ScenarioType.POST_MAINTENANCE_MISALIGNMENT: FailureType.POST_MAINTENANCE_MISALIGNMENT,
        ScenarioType.LOW_LOAD_INEFFICIENCY: FailureType.LOW_LOAD_INEFFICIENCY,
    }
    return mapping.get(scenario_type, FailureType.HEALTHY)


# =========================================
# Scenario Information Endpoints
# =========================================

@router.get(
    "",
    response_model=ScenarioListResponse,
    summary="List available scenarios",
    description="""
    Get a list of all available failure scenarios that can be generated.
    
    Each scenario simulates a specific failure mode with realistic
    physics-based progression of symptoms.
    """
)
async def list_scenarios():
    """List all available scenarios."""
    scenarios = ScenarioLibrary.get_all_scenarios()
    
    return ScenarioListResponse(
        scenarios=[
            ScenarioInfo(
                name=s.name,
                type=s.failure_type.value,
                description=s.description,
                duration_days=s.duration_days,
                affected_metrics=s.get_affected_metrics(),
                story=None  # Don't include full story in list
            )
            for s in scenarios
        ]
    )


@router.get(
    "/{scenario_type}",
    response_model=ScenarioInfo,
    summary="Get scenario details",
    description="""
    Get detailed information about a specific scenario, including
    the full "failure story" that explains the progression.
    """
)
async def get_scenario_details(
    scenario_type: ScenarioType
):
    """Get details for a specific scenario."""
    failure_type = scenario_type_to_failure_type(scenario_type)
    scenario = ScenarioLibrary.get_scenario_by_type(failure_type)
    
    if not scenario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scenario not found: {scenario_type}"
        )
    
    return ScenarioInfo(
        name=scenario.name,
        type=scenario.failure_type.value,
        description=scenario.description,
        duration_days=scenario.duration_days,
        affected_metrics=scenario.get_affected_metrics(),
        story=scenario.story
    )


# =========================================
# Data Generation Endpoints
# =========================================

@router.post(
    "/generate",
    response_model=ScenarioResponse,
    summary="Generate scenario data",
    description="""
    Generate synthetic sensor data with a specified failure scenario.
    
    **Options:**
    - `scenario_type`: Type of failure to simulate
    - `duration_days`: Duration of simulation (default: scenario's default)
    - `asset_id`: Asset ID for generated data
    - `ingest`: Whether to store in database (default: true)
    - `interval_minutes`: Time between readings (default: 5)
    
    **Use Cases:**
    - Demo preparation
    - Testing health algorithms
    - Training exercises
    - System validation
    """
)
async def generate_scenario(
    request: ScenarioRequest,
    db: Session = Depends(get_db)
):
    """Generate and optionally ingest scenario data."""
    failure_type = scenario_type_to_failure_type(request.scenario_type)
    scenario = ScenarioLibrary.get_scenario_by_type(
        failure_type,
        duration_days=request.duration_days
    )
    
    if not scenario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scenario not found: {request.scenario_type}"
        )
    
    # Calculate time range
    duration = request.duration_days or scenario.duration_days
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=duration)
    
    # Generate data
    generator = ChillerDataGenerator(asset_id=request.asset_id)
    generator.set_scenario(scenario)
    
    readings = generator.generate_to_list(
        start_time=start_time,
        duration_days=duration,
        interval_minutes=request.interval_minutes
    )
    
    logger.info(f"Generated {len(readings)} readings for scenario: {scenario.name}")
    
    ingested_count = 0
    
    if request.ingest:
        with DatabaseManager(db) as db_manager:
            for reading in readings:
                try:
                    # Calculate derived metrics
                    if all(k in reading for k in ["chw_supply_temp", "chw_return_temp", "power_kw"]):
                        metrics = physics_calculator.calculate_all_metrics(
                            chw_supply_temp=reading["chw_supply_temp"],
                            chw_return_temp=reading["chw_return_temp"],
                            cdw_inlet_temp=reading.get("cdw_inlet_temp", 29),
                            cdw_outlet_temp=reading.get("cdw_outlet_temp", 35),
                            power_kw=reading["power_kw"],
                            current_r=reading.get("current_r", 0),
                            current_y=reading.get("current_y", 0),
                            current_b=reading.get("current_b", 0),
                            chw_flow_gpm=reading.get("chw_flow_gpm")
                        )
                        reading.update(metrics)
                    
                    # Calculate health score
                    health_metrics = {}
                    if reading.get("vibration_rms") is not None:
                        health_metrics["vibration_rms"] = reading["vibration_rms"]
                    if reading.get("approach_temp") is not None:
                        health_metrics["approach_temp"] = reading["approach_temp"]
                    if reading.get("phase_imbalance") is not None:
                        health_metrics["phase_imbalance"] = reading["phase_imbalance"]
                    if reading.get("kw_per_ton") is not None:
                        health_metrics["kw_per_ton"] = reading["kw_per_ton"]
                    if reading.get("delta_t") is not None:
                        health_metrics["delta_t"] = reading["delta_t"]
                    
                    if health_metrics:
                        health_result = health_engine.calculate(health_metrics)
                        reading["health_score"] = health_result.overall_score
                        reading["health_breakdown"] = health_result.to_dict()
                    
                    # Add validation status
                    reading["validation_status"] = "accepted"
                    
                    # Convert time string to proper format
                    if isinstance(reading.get("time"), str):
                        reading["time"] = datetime.fromisoformat(reading["time"].replace("Z", "+00:00"))
                    
                    db_manager.insert_sensor_data(reading)
                    ingested_count += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to ingest reading: {e}")
                    continue
    
    return ScenarioResponse(
        success=True,
        scenario=ScenarioInfo(
            name=scenario.name,
            type=scenario.failure_type.value,
            description=scenario.description,
            duration_days=duration,
            affected_metrics=scenario.get_affected_metrics(),
            story=scenario.story
        ),
        readings_generated=len(readings),
        readings_ingested=ingested_count,
        time_range={
            "start": start_time,
            "end": end_time
        },
        message=f"Generated {len(readings)} readings, ingested {ingested_count}"
    )


@router.post(
    "/generate/{scenario_type}/quick",
    summary="Quick scenario generation",
    description="""
    Quick endpoint to generate and ingest a scenario with defaults.
    
    Just specify the scenario type and optional duration.
    """
)
async def quick_generate(
    scenario_type: ScenarioType,
    days: int = Query(default=None, ge=1, le=90, description="Duration in days"),
    asset_id: str = Query(default="CH-001", description="Asset ID"),
    db: Session = Depends(get_db)
):
    """Quick generate with minimal parameters."""
    request = ScenarioRequest(
        scenario_type=scenario_type,
        duration_days=days,
        asset_id=asset_id,
        ingest=True,
        interval_minutes=5
    )
    
    return await generate_scenario(request, db)


@router.get(
    "/generate/{scenario_type}/preview",
    summary="Preview scenario data",
    description="""
    Preview what generated data looks like without storing it.
    
    Returns a sample of readings that would be generated.
    """
)
async def preview_scenario(
    scenario_type: ScenarioType,
    samples: int = Query(default=10, ge=1, le=100, description="Number of samples"),
    days: int = Query(default=7, ge=1, le=30, description="Duration in days"),
    asset_id: str = Query(default="CH-001", description="Asset ID")
):
    """Preview scenario data without ingesting."""
    failure_type = scenario_type_to_failure_type(scenario_type)
    scenario = ScenarioLibrary.get_scenario_by_type(failure_type, duration_days=days)
    
    if not scenario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scenario not found: {scenario_type}"
        )
    
    # Generate data
    generator = ChillerDataGenerator(asset_id=asset_id)
    generator.set_scenario(scenario)
    
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=days)
    
    readings = generator.generate_to_list(
        start_time=start_time,
        duration_days=days,
        interval_minutes=5
    )
    
    # Sample evenly across the readings
    sample_rate = max(1, len(readings) // samples)
    sampled = readings[::sample_rate][:samples]
    
    # Add derived metrics to samples
    for reading in sampled:
        if all(k in reading for k in ["chw_supply_temp", "chw_return_temp", "power_kw"]):
            try:
                metrics = physics_calculator.calculate_all_metrics(
                    chw_supply_temp=reading["chw_supply_temp"],
                    chw_return_temp=reading["chw_return_temp"],
                    cdw_inlet_temp=reading.get("cdw_inlet_temp", 29),
                    cdw_outlet_temp=reading.get("cdw_outlet_temp", 35),
                    power_kw=reading["power_kw"],
                    current_r=reading.get("current_r", 0),
                    current_y=reading.get("current_y", 0),
                    current_b=reading.get("current_b", 0),
                )
                reading.update(metrics)
            except Exception:
                pass
    
    return {
        "scenario": {
            "name": scenario.name,
            "type": scenario.failure_type.value,
            "description": scenario.description,
            "affected_metrics": scenario.get_affected_metrics()
        },
        "preview": {
            "total_readings": len(readings),
            "samples_shown": len(sampled),
            "time_range": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            }
        },
        "sample_readings": sampled
    }


# =========================================
# Demo Setup Endpoints
# =========================================

@router.post(
    "/demo/setup",
    summary="Set up demo data",
    description="""
    Set up a complete demo environment with multiple scenarios.
    
    This will:
    1. Clear existing data for the asset
    2. Generate healthy baseline data
    3. Add a failure scenario at the end
    
    Perfect for preparing demonstrations.
    """
)
async def setup_demo(
    asset_id: str = Query(default="CH-001", description="Asset ID"),
    healthy_days: int = Query(default=7, ge=1, le=30, description="Days of healthy data"),
    failure_scenario: ScenarioType = Query(
        default=ScenarioType.TUBE_FOULING,
        description="Failure scenario to add"
    ),
    failure_days: int = Query(default=14, ge=1, le=60, description="Days of failure data"),
    clear_existing: bool = Query(default=True, description="Clear existing data first"),
    db: Session = Depends(get_db)
):
    """Set up complete demo environment."""
    with DatabaseManager(db) as db_manager:
        # Clear existing data if requested
        if clear_existing:
            deleted = db_manager.delete_asset_data(asset_id)
            logger.info(f"Cleared {deleted} existing readings for {asset_id}")
        
        total_ingested = 0
        
        # Generate healthy data first
        healthy_scenario = ScenarioLibrary.healthy_operation(duration_days=healthy_days)
        generator = ChillerDataGenerator(asset_id=asset_id)
        generator.set_scenario(healthy_scenario)
        
        healthy_start = datetime.utcnow() - timedelta(days=healthy_days + failure_days)
        healthy_readings = generator.generate_to_list(
            start_time=healthy_start,
            duration_days=healthy_days,
            interval_minutes=5
        )
        
        # Ingest healthy data
        for reading in healthy_readings:
            try:
                if isinstance(reading.get("time"), str):
                    reading["time"] = datetime.fromisoformat(reading["time"].replace("Z", "+00:00"))
                
                # Add basic metrics
                if all(k in reading for k in ["chw_supply_temp", "chw_return_temp", "power_kw"]):
                    metrics = physics_calculator.calculate_all_metrics(
                        chw_supply_temp=reading["chw_supply_temp"],
                        chw_return_temp=reading["chw_return_temp"],
                        cdw_inlet_temp=reading.get("cdw_inlet_temp", 29),
                        cdw_outlet_temp=reading.get("cdw_outlet_temp", 35),
                        power_kw=reading["power_kw"],
                        current_r=reading.get("current_r", 0),
                        current_y=reading.get("current_y", 0),
                        current_b=reading.get("current_b", 0),
                    )
                    reading.update(metrics)
                
                # Calculate health
                health_metrics = {
                    k: reading[k] for k in 
                    ["vibration_rms", "approach_temp", "phase_imbalance", "kw_per_ton", "delta_t"]
                    if reading.get(k) is not None
                }
                if health_metrics:
                    health_result = health_engine.calculate(health_metrics)
                    reading["health_score"] = health_result.overall_score
                    reading["health_breakdown"] = health_result.to_dict()
                
                reading["validation_status"] = "accepted"
                db_manager.insert_sensor_data(reading)
                total_ingested += 1
            except Exception as e:
                logger.warning(f"Failed to ingest healthy reading: {e}")
        
        # Generate failure data
        failure_type = scenario_type_to_failure_type(failure_scenario)
        fail_scenario = ScenarioLibrary.get_scenario_by_type(failure_type, duration_days=failure_days)
        
        generator.set_scenario(fail_scenario)
        failure_start = datetime.utcnow() - timedelta(days=failure_days)
        failure_readings = generator.generate_to_list(
            start_time=failure_start,
            duration_days=failure_days,
            interval_minutes=5
        )
        
        # Ingest failure data
        for reading in failure_readings:
            try:
                if isinstance(reading.get("time"), str):
                    reading["time"] = datetime.fromisoformat(reading["time"].replace("Z", "+00:00"))
                
                if all(k in reading for k in ["chw_supply_temp", "chw_return_temp", "power_kw"]):
                    metrics = physics_calculator.calculate_all_metrics(
                        chw_supply_temp=reading["chw_supply_temp"],
                        chw_return_temp=reading["chw_return_temp"],
                        cdw_inlet_temp=reading.get("cdw_inlet_temp", 29),
                        cdw_outlet_temp=reading.get("cdw_outlet_temp", 35),
                        power_kw=reading["power_kw"],
                        current_r=reading.get("current_r", 0),
                        current_y=reading.get("current_y", 0),
                        current_b=reading.get("current_b", 0),
                    )
                    reading.update(metrics)
                
                health_metrics = {
                    k: reading[k] for k in 
                    ["vibration_rms", "approach_temp", "phase_imbalance", "kw_per_ton", "delta_t"]
                    if reading.get(k) is not None
                }
                if health_metrics:
                    health_result = health_engine.calculate(health_metrics)
                    reading["health_score"] = health_result.overall_score
                    reading["health_breakdown"] = health_result.to_dict()
                
                reading["validation_status"] = "accepted"
                db_manager.insert_sensor_data(reading)
                total_ingested += 1
            except Exception as e:
                logger.warning(f"Failed to ingest failure reading: {e}")
        
        return {
            "success": True,
            "asset_id": asset_id,
            "setup": {
                "cleared_existing": clear_existing,
                "healthy_days": healthy_days,
                "failure_scenario": failure_scenario.value,
                "failure_days": failure_days
            },
            "results": {
                "healthy_readings": len(healthy_readings),
                "failure_readings": len(failure_readings),
                "total_ingested": total_ingested
            },
            "time_range": {
                "start": healthy_start.isoformat(),
                "end": datetime.utcnow().isoformat()
            },
            "message": f"Demo setup complete. Generated {total_ingested} readings over {healthy_days + failure_days} days."
  }
