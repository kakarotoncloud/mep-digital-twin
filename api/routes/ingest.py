"""
Data Ingestion Endpoints

This module handles sensor data ingestion with physics validation.
It's the primary entry point for getting data into the system.

Flow:
1. Receive sensor data (single or batch)
2. Validate against physics rules (Physics-Guard)
3. Calculate derived metrics
4. Calculate health score
5. Store in TimescaleDB
6. Return validation results and health assessment

Key Features:
- Physics-based validation (rejects impossible data)
- Automatic derived metric calculation
- Real-time health scoring
- Detailed validation feedback
"""

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.database import get_db, DatabaseManager
from api.models import (
    SensorDataInput,
    SensorDataBatch,
    IngestResponse,
    BatchIngestResponse,
    ValidationResponse,
    ValidationIssue,
    ValidationStatus,
    DerivedMetrics,
)
from core.physics import PhysicsCalculator
from core.validators import PhysicsGuard, ValidationResult
from core.health_score import HealthScoreEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingest", tags=["Data Ingestion"])

# Initialize core components
physics_calculator = PhysicsCalculator()
physics_guard = PhysicsGuard()
health_engine = HealthScoreEngine()


def process_sensor_data(
    data: SensorDataInput,
    db_manager: DatabaseManager
) -> IngestResponse:
    """
    Process a single sensor reading through the full pipeline.
    
    Args:
        data: Sensor data input
        db_manager: Database manager instance
        
    Returns:
        IngestResponse with validation and health results
    """
    # Set timestamp if not provided
    timestamp = data.time or datetime.utcnow()
    
    # Convert to dict for processing
    data_dict = data.model_dump(exclude_none=True)
    data_dict["time"] = timestamp
    
    # =========================================
    # Step 1: Physics Validation
    # =========================================
    validation_result = physics_guard.validate(data_dict)
    
    # Convert validation result to response model
    validation_response = ValidationResponse(
        is_valid=validation_result.is_valid,
        status=ValidationStatus(validation_result.status),
        error_count=len([i for i in validation_result.issues if i.severity.value == "error"]),
        warning_count=len([i for i in validation_result.issues if i.severity.value == "warning"]),
        issues=[
            ValidationIssue(
                severity=issue.severity.value,
                rule_name=issue.rule_name,
                message=issue.message,
                metric_name=issue.metric_name,
                actual_value=issue.actual_value,
                expected_range=issue.expected_range,
                recommendation=issue.recommendation
            )
            for issue in validation_result.issues
        ]
    )
    
    # If validation failed, return early
    if not validation_result.is_valid:
        return IngestResponse(
            success=False,
            message=f"Data rejected: {validation_result.issues[0].message if validation_result.issues else 'Validation failed'}",
            asset_id=data.asset_id,
            timestamp=timestamp,
            validation=validation_response,
            derived_metrics=None,
            health_score=None
        )
    
    # =========================================
    # Step 2: Calculate Derived Metrics
    # =========================================
    derived_metrics = None
    metrics_dict = {}
    
    # Check if we have enough data for physics calculations
    has_thermal = all([
        data.chw_supply_temp is not None,
        data.chw_return_temp is not None,
        data.cdw_outlet_temp is not None
    ])
    has_electrical = all([
        data.current_r is not None,
        data.current_y is not None,
        data.current_b is not None
    ])
    has_power = data.power_kw is not None
    
    if has_thermal and has_power:
        try:
            metrics_dict = physics_calculator.calculate_all_metrics(
                chw_supply_temp=data.chw_supply_temp,
                chw_return_temp=data.chw_return_temp,
                cdw_inlet_temp=data.cdw_inlet_temp or 29.0,  # Default if missing
                cdw_outlet_temp=data.cdw_outlet_temp,
                power_kw=data.power_kw,
                current_r=data.current_r or 0,
                current_y=data.current_y or 0,
                current_b=data.current_b or 0,
                chw_flow_gpm=data.chw_flow_gpm
            )
            
            derived_metrics = DerivedMetrics(
                delta_t=metrics_dict.get("delta_t"),
                cooling_tons=metrics_dict.get("cooling_tons"),
                kw_per_ton=metrics_dict.get("kw_per_ton"),
                approach_temp=metrics_dict.get("approach_temp"),
                phase_imbalance=metrics_dict.get("phase_imbalance"),
                cop=metrics_dict.get("cop")
            )
            
            # Add derived metrics to data dict for storage
            data_dict.update(metrics_dict)
            
        except Exception as e:
            logger.warning(f"Failed to calculate derived metrics: {e}")
    
    elif has_electrical:
        # At least calculate phase imbalance
        try:
            phase_imbalance = physics_calculator.calculate_phase_imbalance(
                data.current_r, data.current_y, data.current_b
            )
            metrics_dict["phase_imbalance"] = phase_imbalance
            data_dict["phase_imbalance"] = phase_imbalance
            
            derived_metrics = DerivedMetrics(phase_imbalance=phase_imbalance)
        except Exception as e:
            logger.warning(f"Failed to calculate phase imbalance: {e}")
    
    # =========================================
    # Step 3: Calculate Health Score
    # =========================================
    health_score = None
    health_breakdown = None
    
    # Build metrics for health scoring
    health_metrics = {}
    
    if data.vibration_rms is not None:
        health_metrics["vibration_rms"] = data.vibration_rms
    if metrics_dict.get("approach_temp") is not None:
        health_metrics["approach_temp"] = metrics_dict["approach_temp"]
    if metrics_dict.get("phase_imbalance") is not None:
        health_metrics["phase_imbalance"] = metrics_dict["phase_imbalance"]
    if metrics_dict.get("kw_per_ton") is not None:
        health_metrics["kw_per_ton"] = metrics_dict["kw_per_ton"]
    if metrics_dict.get("delta_t") is not None:
        health_metrics["delta_t"] = metrics_dict["delta_t"]
    
    if health_metrics:
        try:
            health_result = health_engine.calculate(health_metrics)
            health_score = health_result.overall_score
            health_breakdown = health_result.to_dict()
            
            # Add to data dict for storage
            data_dict["health_score"] = health_score
            data_dict["health_breakdown"] = health_breakdown
            
        except Exception as e:
            logger.warning(f"Failed to calculate health score: {e}")
    
    # =========================================
    # Step 4: Store in Database
    # =========================================
    # Add validation info
    data_dict["validation_status"] = validation_result.status
    if validation_result.issues:
        data_dict["validation_warnings"] = [
            issue.to_dict() if hasattr(issue, 'to_dict') else {
                "severity": issue.severity.value,
                "rule_name": issue.rule_name,
                "message": issue.message
            }
            for issue in validation_result.issues
            if issue.severity.value in ("warning", "info")
        ]
    
    try:
        db_manager.insert_sensor_data(data_dict)
        success = True
        message = "Data ingested successfully"
        
        if validation_result.status == "accepted_with_warnings":
            message += f" with {validation_response.warning_count} warning(s)"
            
    except Exception as e:
        logger.error(f"Failed to store sensor data: {e}")
        success = False
        message = f"Data validated but storage failed: {str(e)}"
    
    return IngestResponse(
        success=success,
        message=message,
        asset_id=data.asset_id,
        timestamp=timestamp,
        validation=validation_response,
        derived_metrics=derived_metrics,
        health_score=health_score
    )


# =========================================
# API Endpoints
# =========================================

@router.post(
    "",
    response_model=IngestResponse,
    summary="Ingest single sensor reading",
    description="""
    Ingest a single sensor reading with full physics validation.
    
    The endpoint will:
    1. Validate data against physical laws (Physics-Guard)
    2. Calculate derived metrics (kW/ton, approach temp, etc.)
    3. Calculate health score
    4. Store in TimescaleDB
    
    **Validation Levels:**
    - `accepted`: All validations passed
    - `accepted_with_warnings`: Data accepted but has suspicious values
    - `rejected`: Data violates physical laws (impossible data)
    
    **Example - Good Data:**
    ```json
    {
        "asset_id": "CH-001",
        "chw_supply_temp": 6.7,
        "chw_return_temp": 12.2,
        "cdw_inlet_temp": 29.4,
        "cdw_outlet_temp": 35.0,
        "power_kw": 280,
        "vibration_rms": 2.1
    }
    ```
    
    **Example - Rejected Data (impossible physics):**
    ```json
    {
        "asset_id": "CH-001",
        "chw_supply_temp": 12.2,
        "chw_return_temp": 6.7
    }
    ```
    This would be rejected because return temp cannot be less than supply temp.
    """
)
async def ingest_single(
    data: SensorDataInput,
    db: Session = Depends(get_db)
):
    """Ingest a single sensor reading."""
    with DatabaseManager(db) as db_manager:
        return process_sensor_data(data, db_manager)


@router.post(
    "/batch",
    response_model=BatchIngestResponse,
    summary="Ingest multiple sensor readings",
    description="""
    Ingest multiple sensor readings in a single request.
    
    Each reading is validated independently. The response includes
    counts of accepted, rejected, and warning readings.
    
    **Limits:**
    - Maximum 1000 readings per batch
    - Each reading is processed independently
    - Failed readings don't affect successful ones
    """
)
async def ingest_batch(
    batch: SensorDataBatch,
    db: Session = Depends(get_db)
):
    """Ingest a batch of sensor readings."""
    results = []
    accepted = 0
    rejected = 0
    warnings = 0
    
    with DatabaseManager(db) as db_manager:
        for reading in batch.readings:
            result = process_sensor_data(reading, db_manager)
            results.append(result)
            
            if result.success:
                accepted += 1
                if result.validation.status == ValidationStatus.ACCEPTED_WITH_WARNINGS:
                    warnings += 1
            else:
                rejected += 1
    
    return BatchIngestResponse(
        success=rejected == 0,
        total_readings=len(batch.readings),
        accepted=accepted,
        rejected=rejected,
        warnings=warnings,
        message=f"Processed {len(batch.readings)} readings: {accepted} accepted, {rejected} rejected",
        details=results if len(results) <= 10 else None  # Only include details for small batches
    )


@router.post(
    "/validate",
    response_model=ValidationResponse,
    summary="Validate data without storing",
    description="""
    Validate sensor data against physics rules without storing it.
    
    Useful for:
    - Testing sensor configurations
    - Debugging data quality issues
    - Pre-validation before batch uploads
    """
)
async def validate_only(data: SensorDataInput):
    """Validate sensor data without storing."""
    data_dict = data.model_dump(exclude_none=True)
    validation_result = physics_guard.validate(data_dict)
    
    return ValidationResponse(
        is_valid=validation_result.is_valid,
        status=ValidationStatus(validation_result.status),
        error_count=len([i for i in validation_result.issues if i.severity.value == "error"]),
        warning_count=len([i for i in validation_result.issues if i.severity.value == "warning"]),
        issues=[
            ValidationIssue(
                severity=issue.severity.value,
                rule_name=issue.rule_name,
                message=issue.message,
                metric_name=issue.metric_name,
                actual_value=issue.actual_value,
                expected_range=issue.expected_range,
                recommendation=issue.recommendation
            )
            for issue in validation_result.issues
        ]
    )


@router.post(
    "/calculate",
    response_model=DerivedMetrics,
    summary="Calculate derived metrics only",
    description="""
    Calculate derived physics metrics without validation or storage.
    
    Returns calculated values for:
    - Delta-T (temperature differential)
    - Cooling tons (capacity)
    - kW/Ton (efficiency)
    - Approach temperature
    - Phase imbalance
    - COP (Coefficient of Performance)
    """
)
async def calculate_metrics(data: SensorDataInput):
    """Calculate derived metrics from sensor data."""
    # Check required fields
    if data.chw_supply_temp is None or data.chw_return_temp is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="chw_supply_temp and chw_return_temp are required"
        )
    
    if data.power_kw is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="power_kw is required for efficiency calculations"
        )
    
    try:
        metrics = physics_calculator.calculate_all_metrics(
            chw_supply_temp=data.chw_supply_temp,
            chw_return_temp=data.chw_return_temp,
            cdw_inlet_temp=data.cdw_inlet_temp or 29.0,
            cdw_outlet_temp=data.cdw_outlet_temp or 35.0,
            power_kw=data.power_kw,
            current_r=data.current_r or 0,
            current_y=data.current_y or 0,
            current_b=data.current_b or 0,
            chw_flow_gpm=data.chw_flow_gpm
        )
        
        return DerivedMetrics(
            delta_t=metrics.get("delta_t"),
            cooling_tons=metrics.get("cooling_tons"),
            kw_per_ton=metrics.get("kw_per_ton"),
            approach_temp=metrics.get("approach_temp"),
            phase_imbalance=metrics.get("phase_imbalance"),
            cop=metrics.get("cop")
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Calculation failed: {str(e)}"
            )
