"""
Physics Calculations for Chiller Performance Metrics

This module contains first-principles calculations for deriving
meaningful metrics from raw sensor data. All calculations are based
on ASHRAE standards and thermodynamic principles.

Key Metrics:
- Delta-T: Temperature differential across evaporator
- kW/Ton: Energy efficiency metric
- Approach Temperature: Condenser heat transfer efficiency
- Phase Imbalance: Electrical health indicator
- COP: Coefficient of Performance
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class PhysicsConstants:
    """
    Physical constants used in chiller calculations.
    
    These values are based on standard conditions and
    can be adjusted for specific applications.
    """
    
    # Water properties
    WATER_SPECIFIC_HEAT: float = 1.0      # BTU/(lb·°F)
    WATER_DENSITY: float = 8.33           # lb/gal at ~60°F
    
    # Conversion factors
    BTU_PER_TON_HOUR: float = 12000       # BTU/hr per ton of refrigeration
    KW_PER_TON: float = 3.517             # kW per ton (for COP calc)
    GPM_FACTOR: float = 500               # GPM to BTU/hr factor (8.33 × 60 × 1.0)
    
    # Typical operating ranges (for reference)
    TYPICAL_APPROACH_MIN: float = 0.5     # °C
    TYPICAL_APPROACH_MAX: float = 8.0     # °C
    TYPICAL_KW_PER_TON_MIN: float = 0.4   # kW/ton
    TYPICAL_KW_PER_TON_MAX: float = 1.5   # kW/ton
    TYPICAL_COP_MIN: float = 3.0          # dimensionless
    TYPICAL_COP_MAX: float = 8.0          # dimensionless
    
    # Demo/MVP assumptions (documented)
    DEFAULT_CHW_FLOW_GPM: float = 1000.0  # Assumed flow when not measured
    REFRIGERANT_SAT_OFFSET: float = 3.0   # Approximation when no pressure sensor


class PhysicsCalculator:
    """
    Calculator for chiller physics metrics.
    
    This class provides methods to calculate derived metrics from
    raw sensor readings. All methods are designed to be:
    - Pure functions (no side effects)
    - Well-documented with physics explanations
    - Defensive against bad inputs
    
    Example:
        calc = PhysicsCalculator()
        metrics = calc.calculate_all_metrics(
            chw_supply_temp=6.7,
            chw_return_temp=12.2,
            cdw_inlet_temp=29.4,
            cdw_outlet_temp=35.0,
            power_kw=280,
            current_r=200,
            current_y=200,
            current_b=200
        )
    """
    
    def __init__(self, constants: Optional[PhysicsConstants] = None):
        """
        Initialize the physics calculator.
        
        Args:
            constants: Custom physical constants. If None, uses defaults.
        """
        self.constants = constants or PhysicsConstants()
    
    def calculate_delta_t(
        self,
        chw_return_temp: float,
        chw_supply_temp: float
    ) -> float:
        """
        Calculate chilled water temperature differential (Delta-T).
        
        Args:
            chw_return_temp: Chilled water return temperature (°C)
            chw_supply_temp: Chilled water supply temperature (°C)
            
        Returns:
            Temperature differential in °C
            
        Physics Explanation:
            Delta-T represents the heat absorbed by the chilled water
            as it passes through the building's air handlers. 
            
            Q = m × Cp × ΔT
            
            Where:
            - Q = Heat absorbed (BTU/hr)
            - m = Mass flow rate (lb/hr)
            - Cp = Specific heat of water (BTU/lb·°F)
            - ΔT = Temperature rise (°F)
            
        Typical Values:
            - Design: 10°F (5.6°C) for comfort cooling
            - Low load: 4-6°F (2.2-3.3°C)
            - High load: 12-14°F (6.7-7.8°C)
            
        Diagnostic Value:
            - Low ΔT syndrome: Flow too high, control issues
            - High ΔT: Flow restriction, high load
        """
        return chw_return_temp - chw_supply_temp
    
    def calculate_cooling_tons(
        self,
        delta_t: float,
        chw_flow_gpm: Optional[float] = None
    ) -> float:
        """
        Calculate cooling capacity in tons of refrigeration.
        
        Args:
            delta_t: Temperature differential in °C
            chw_flow_gpm: Chilled water flow rate in GPM
            
        Returns:
            Cooling capacity in tons
            
        Formula:
            Tons = (GPM × ΔT°F × 500) / 12000
            
            Where:
            - 500 = 8.33 lb/gal × 60 min/hr × 1.0 BTU/(lb·°F)
            - 12000 = BTU/hr per ton of refrigeration
            
        Note:
            Input delta_t is in Celsius, converted internally to Fahrenheit.
        """
        if chw_flow_gpm is None:
            chw_flow_gpm = self.constants.DEFAULT_CHW_FLOW_GPM
        
        # Convert Celsius to Fahrenheit for BTU calculation
        delta_t_fahrenheit = delta_t * 9.0 / 5.0
        
        # Calculate tons
        tons = (chw_flow_gpm * delta_t_fahrenheit * self.constants.GPM_FACTOR) / self.constants.BTU_PER_TON_HOUR
        
        # Prevent negative or zero values
        return max(tons, 0.1)
    
    def calculate_kw_per_ton(
        self,
        power_kw: float,
        delta_t: float,
        chw_flow_gpm: Optional[float] = None
    ) -> float:
        """
        Calculate efficiency metric (kW/Ton).
        
        Args:
            power_kw: Compressor power consumption in kW
            delta_t: Temperature differential in °C
            chw_flow_gpm: Chilled water flow rate in GPM
            
        Returns:
            Efficiency in kW per ton of refrigeration
            
        Formula:
            kW/Ton = Power (kW) / Cooling Capacity (Tons)
            
        Typical Values:
            - Excellent: < 0.55 kW/ton
            - Good: 0.55 - 0.70 kW/ton
            - Average: 0.70 - 0.85 kW/ton
            - Poor: 0.85 - 1.00 kW/ton
            - Critical: > 1.00 kW/ton
            
        Diagnostic Value:
            Rising kW/ton indicates:
            - Condenser fouling
            - Refrigerant issues
            - Mechanical wear
            - Control problems
            
        Part-Load Consideration:
            Chillers are typically most efficient at 70-80% load.
            At low loads (<30%), kW/ton increases significantly.
        """
        if power_kw <= 0:
            return 0.0
        
        tons = self.calculate_cooling_tons(delta_t, chw_flow_gpm)
        
        if tons < 0.1:
            return 0.0
        
        return power_kw / tons
    
    def calculate_approach_temperature(
        self,
        cdw_outlet_temp: float,
        refrigerant_sat_temp: Optional[float] = None
    ) -> float:
        """
        Calculate condenser approach temperature.
        
        Args:
            cdw_outlet_temp: Condenser water outlet temperature in °C
            refrigerant_sat_temp: Refrigerant saturation temperature in °C
                                  If None, uses demo approximation.
                                  
        Returns:
            Approach temperature in °C
            
        Physics Explanation:
            Approach temperature is the difference between the refrigerant
            condensing temperature and the leaving condenser water temperature.
            
            Approach = T_refrigerant_sat - T_cdw_leaving
            
            In a real system, refrigerant saturation temperature is determined
            from condenser pressure using the refrigerant's P-T relationship
            (e.g., for R-134a, R-410A, etc.).
            
        MVP Approximation:
            When pressure sensors are not available, we approximate:
            T_refrigerant_sat ≈ T_cdw_outlet + 3.0°C
            
            This is documented as an assumption and should be replaced
            with actual pressure-based calculation in production.
            
        Typical Values:
            - Excellent: 1-2°C (clean tubes, good flow)
            - Normal: 2-3°C
            - Warning: 3-5°C (fouling beginning)
            - Critical: >5°C (significant fouling)
            
        Million-Dollar Insight:
            Every 1°C increase in approach temperature increases
            energy consumption by approximately 2-3%.
            
            For a 500-ton chiller running 4000 hours/year at $0.10/kWh:
            - 1°C degradation ≈ $5,000-8,000/year extra energy cost
            - Severe fouling (5°C) ≈ $25,000-40,000/year
        """
        if refrigerant_sat_temp is None:
            # Demo approximation - document this assumption
            refrigerant_sat_temp = cdw_outlet_temp + self.constants.REFRIGERANT_SAT_OFFSET
        
        approach = refrigerant_sat_temp - cdw_outlet_temp
        
        # Approach cannot be negative (would violate thermodynamics)
        return max(approach, 0.0)
    
    def calculate_phase_imbalance(
        self,
        current_r: float,
        current_y: float,
        current_b: float
    ) -> float:
        """
        Calculate three-phase current imbalance percentage.
        
        Args:
            current_r: R-phase (or A-phase) current in Amps
            current_y: Y-phase (or B-phase) current in Amps
            current_b: B-phase (or C-phase) current in Amps
            
        Returns:
            Phase imbalance as a percentage
            
        Formula:
            Average = (Ir + Iy + Ib) / 3
            Max Deviation = max(|Ir - Avg|, |Iy - Avg|, |Ib - Avg|)
            Imbalance % = (Max Deviation / Average) × 100
            
        Typical Values:
            - Excellent: < 1%
            - Normal: 1-2%
            - Warning: 2-5%
            - Critical: > 5%
            
        Physics Explanation:
            Phase imbalance causes negative-sequence currents in the motor,
            which create a magnetic field rotating opposite to the rotor.
            This causes:
            - Additional heating in the stator and rotor
            - Reduced torque
            - Increased vibration
            - Shortened motor life
            
        NEMA MG-1 Guidelines:
            - 1% voltage imbalance → 6-10% current imbalance
            - Prolonged operation at >5% imbalance can reduce motor life by 50%
            
        Common Causes:
            - Utility supply issues
            - Loose connections
            - Failed capacitors
            - Unequal cable impedances
        """
        currents = [current_r, current_y, current_b]
        
        # Handle edge cases
        if all(c <= 0 for c in currents):
            return 0.0
        
        avg_current = sum(currents) / 3
        
        if avg_current < 0.1:  # Motor not running or very low load
            return 0.0
        
        max_deviation = max(abs(c - avg_current) for c in currents)
        imbalance = (max_deviation / avg_current) * 100
        
        return imbalance
    
    def calculate_cop(
        self,
        delta_t: float,
        power_kw: float,
        chw_flow_gpm: Optional[float] = None
    ) -> float:
        """
        Calculate Coefficient of Performance (COP).
        
        Args:
            delta_t: Temperature differential in °C
            power_kw: Compressor power consumption in kW
            chw_flow_gpm: Chilled water flow rate in GPM
            
        Returns:
            COP (dimensionless ratio)
            
        Formula:
            COP = Cooling Effect (kW) / Power Input (kW)
            COP = Tons × 3.517 / Power (kW)
            
        Relationship to kW/Ton:
            COP = 3.517 / (kW/Ton)
            
        Typical Values:
            - Water-cooled centrifugal: 5.5 - 7.0
            - Water-cooled screw: 4.5 - 6.0
            - Air-cooled screw: 2.8 - 3.5
            - Air-cooled scroll: 2.5 - 3.2
            
        Note:
            COP varies with:
            - Lift (difference between evaporating and condensing temps)
            - Part-load ratio
            - Ambient/condenser water conditions
        """
        if power_kw <= 0:
            return 0.0
        
        tons = self.calculate_cooling_tons(delta_t, chw_flow_gpm)
        cooling_kw = tons * self.constants.KW_PER_TON
        
        return cooling_kw / power_kw
    
    def calculate_all_metrics(
        self,
        chw_supply_temp: float,
        chw_return_temp: float,
        cdw_inlet_temp: float,
        cdw_outlet_temp: float,
        power_kw: float,
        current_r: float,
        current_y: float,
        current_b: float,
        chw_flow_gpm: Optional[float] = None,
        refrigerant_sat_temp: Optional[float] = None
    ) -> Dict[str, float]:
        """
        Calculate all derived physics metrics from raw sensor data.
        
        This is the main entry point for calculating all metrics
        from a complete set of sensor readings.
        
        Args:
            chw_supply_temp: Chilled water supply temperature (°C)
            chw_return_temp: Chilled water return temperature (°C)
            cdw_inlet_temp: Condenser water inlet temperature (°C)
            cdw_outlet_temp: Condenser water outlet temperature (°C)
            power_kw: Compressor power consumption (kW)
            current_r: R-phase current (A)
            current_y: Y-phase current (A)
            current_b: B-phase current (A)
            chw_flow_gpm: Optional chilled water flow rate (GPM)
            refrigerant_sat_temp: Optional refrigerant saturation temp (°C)
            
        Returns:
            Dictionary containing all derived metrics:
            - delta_t: Temperature differential (°C)
            - cooling_tons: Cooling capacity (tons)
            - kw_per_ton: Efficiency (kW/ton)
            - approach_temp: Condenser approach (°C)
            - phase_imbalance: Current imbalance (%)
            - cop: Coefficient of Performance
        """
        # Calculate delta-T first (used by other calculations)
        delta_t = self.calculate_delta_t(chw_return_temp, chw_supply_temp)
        
        # Calculate all metrics
        cooling_tons = self.calculate_cooling_tons(delta_t, chw_flow_gpm)
        kw_per_ton = self.calculate_kw_per_ton(power_kw, delta_t, chw_flow_gpm)
        approach_temp = self.calculate_approach_temperature(cdw_outlet_temp, refrigerant_sat_temp)
        phase_imbalance = self.calculate_phase_imbalance(current_r, current_y, current_b)
        cop = self.calculate_cop(delta_t, power_kw, chw_flow_gpm)
        
        return {
            "delta_t": round(delta_t, 3),
            "cooling_tons": round(cooling_tons, 2),
            "kw_per_ton": round(kw_per_ton, 3),
            "approach_temp": round(approach_temp, 3),
            "phase_imbalance": round(phase_imbalance, 2),
            "cop": round(cop, 2),
        }


def quick_physics_check(sensor_data: Dict[str, Any]) -> Dict[str, float]:
    """
    Convenience function for quick physics calculations.
    
    Useful for API endpoints and testing.
    
    Args:
        sensor_data: Dictionary containing sensor readings
        
    Returns:
        Dictionary of calculated physics metrics
        
    Example:
        data = {
            "chw_supply_temp": 6.7,
            "chw_return_temp": 12.2,
            "cdw_inlet_temp": 29.4,
            "cdw_outlet_temp": 35.0,
            "power_kw": 280,
            "current_r": 200,
            "current_y": 200,
            "current_b": 200
        }
        metrics = quick_physics_check(data)
        print(f"Efficiency: {metrics['kw_per_ton']} kW/ton")
    """
    calc = PhysicsCalculator()
    
    return calc.calculate_all_metrics(
        chw_supply_temp=sensor_data.get("chw_supply_temp", 0),
        chw_return_temp=sensor_data.get("chw_return_temp", 0),
        cdw_inlet_temp=sensor_data.get("cdw_inlet_temp", 0),
        cdw_outlet_temp=sensor_data.get("cdw_outlet_temp", 0),
        power_kw=sensor_data.get("power_kw", 0),
        current_r=sensor_data.get("current_r", 0),
        current_y=sensor_data.get("current_y", 0),
        current_b=sensor_data.get("current_b", 0),
        chw_flow_gpm=sensor_data.get("chw_flow_gpm"),
        refrigerant_sat_temp=sensor_data.get("refrigerant_sat_temp"),
      )
