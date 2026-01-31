"""
Pydantic Models for API Request/Response Validation

This module defines all the data models used by the API for:
- Request body validation
- Response serialization
- Documentation generation (OpenAPI/Swagger)

All models use Pydantic v2 syntax for validation and serialization.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, field_validator, model_validator


# =========================================
# Enums
# =========================================

class OperatingMode(str, Enum):
    """Chiller operating modes."""
    AUTO = "AUTO"
    MANUAL = "MANUAL"
    STANDBY = "STANDBY"
    OFF = "OFF"


class ValidationStatus(str, Enum):
    """Data validation status."""
    ACCEPTED = "accepted"
    ACCEPTED_WITH_WARNINGS = "accepted_with_warnings"
    REJECTED = "rejected"


class HealthCategory(str, Enum):
    """Health score categories."""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    CRITICAL = "critical"


class ScenarioType(str, Enum):
    """Available failure scenarios."""
    HEALTHY = "healthy"
    TUBE_FOULING = "tube_fouling"
    BEARING_WEAR = "bearing_wear"
    REFRIGERANT_LEAK = "refrigerant_leak"
    ELECTRICAL_ISSUE = "electrical_issue"
    POST_MAINTENANCE_MISALIGNMENT = "post_maintenance_misalignment"
    LOW_LOAD_INEFFICIENCY = "low_load_inefficiency"


# =========================================
# Sensor Data Models
# =========================================

class SensorDataInput(BaseModel):
    """
    Input model for sensor data ingestion.
    
    All fields are optional to allow partial updates,
    but the physics validation will check for required
    combinations.
    """
    # Timestamp (optional - will use current time if not provided)
    time: Optional[datetime] = Field(
        default=None,
        description="Timestamp of the reading (ISO 8601 format)"
    )
    
    # Asset identification
    asset_id: str = Field(
        default="CH-001",
        description="Unique identifier for the chiller asset",
        min_length=1,
        max_length=50
    )
    
    # Thermal sensors (°C)
    chw_supply_temp: Optional[float] = Field(
        default=None,
        description="Chilled water supply temperature (°C)",
        ge=-10, le=30
    )
    chw_return_temp: Optional[float] = Field(
        default=None,
        description="Chilled water return temperature (°C)",
        ge=-10, le=35
    )
    cdw_inlet_temp: Optional[float] = Field(
        default=None,
        description="Condenser water inlet temperature (°C)",
        ge=0, le=50
    )
    cdw_outlet_temp: Optional[float] = Field(
        default=None,
        description="Condenser water outlet temperature (°C)",
        ge=0, le=60
    )
    ambient_temp: Optional[float] = Field(
        default=None,
        description="Ambient temperature (°C)",
        ge=-40, le=60
    )
    
    # Mechanical sensors
    vibration_rms: Optional[float] = Field(
        default=None,
        description="Vibration RMS velocity (mm/s)",
        ge=0, le=50
    )
    vibration_freq: Optional[float] = Field(
        default=None,
        description="Dominant vibration frequency (Hz)",
        ge=0, le=500
    )
    runtime_hours: Optional[float] = Field(
        default=None,
        description="Total runtime hours",
        ge=0
    )
    start_stop_cycles: Optional[int] = Field(
        default=None,
        description="Start/stop cycles today",
        ge=0, le=100
    )
    
    # Electrical sensors
    current_r: Optional[float] = Field(
        default=None,
        description="R-phase current (Amps)",
        ge=0, le=2000
    )
    current_y: Optional[float] = Field(
        default=None,
        description="Y-phase current (Amps)",
        ge=0, le=2000
    )
    current_b: Optional[float] = Field(
        default=None,
        description="B-phase current (Amps)",
        ge=0, le=2000
    )
    power_kw: Optional[float] = Field(
        default=None,
        description="Power consumption (kW)",
        ge=0, le=5000
    )
    
    # Operational parameters
    load_percent: Optional[float] = Field(
        default=None,
        description="Load percentage (0-100)",
        ge=0, le=100
    )
    operating_mode: Optional[OperatingMode] = Field(
        default=OperatingMode.AUTO,
        description="Operating mode"
    )
    alarm_status: Optional[int] = Field(
        default=0,
        description="Alarm status (0=normal, 1=alarm)",
        ge=0, le=1
    )
    chw_flow_gpm: Optional[float] = Field(
        default=None,
        description="Chilled water flow rate (GPM)",
        ge=0, le=10000
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "asset_id": "CH-001",
                "chw_supply_temp": 6.7,
                "chw_return_temp": 12.2,
                "cdw_inlet_temp": 29.4,
                "cdw_outlet_temp": 35.0,
                "ambient_temp": 25.0,
                "vibration_rms": 2.1,
                "power_kw": 280.0,
                "current_r": 195.0,
                "current_y": 198.0,
                "current_b": 197.0,
                "load_percent": 78.5,
                "operating_mode": "AUTO"
            }
        }


class SensorDataBatch(BaseModel):
    """Batch of sensor readings for bulk ingestion."""
    readings: List[SensorDataInput] = Field(
        ...,
        description="List of sensor readings",
        min_length=1,
        max_length=1000
    )


# =========================================
# Validation Response Models
# =========================================

class ValidationIssue(BaseModel):
    """A single validation issue."""
    severity: str = Field(..., description="error, warning, or info")
    rule_name: str = Field(..., description="Name of the violated rule")
    message: str = Field(..., description="Human-readable description")
    metric_name: Optional[str] = Field(None, description="Affected metric")
    actual_value: Optional[float] = Field(None, description="The problematic value")
    expected_range: Optional[str] = Field(None, description="Expected value range")
    recommendation: Optional[str] = Field(None, description="How to fix")


class ValidationResponse(BaseModel):
    """Response from physics validation."""
    is_valid: bool = Field(..., description="Whether data was accepted")
    status: ValidationStatus = Field(..., description="Validation status")
    error_count: int = Field(default=0, description="Number of errors")
    warning_count: int = Field(default=0, description="Number of warnings")
    issues: List[ValidationIssue] = Field(
        default_factory=list,
        description="List of validation issues"
    )


# =========================================
# Ingestion Response Models
# =========================================

class DerivedMetrics(BaseModel):
    """Calculated physics metrics."""
    delta_t: Optional[float] = Field(None, description="Temperature differential (°C)")
    cooling_tons: Optional[float] = Field(None, description="Cooling capacity (tons)")
    kw_per_ton: Optional[float] = Field(None, description="Efficiency (kW/ton)")
    approach_temp: Optional[float] = Field(None, description="Condenser approach (°C)")
    phase_imbalance: Optional[float] = Field(None, description="Current imbalance (%)")
    cop: Optional[float] = Field(None, description="Coefficient of Performance")


class IngestResponse(BaseModel):
    """Response from data ingestion endpoint."""
    success: bool = Field(..., description="Whether ingestion succeeded")
    message: str = Field(..., description="Status message")
    asset_id: str = Field(..., description="Asset identifier")
    timestamp: datetime = Field(..., description="Timestamp of reading")
    validation: ValidationResponse = Field(..., description="Validation results")
    derived_metrics: Optional[DerivedMetrics] = Field(
        None, 
        description="Calculated physics metrics"
    )
    health_score: Optional[float] = Field(
        None,
        description="Calculated health score (0-100)"
    )


class BatchIngestResponse(BaseModel):
    """Response from batch ingestion endpoint."""
    success: bool
    total_readings: int
    accepted: int
    rejected: int
    warnings: int
    message: str
    details: Optional[List[IngestResponse]] = None


# =========================================
# Health Score Models
# =========================================

class MetricBreakdown(BaseModel):
    """Health score breakdown for a single metric."""
    metric_name: str = Field(..., description="Name of the metric")
    raw_value: float = Field(..., description="Actual sensor value")
    normalized_score: float = Field(..., description="Score 0-100 for this metric")
    weighted_contribution: float = Field(..., description="Points contributed to overall")
    weight: float = Field(..., description="Weight factor used")
    status: str = Field(..., description="excellent/good/fair/poor/critical")
    message: str = Field(..., description="Human-readable assessment")


class HealthScoreResponse(BaseModel):
    """Complete health score response."""
    asset_id: str = Field(..., description="Asset identifier")
    timestamp: datetime = Field(..., description="Time of assessment")
    overall_score: float = Field(..., description="Overall health score (0-100)")
    category: HealthCategory = Field(..., description="Health category")
    primary_concern: Optional[str] = Field(
        None,
        description="Most significant issue (if any)"
    )
    recommendations: List[str] = Field(
        default_factory=list,
        description="Actionable recommendations"
    )
    breakdown: List[MetricBreakdown] = Field(
        default_factory=list,
        description="Per-metric score breakdown"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "asset_id": "CH-001",
                "timestamp": "2024-01-15T14:30:00Z",
                "overall_score": 82.5,
                "category": "good",
                "primary_concern": None,
                "recommendations": [],
                "breakdown": [
                    {
                        "metric_name": "vibration_rms",
                        "raw_value": 2.3,
                        "normalized_score": 92.0,
                        "weighted_contribution": 32.2,
                        "weight": 0.35,
                        "status": "excellent",
                        "message": "✅ Excellent Mechanical vibration level: 2.30 mm/s"
                    }
                ]
            }
        }


# =========================================
# Query Response Models
# =========================================

class SensorReading(BaseModel):
    """Complete sensor reading with derived metrics."""
    time: datetime
    asset_id: str
    
    # Raw sensors
    chw_supply_temp: Optional[float] = None
    chw_return_temp: Optional[float] = None
    cdw_inlet_temp: Optional[float] = None
    cdw_outlet_temp: Optional[float] = None
    ambient_temp: Optional[float] = None
    vibration_rms: Optional[float] = None
    vibration_freq: Optional[float] = None
    runtime_hours: Optional[float] = None
    start_stop_cycles: Optional[int] = None
    current_r: Optional[float] = None
    current_y: Optional[float] = None
    current_b: Optional[float] = None
    power_kw: Optional[float] = None
    load_percent: Optional[float] = None
    operating_mode: Optional[str] = None
    alarm_status: Optional[int] = None
    chw_flow_gpm: Optional[float] = None
    
    # Derived metrics
    delta_t: Optional[float] = None
    kw_per_ton: Optional[float] = None
    approach_temp: Optional[float] = None
    phase_imbalance: Optional[float] = None
    cooling_tons: Optional[float] = None
    cop: Optional[float] = None
    
    # Health
    health_score: Optional[float] = None
    health_breakdown: Optional[Dict[str, Any]] = None
    
    # Validation
    validation_status: Optional[str] = None
    validation_warnings: Optional[List[Dict[str, Any]]] = None
    
    class Config:
        from_attributes = True


class LatestReadingResponse(BaseModel):
    """Response with latest sensor reading."""
    asset_id: str
    reading: Optional[SensorReading] = None
    message: str


class HistoryResponse(BaseModel):
    """Response with historical sensor readings."""
    asset_id: str
    start_time: datetime
    end_time: datetime
    reading_count: int
    readings: List[SensorReading]


# =========================================
# Scenario Generation Models
# =========================================

class ScenarioRequest(BaseModel):
    """Request to generate synthetic scenario data."""
    scenario_type: ScenarioType = Field(
        ...,
        description="Type of failure scenario"
    )
    duration_days: Optional[int] = Field(
        default=None,
        description="Duration in days (uses scenario default if not specified)",
        ge=1, le=365
    )
    asset_id: str = Field(
        default="CH-001",
        description="Asset ID for generated data"
    )
    ingest: bool = Field(
        default=True,
        description="Whether to ingest generated data into database"
    )
    interval_minutes: int = Field(
        default=5,
        description="Minutes between readings",
        ge=1, le=60
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "scenario_type": "tube_fouling",
                "duration_days": 30,
                "asset_id": "CH-001",
                "ingest": True,
                "interval_minutes": 5
            }
        }


class ScenarioInfo(BaseModel):
    """Information about a scenario."""
    name: str
    type: str
    description: str
    duration_days: int
    affected_metrics: List[str]
    story: Optional[str] = None


class ScenarioResponse(BaseModel):
    """Response from scenario generation."""
    success: bool
    scenario: ScenarioInfo
    readings_generated: int
    readings_ingested: int
    time_range: Dict[str, datetime]
    message: str


class ScenarioListResponse(BaseModel):
    """Response listing available scenarios."""
    scenarios: List[ScenarioInfo]


# =========================================
# Asset Models
# =========================================

class Asset(BaseModel):
    """Asset information."""
    asset_id: str
    asset_name: str
    asset_type: str
    location: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    capacity_tons: Optional[float] = None
    install_date: Optional[datetime] = None
    last_maintenance: Optional[datetime] = None
    status: str = "active"
    
    class Config:
        from_attributes = True


class AssetListResponse(BaseModel):
    """Response listing assets."""
    count: int
    assets: List[Asset]


# =========================================
# System Status Models
# =========================================

class SystemHealth(BaseModel):
    """System health check response."""
    status: str = Field(..., description="ok, degraded, or error")
    version: str = Field(..., description="API version")
    timestamp: datetime = Field(..., description="Current server time")
    database: str = Field(..., description="Database connection status")
    components: Dict[str, str] = Field(
        default_factory=dict,
        description="Status of system components"
    )


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: bool = True
    message: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
