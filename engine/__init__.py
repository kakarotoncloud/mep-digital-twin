"""
Engine Module - Synthetic Data Generation

This module provides synthetic data generation capabilities for
testing and demonstration of the MEP Digital Twin system.

Key Components:
- ChillerDataGenerator: Generates realistic sensor readings
- FailureScenario: Defines failure mode patterns
- ScenarioLibrary: Pre-built failure scenarios

Usage:
    from engine import ChillerDataGenerator, ScenarioLibrary
    
    # Generate healthy data
    generator = ChillerDataGenerator(asset_id="CH-001")
    readings = generator.generate_to_list(
        start_time=datetime.now(),
        duration_days=7
    )
    
    # Generate failure scenario
    scenario = ScenarioLibrary.tube_fouling()
    generator.set_scenario(scenario)
    failure_readings = generator.generate_to_list(
        start_time=datetime.now(),
        duration_days=30
    )
"""

from .failure_scenarios import (
    FailureScenario,
    FailureType,
    ScenarioLibrary,
)
from .generator import (
    ChillerDataGenerator,
    ChillerBaseline,
    generate_healthy_data,
    generate_scenario_data,
)

__all__ = [
    # Failure Scenarios
    "FailureScenario",
    "FailureType",
    "ScenarioLibrary",
    
    # Data Generator
    "ChillerDataGenerator",
    "ChillerBaseline",
    "generate_healthy_data",
    "generate_scenario_data",
]

__version__ = "0.1.0"
