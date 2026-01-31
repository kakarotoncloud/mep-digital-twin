"""
Synthetic Data Generator for Chiller Sensor Data

Generates realistic time-series sensor data for testing and demonstration,
including various failure scenarios with physics-based degradation patterns.

Features:
- Realistic baseline values based on design conditions
- Time-varying load profiles (diurnal patterns)
- Environmental correlations (ambient affects CDW temps)
- Failure scenario injection
- Physics-consistent relationships between metrics
- Export to JSON, CSV, or as Python lists
"""

import random
import math
import json
import csv
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Generator, Any
from dataclasses import dataclass, asdict

from .failure_scenarios import FailureScenario, FailureType, ScenarioLibrary


@dataclass
class ChillerBaseline:
    """
    Baseline operating parameters for a healthy chiller.
    
    These values represent typical design conditions for a
    500-ton water-cooled centrifugal chiller at 80% load.
    
    All values can be customized for different equipment types
    or operating conditions.
    """
    # Thermal parameters (°C)
    chw_supply_temp: float = 6.7      # 44°F - typical setpoint
    chw_return_temp: float = 12.2     # 54°F - 10°F design delta
    cdw_inlet_temp: float = 29.4      # 85°F - from cooling tower
    cdw_outlet_temp: float = 35.0     # 95°F - 10°F rise
    ambient_temp: float = 25.0        # 77°F - moderate conditions
    
    # Mechanical parameters
    vibration_rms: float = 2.0        # mm/s - good condition
    vibration_freq: float = 60.0      # Hz - motor frequency
    
    # Electrical parameters (for ~350kW at 80% load)
    current_r: float = 200.0          # Amps - R phase
    current_y: float = 200.0          # Amps - Y phase
    current_b: float = 200.0          # Amps - B phase
    power_kw: float = 280.0           # kW at 80% load
    
    # Operational parameters
    load_percent: float = 80.0        # % of capacity
    chw_flow_gpm: float = 1000.0      # Gallons per minute
    runtime_hours: float = 15000.0    # Total runtime
    start_stop_cycles: int = 2        # Per day


class ChillerDataGenerator:
    """
    Generator for synthetic chiller sensor data.
    
    This generator creates realistic sensor readings that can be used
    for testing, demonstrations, and development of the digital twin
    system. It supports:
    
    - Normal healthy operation with natural variation
    - Diurnal load patterns (higher during business hours)
    - Ambient temperature effects
    - Injection of failure scenarios
    - Multiple output formats
    
    Example:
        # Create generator
        gen = ChillerDataGenerator(asset_id="CH-001")
        
        # Generate 7 days of healthy data
        data = gen.generate_to_list(
            start_time=datetime.now() - timedelta(days=7),
            duration_days=7
        )
        
        # Generate with failure scenario
        gen.set_scenario(ScenarioLibrary.tube_fouling())
        failure_data = gen.generate_to_list(
            start_time=datetime.now() - timedelta(days=30),
            duration_days=30
        )
    """
    
    def __init__(
        self,
        asset_id: str = "CH-001",
        baseline: Optional[ChillerBaseline] = None,
        random_seed: Optional[int] = None
    ):
        """
        Initialize the generator.
        
        Args:
            asset_id: Identifier for the chiller asset
            baseline: Baseline operating parameters (uses defaults if None)
            random_seed: Seed for reproducible random generation
        """
        self.asset_id = asset_id
        self.baseline = baseline or ChillerBaseline()
        
        if random_seed is not None:
            random.seed(random_seed)
        
        self.scenario: Optional[FailureScenario] = None
        self.scenario_start_day: int = 0
    
    def set_scenario(
        self, 
        scenario: FailureScenario, 
        start_day: int = 0
    ) -> None:
        """
        Set the failure scenario to apply during generation.
        
        Args:
            scenario: The failure scenario to simulate
            start_day: Day number when the scenario should start
        """
        self.scenario = scenario
        self.scenario_start_day = start_day
    
    def clear_scenario(self) -> None:
        """Remove any active scenario (return to healthy generation)."""
        self.scenario = None
        self.scenario_start_day = 0
    
    def generate_reading(
        self,
        timestamp: datetime,
        day_number: int = 0
    ) -> Dict[str, Any]:
        """
        Generate a single sensor reading.
        
        Args:
            timestamp: Timestamp for the reading
            day_number: Day number in the simulation (for scenarios)
            
        Returns:
            Dictionary containing all sensor values and metadata
        """
        hour = timestamp.hour
        
        # Calculate load based on time of day
        load_factor = self._calculate_load_factor(hour)
        
        # Generate base values with natural variation
        data = self._generate_base_values(load_factor, hour, day_number)
        
        # Apply scenario modifiers if active
        if self.scenario and day_number >= self.scenario_start_day:
            scenario_day = day_number - self.scenario_start_day
            if scenario_day < self.scenario.duration_days:
                progress = scenario_day / self.scenario.duration_days
                data = self._apply_scenario(data, progress, scenario_day)
        
        # Add metadata
        data["time"] = timestamp.isoformat()
        data["asset_id"] = self.asset_id
        data["operating_mode"] = "AUTO"
        data["alarm_status"] = 0
        
        return data
    
    def generate_batch(
        self,
        start_time: datetime,
        duration_days: int,
        interval_minutes: int = 5
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Generate a batch of readings over a time period.
        
        Args:
            start_time: Start timestamp
            duration_days: Number of days to generate
            interval_minutes: Minutes between readings (default 5)
            
        Yields:
            Sensor reading dictionaries
        """
        current_time = start_time
        end_time = start_time + timedelta(days=duration_days)
        day_number = 0
        current_day = start_time.date()
        
        while current_time < end_time:
            # Track day number for scenarios
            if current_time.date() != current_day:
                day_number += 1
                current_day = current_time.date()
            
            yield self.generate_reading(current_time, day_number)
            current_time += timedelta(minutes=interval_minutes)
    
    def generate_to_list(
        self,
        start_time: datetime,
        duration_days: int,
        interval_minutes: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Generate readings and return as a list.
        
        Args:
            start_time: Start timestamp
            duration_days: Number of days to generate
            interval_minutes: Minutes between readings
            
        Returns:
            List of sensor reading dictionaries
        """
        return list(self.generate_batch(start_time, duration_days, interval_minutes))
    
    def generate_to_json(
        self,
        start_time: datetime,
        duration_days: int,
        interval_minutes: int = 5,
        filepath: Optional[str] = None,
        indent: int = 2
    ) -> str:
        """
        Generate readings and return/save as JSON.
        
        Args:
            start_time: Start timestamp
            duration_days: Number of days to generate
            interval_minutes: Minutes between readings
            filepath: Optional file path to save JSON
            indent: JSON indentation (default 2)
            
        Returns:
            JSON string
        """
        readings = self.generate_to_list(start_time, duration_days, interval_minutes)
        json_str = json.dumps(readings, indent=indent, default=str)
        
        if filepath:
            with open(filepath, 'w') as f:
                f.write(json_str)
        
        return json_str
    
    def generate_to_csv(
        self,
        start_time: datetime,
        duration_days: int,
        interval_minutes: int = 5,
        filepath: str = "sensor_data.csv"
    ) -> str:
        """
        Generate readings and save as CSV.
        
        Args:
            start_time: Start timestamp
            duration_days: Number of days to generate
            interval_minutes: Minutes between readings
            filepath: File path to save CSV
            
        Returns:
            Filepath of saved CSV
        """
        readings = self.generate_to_list(start_time, duration_days, interval_minutes)
        
        if not readings:
            return filepath
        
        # Get all field names from first reading
        fieldnames = list(readings[0].keys())
        
        with open(filepath, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(readings)
        
        return filepath
    
    def _calculate_load_factor(self, hour: int) -> float:
        """
        Calculate load factor based on time of day.
        
        Simulates typical commercial building load profile:
        - Low load at night (30-50%)
        - Ramp up in morning (6-9 AM)
        - Peak during business hours (9 AM - 6 PM)
        - Ramp down in evening
        
        Args:
            hour: Hour of day (0-23)
            
        Returns:
            Load factor (0.0 to 1.0)
        """
        if 0 <= hour < 6:
            # Night: low load
            base = 0.30
            variation = random.uniform(0, 0.10)
            
        elif 6 <= hour < 9:
            # Morning ramp-up
            progress = (hour - 6) / 3.0
            base = 0.35 + 0.40 * progress
            variation = random.uniform(-0.05, 0.08)
            
        elif 9 <= hour < 12:
            # Late morning: building toward peak
            base = 0.75 + (hour - 9) * 0.05
            variation = random.uniform(-0.05, 0.10)
            
        elif 12 <= hour < 14:
            # Midday peak
            base = 0.85
            variation = random.uniform(-0.05, 0.15)
            
        elif 14 <= hour < 18:
            # Afternoon: sustained high load
            base = 0.80
            variation = random.uniform(-0.08, 0.12)
            
        elif 18 <= hour < 21:
            # Evening ramp-down
            progress = (hour - 18) / 3.0
            base = 0.70 - 0.25 * progress
            variation = random.uniform(-0.05, 0.05)
            
        else:
            # Late night: low load
            base = 0.35
            variation = random.uniform(0, 0.08)
        
        return min(1.0, max(0.1, base + variation))
    
    def _generate_base_values(
        self, 
        load_factor: float, 
        hour: int,
        day: int
    ) -> Dict[str, float]:
        """
        Generate base sensor values with realistic noise.
        
        Args:
            load_factor: Current load as fraction (0.0 to 1.0)
            hour: Hour of day (0-23)
            day: Day number in simulation
            
        Returns:
            Dictionary of sensor values
        """
        b = self.baseline
        
        # Load percentage
        load_percent = load_factor * 100
        
        # =========================================
        # Power and Efficiency
        # =========================================
        # Power scales with load, but non-linearly due to part-load effects
        # At low loads, efficiency is worse (higher kW/ton)
        if load_factor < 0.3:
            efficiency_factor = 0.75  # Poor at very low load
        elif load_factor < 0.5:
            efficiency_factor = 0.85
        elif load_factor < 0.8:
            efficiency_factor = 0.95  # Best efficiency zone
        else:
            efficiency_factor = 0.90  # Slightly less efficient at high load
        
        # Base power at 80% load, scale for current load
        power_base = b.power_kw * (load_factor / 0.8)
        power_kw = power_base / efficiency_factor
        power_kw += random.gauss(0, power_kw * 0.02)  # 2% noise
        power_kw = max(10.0, power_kw)  # Minimum power when running
        
        # =========================================
        # Chilled Water Temperatures
        # =========================================
        # Supply temp is controlled, slight variation
        chw_supply = b.chw_supply_temp + random.gauss(0, 0.15)
        
        # Delta-T varies with load
        design_delta_t = b.chw_return_temp - b.chw_supply_temp
        actual_delta_t = design_delta_t * load_factor * 0.95
        actual_delta_t = max(actual_delta_t, 2.0)  # Minimum delta-T
        actual_delta_t += random.gauss(0, 0.3)
        
        chw_return = chw_supply + actual_delta_t
        
        # =========================================
        # Condenser Water Temperatures
        # =========================================
        # CDW inlet affected by ambient and time of day
        # Cooling towers work better at night
        ambient_variation = 5.0 * math.sin((hour - 6) * math.pi / 12)
        cdw_inlet = b.cdw_inlet_temp + ambient_variation * 0.5
        cdw_inlet += random.gauss(0, 0.5)
        
        # CDW rise depends on load (more heat to reject)
        design_cdw_rise = b.cdw_outlet_temp - b.cdw_inlet_temp
        actual_cdw_rise = design_cdw_rise * (0.6 + 0.5 * load_factor)
        actual_cdw_rise += random.gauss(0, 0.3)
        
        cdw_outlet = cdw_inlet + actual_cdw_rise
        
        # Ambient temperature (diurnal pattern)
        ambient = b.ambient_temp + 6.0 * math.sin((hour - 6) * math.pi / 12)
        ambient += random.gauss(0, 1.0)
        # Slight day-to-day variation
        ambient += 2.0 * math.sin(day * 0.3)
        
        # =========================================
        # Mechanical - Vibration
        # =========================================
        # Base vibration with slight load dependency
        vibration_rms = b.vibration_rms * (0.9 + 0.2 * load_factor)
        vibration_rms += random.gauss(0, 0.2)
        vibration_rms = max(0.5, vibration_rms)
        
        vibration_freq = b.vibration_freq + random.gauss(0, 0.3)
        
        # =========================================
        # Electrical
        # =========================================
        # Base current scales with power
        current_factor = power_kw / b.power_kw
        base_current = b.current_r * current_factor
        
        # Small natural imbalance (< 2% typical)
        current_r = base_current * (1.0 + random.gauss(0, 0.008))
        current_y = base_current * (1.0 + random.gauss(0, 0.008))
        current_b = base_current * (1.0 + random.gauss(0, 0.008))
        
        # =========================================
        # Operational
        # =========================================
        runtime_hours = b.runtime_hours + (day * 12) + random.uniform(0, 0.5)
        chw_flow = b.chw_flow_gpm + random.gauss(0, 10)
        start_stop = random.randint(1, 4)
        
        return {
            "chw_supply_temp": round(chw_supply, 2),
            "chw_return_temp": round(chw_return, 2),
            "cdw_inlet_temp": round(cdw_inlet, 2),
            "cdw_outlet_temp": round(cdw_outlet, 2),
            "ambient_temp": round(ambient, 2),
            "vibration_rms": round(vibration_rms, 2),
            "vibration_freq": round(vibration_freq, 1),
            "runtime_hours": round(runtime_hours, 1),
            "start_stop_cycles": start_stop,
            "current_r": round(current_r, 1),
            "current_y": round(current_y, 1),
            "current_b": round(current_b, 1),
            "power_kw": round(power_kw, 1),
            "load_percent": round(load_percent, 1),
            "chw_flow_gpm": round(chw_flow, 1),
        }
    
    def _apply_scenario(
        self,
        data: Dict[str, Any],
        progress: float,
        scenario_day: int
    ) -> Dict[str, Any]:
        """
        Apply scenario modifiers to generated data.
        
        Args:
            data: Base sensor data
            progress: Scenario progress (0.0 to 1.0)
            scenario_day: Day number within scenario
            
        Returns:
            Modified sensor data
        """
        if not self.scenario:
            return data
        
        modified = data.copy()
        
        for metric_name in data:
            if metric_name in self.scenario.modifiers:
                original_value = data[metric_name]
                if isinstance(original_value, (int, float)):
                    modified_value = self.scenario.apply_modifier(
                        metric_name, 
                        float(original_value), 
                        progress, 
                        scenario_day
                    )
                    # Keep same type (int or float)
                    if isinstance(original_value, int):
                        modified[metric_name] = int(round(modified_value))
                    else:
                        modified[metric_name] = round(modified_value, 2)
        
        return modified


# =========================================
# Convenience Functions
# =========================================

def generate_healthy_data(
    days: int = 7,
    asset_id: str = "CH-001",
    start_time: Optional[datetime] = None,
    interval_minutes: int = 5
) -> List[Dict[str, Any]]:
    """
    Generate healthy operation data.
    
    Args:
        days: Number of days to generate
        asset_id: Asset identifier
        start_time: Start timestamp (defaults to 'days' ago)
        interval_minutes: Minutes between readings
        
    Returns:
        List of sensor reading dictionaries
    """
    generator = ChillerDataGenerator(asset_id=asset_id)
    start = start_time or (datetime.now() - timedelta(days=days))
    return generator.generate_to_list(start, days, interval_minutes)


def generate_scenario_data(
    scenario_type: FailureType,
    days: Optional[int] = None,
    asset_id: str = "CH-001",
    start_time: Optional[datetime] = None,
    interval_minutes: int = 5
) -> List[Dict[str, Any]]:
    """
    Generate data with a specific failure scenario.
    
    Args:
        scenario_type: Type of failure to simulate
        days: Duration (uses scenario default if None)
        asset_id: Asset identifier
        start_time: Start timestamp
        interval_minutes: Minutes between readings
        
    Returns:
        List of sensor reading dictionaries
        
    Raises:
        ValueError: If scenario type is unknown
    """
    scenario = ScenarioLibrary.get_scenario_by_type(scenario_type)
    if not scenario:
        raise ValueError(f"Unknown scenario type: {scenario_type}")
    
    generator = ChillerDataGenerator(asset_id=asset_id)
    generator.set_scenario(scenario)
    
    duration = days or scenario.duration_days
    start = start_time or (datetime.now() - timedelta(days=duration))
    
    return generator.generate_to_list(start, duration, interval_minutes)


def get_available_scenarios() -> List[Dict[str, Any]]:
    """
    Get information about all available scenarios.
    
    Returns:
        List of scenario info dictionaries
    """
    scenarios = ScenarioLibrary.get_all_scenarios()
    return [
        {
            "name": s.name,
            "type": s.failure_type.value,
            "description": s.description,
            "duration_days": s.duration_days,
            "affected_metrics": s.get_affected_metrics(),
        }
        for s in scenarios
  ]
