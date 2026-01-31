"""
Core Module - MEP Digital Twin

This module contains the core business logic for the MEP Digital Twin system:
- Physics calculations (thermodynamics, efficiency metrics)
- Validation layer (Physics-Guard)
- Health scoring engine

These components are framework-agnostic and can be used by both
the API and the Streamlit dashboard.
"""

from .physics import PhysicsCalculator, quick_physics_check
from .validators import PhysicsGuard, ValidationResult, validate_sensor_data
from .health_score import HealthScoreEngine, HealthScore, calculate_health_score

__all__ = [
    # Physics calculations
    "PhysicsCalculator",
    "quick_physics_check",
    
    # Validation
    "PhysicsGuard",
    "ValidationResult", 
    "validate_sensor_data",
    
    # Health scoring
    "HealthScoreEngine",
    "HealthScore",
    "calculate_health_score",
]

__version__ = "0.1.0"
