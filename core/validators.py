"""
Physics-Guard Validation Layer

This module implements validation rules based on physical laws and
thermodynamic principles. It ensures that sensor data is physically
plausible before storage and analysis.

Philosophy:
- Hard failures: Physically impossible → Reject immediately
- Soft warnings: Suspicious but possible → Accept with warnings  
- The goal is to catch sensor errors, not to filter unusual events

Why This Matters:
- Bad data in = Bad predictions out
- Sensor wiring errors are common
- Calibration drift happens over time
- Communication errors corrupt values
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """Severity levels for validation issues."""
    ERROR = "error"        # Physically impossible - must reject
    WARNING = "warning"    # Suspicious - accept with warning
    INFO = "info"          # Informational note


@dataclass
class ValidationIssue:
    """
    A single validation issue found in the data.
    
    Attributes:
        severity: How serious is this issue
        rule_name: Identifier for the rule that was violated
        message: Human-readable description
        metric_name: Which sensor/metric has the issue
        actual_value: The problematic value
        expected_range: What the value should be
        recommendation: How to fix the issue
    """
    severity: ValidationSeverity
    rule_name: str
    message: str
    metric_name: Optional[str] = None
    actual_value: Optional[float] = None
    expected_range: Optional[str] = None
    recommendation: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "severity": self.severity.value,
            "rule_name": self.rule_name,
            "message": self.message,
            "metric_name": self.metric_name,
            "actual_value": self.actual_value,
            "expected_range": self.expected_range,
            "recommendation": self.recommendation,
        }


@dataclass
class ValidationResult:
    """
    Result of validating sensor data.
    
    Attributes:
        is_valid: True if data can be accepted (possibly with warnings)
        status: "accepted", "accepted_with_warnings", or "rejected"
        issues: List of all validation issues found
    """
    is_valid: bool
    status: str
    issues: List[ValidationIssue] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        errors = [i for i in self.issues if i.severity == ValidationSeverity.ERROR]
        warnings = [i for i in self.issues if i.severity == ValidationSeverity.WARNING]
        infos = [i for i in self.issues if i.severity == ValidationSeverity.INFO]
        
        return {
            "is_valid": self.is_valid,
            "status": self.status,
            "error_count": len(errors),
            "warning_count": len(warnings),
            "info_count": len(infos),
            "issues": [issue.to_dict() for issue in self.issues],
        }


class PhysicsGuard:
    """
    Physics-based validation guard for sensor data.
    
    This class implements validation rules that ensure sensor data
    is physically plausible. It catches common issues like:
    - Swapped sensor connections (return/supply reversed)
    - Sensor calibration errors
    - Data entry mistakes
    - Communication/transmission errors
    
    It does NOT try to detect all anomalies - that's the job of the
    health scoring and ML systems. This only catches impossible physics.
    
    Example:
        guard = PhysicsGuard()
        result = guard.validate({
            "chw_supply_temp": 6.7,
            "chw_return_temp": 12.2,  # Valid: return > supply
            "load_percent": 80
        })
        print(result.status)  # "accepted"
        
        result = guard.validate({
            "chw_supply_temp": 12.2,
            "chw_return_temp": 6.7,  # Invalid: return < supply (impossible!)
        })
        print(result.status)  # "rejected"
    """
    
    def __init__(self, strict_mode: bool = False):
        """
        Initialize the physics guard.
        
        Args:
            strict_mode: If True, treat warnings as errors (reject more)
        """
        self.strict_mode = strict_mode
        
        # Define typical operating ranges for soft validation
        # Values outside these trigger warnings, not errors
        self.typical_ranges = {
            "chw_supply_temp": (4.0, 12.0),       # °C (39-54°F)
            "chw_return_temp": (8.0, 18.0),       # °C (46-64°F)
            "cdw_inlet_temp": (18.0, 38.0),       # °C (64-100°F)
            "cdw_outlet_temp": (23.0, 45.0),      # °C (73-113°F)
            "ambient_temp": (-10.0, 50.0),        # °C (14-122°F)
            "vibration_rms": (0.0, 15.0),         # mm/s
            "power_kw": (0.0, 2000.0),            # kW
            "load_percent": (0.0, 100.0),         # %
            "kw_per_ton": (0.35, 1.5),            # kW/ton
            "approach_temp": (0.5, 10.0),         # °C
            "phase_imbalance": (0.0, 15.0),       # %
            "delta_t": (1.5, 12.0),               # °C
        }
    
    def validate(self, data: Dict[str, Any]) -> ValidationResult:
        """
        Validate sensor data against physics rules.
        
        Args:
            data: Dictionary containing sensor readings
            
        Returns:
            ValidationResult with status and any issues found
        """
        issues: List[ValidationIssue] = []
        
        # Run all validation rules
        issues.extend(self._validate_thermal_directionality(data))
        issues.extend(self._validate_absolute_bounds(data))
        issues.extend(self._validate_derived_metrics(data))
        issues.extend(self._validate_operational_consistency(data))
        issues.extend(self._validate_typical_ranges(data))
        
        # Determine overall result
        errors = [i for i in issues if i.severity == ValidationSeverity.ERROR]
        warnings = [i for i in issues if i.severity == ValidationSeverity.WARNING]
        
        if errors:
            return ValidationResult(
                is_valid=False,
                status="rejected",
                issues=issues
            )
        elif warnings:
            if self.strict_mode:
                # In strict mode, warnings become errors
                for w in warnings:
                    w.severity = ValidationSeverity.ERROR
                return ValidationResult(
                    is_valid=False,
                    status="rejected",
                    issues=issues
                )
            return ValidationResult(
                is_valid=True,
                status="accepted_with_warnings",
                issues=issues
            )
        else:
            return ValidationResult(
                is_valid=True,
                status="accepted",
                issues=issues
            )
    
    def _validate_thermal_directionality(self, data: Dict[str, Any]) -> List[ValidationIssue]:
        """
        Validate that heat flows in the correct direction.
        
        Physics: 
            Heat ALWAYS flows from hot to cold (2nd Law of Thermodynamics).
            
            In a chiller:
            - Chilled water absorbs heat from building → return > supply
            - Condenser water absorbs heat from refrigerant → outlet > inlet
            
        Common Causes of Violation:
            - Sensor wiring swapped during installation
            - Sensor labels incorrect in BMS
            - Communication error corrupting values
        """
        issues = []
        
        chw_supply = data.get("chw_supply_temp")
        chw_return = data.get("chw_return_temp")
        cdw_inlet = data.get("cdw_inlet_temp")
        cdw_outlet = data.get("cdw_outlet_temp")
        
        # Rule 1: Chilled water return must be warmer than supply
        if chw_supply is not None and chw_return is not None:
            if chw_return <= chw_supply:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    rule_name="chw_thermal_direction",
                    message="Chilled water return must be warmer than supply (heat is absorbed from building)",
                    metric_name="chw_return_temp",
                    actual_value=chw_return,
                    expected_range=f"> {chw_supply}°C (supply temp)",
                    recommendation="Check CHW temperature sensor wiring - supply and return may be swapped"
                ))
        
        # Rule 2: Condenser water outlet must be warmer than inlet
        if cdw_inlet is not None and cdw_outlet is not None:
            if cdw_outlet <= cdw_inlet:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    rule_name="cdw_thermal_direction",
                    message="Condenser water outlet must be warmer than inlet (heat is rejected to cooling tower)",
                    metric_name="cdw_outlet_temp",
                    actual_value=cdw_outlet,
                    expected_range=f"> {cdw_inlet}°C (inlet temp)",
                    recommendation="Check CDW temperature sensor wiring - inlet and outlet may be swapped"
                ))
        
        return issues
    
    def _validate_absolute_bounds(self, data: Dict[str, Any]) -> List[ValidationIssue]:
        """
        Validate that values are within physically possible bounds.
        
        These are hard limits that cannot be violated under any circumstances.
        """
        issues = []
        
        # Load percent: 0-100% by definition
        load_percent = data.get("load_percent")
        if load_percent is not None:
            if load_percent < 0:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    rule_name="load_percent_negative",
                    message="Load percent cannot be negative",
                    metric_name="load_percent",
                    actual_value=load_percent,
                    expected_range="0 - 100",
                    recommendation="Check load calculation logic or sensor"
                ))
            elif load_percent > 100:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    rule_name="load_percent_over_100",
                    message="Load percent cannot exceed 100%",
                    metric_name="load_percent",
                    actual_value=load_percent,
                    expected_range="0 - 100",
                    recommendation="Check load calculation - may need recalibration to actual capacity"
                ))
        
        # Power: Cannot be negative (conservation of energy)
        power_kw = data.get("power_kw")
        if power_kw is not None and power_kw < 0:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                rule_name="power_non_negative",
                message="Power consumption cannot be negative",
                metric_name="power_kw",
                actual_value=power_kw,
                expected_range=">= 0 kW",
                recommendation="Check power meter wiring and CT orientation"
            ))
        
        # Vibration: Cannot be negative (RMS is always positive)
        vibration_rms = data.get("vibration_rms")
        if vibration_rms is not None and vibration_rms < 0:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                rule_name="vibration_non_negative",
                message="Vibration RMS cannot be negative",
                metric_name="vibration_rms",
                actual_value=vibration_rms,
                expected_range=">= 0 mm/s",
                recommendation="Check vibration sensor signal processing"
            ))
        
        # Currents: Cannot be negative (we measure magnitude)
        for phase in ["current_r", "current_y", "current_b"]:
            current = data.get(phase)
            if current is not None and current < 0:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    rule_name=f"{phase}_non_negative",
                    message=f"Current ({phase}) cannot be negative",
                    metric_name=phase,
                    actual_value=current,
                    expected_range=">= 0 A",
                    recommendation="Check current transformer wiring and polarity"
                ))
        
        # Runtime hours: Cannot be negative
        runtime_hours = data.get("runtime_hours")
        if runtime_hours is not None and runtime_hours < 0:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                rule_name="runtime_non_negative",
                message="Runtime hours cannot be negative",
                metric_name="runtime_hours",
                actual_value=runtime_hours,
                expected_range=">= 0 hours",
                recommendation="Check runtime counter logic"
            ))
        
        return issues
    
    def _validate_derived_metrics(self, data: Dict[str, Any]) -> List[ValidationIssue]:
        """
        Validate derived physics metrics.
        """
        issues = []
        
        # Approach temperature cannot be negative
        # (Refrigerant cannot be colder than the water cooling it)
        approach_temp = data.get("approach_temp")
        if approach_temp is not None and approach_temp < 0:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                rule_name="approach_non_negative",
                message="Approach temperature cannot be negative",
                metric_name="approach_temp",
                actual_value=approach_temp,
                expected_range=">= 0°C",
                recommendation="Refrigerant saturation temp calculation may be incorrect, or CDW temp sensor issue"
            ))
        
        # Delta-T should be positive when chiller is running
        delta_t = data.get("delta_t")
        power_kw = data.get("power_kw", 0)
        if delta_t is not None and power_kw > 10:  # Chiller running
            if delta_t <= 0:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    rule_name="delta_t_positive_when_running",
                    message="Delta-T must be positive when chiller is running",
                    metric_name="delta_t",
                    actual_value=delta_t,
                    expected_range="> 0°C when running",
                    recommendation="Check temperature sensors or verify chiller is actually producing cooling"
                ))
        
        return issues
    
    def _validate_operational_consistency(self, data: Dict[str, Any]) -> List[ValidationIssue]:
        """
        Validate consistency between related operational metrics.
        
        These are logical checks, not physics checks.
        """
        issues = []
        
        power_kw = data.get("power_kw", 0)
        load_percent = data.get("load_percent")
        vibration = data.get("vibration_rms", 0)
        
        # If power is zero, load should be low/zero (chiller off)
        if power_kw == 0 and load_percent is not None and load_percent > 10:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                rule_name="power_load_consistency",
                message="Load percent is high but power consumption is zero",
                metric_name="load_percent",
                actual_value=load_percent,
                expected_range="< 10% when power is 0",
                recommendation="Verify power meter is reading correctly, or load calculation has correct inputs"
            ))
        
        # If power is zero but vibration is high (chiller off but shaking?)
        if power_kw == 0 and vibration > 5.0:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                rule_name="power_vibration_consistency",
                message="High vibration detected but power is zero (chiller should be off)",
                metric_name="vibration_rms",
                actual_value=vibration,
                expected_range="< 1.0 mm/s when power is 0",
                recommendation="Check if vibration sensor is picking up external sources, or power meter issue"
            ))
        
        return issues
    
    def _validate_typical_ranges(self, data: Dict[str, Any]) -> List[ValidationIssue]:
        """
        Check if values are within typical operating ranges.
        
        These are soft checks - values outside typical ranges are
        unusual but not impossible. They generate warnings, not errors.
        """
        issues = []
        
        for metric_name, (min_val, max_val) in self.typical_ranges.items():
            value = data.get(metric_name)
            
            if value is None:
                continue
            
            if value < min_val or value > max_val:
                # Determine severity based on how far outside range
                deviation_factor = 0
                if value < min_val:
                    deviation_factor = (min_val - value) / max(abs(min_val), 1)
                else:
                    deviation_factor = (value - max_val) / max(abs(max_val), 1)
                
                # Large deviations get warnings, small ones get info
                if deviation_factor > 0.5:
                    severity = ValidationSeverity.WARNING
                else:
                    severity = ValidationSeverity.INFO
                
                issues.append(ValidationIssue(
                    severity=severity,
                    rule_name=f"{metric_name}_typical_range",
                    message=f"{metric_name} is outside typical operating range",
                    metric_name=metric_name,
                    actual_value=round(value, 2),
                    expected_range=f"{min_val} - {max_val}",
                    recommendation=f"Verify {metric_name} sensor accuracy and operating conditions"
                ))
        
        # Special case: kW/ton "too good to be true"
        kw_per_ton = data.get("kw_per_ton")
        if kw_per_ton is not None and kw_per_ton > 0:
            if kw_per_ton < 0.35:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    rule_name="kw_per_ton_too_efficient",
                    message="kW/ton is suspiciously low - efficiency appears too good to be true",
                    metric_name="kw_per_ton",
                    actual_value=round(kw_per_ton, 3),
                    expected_range="0.5 - 1.2 kW/ton typical",
                    recommendation="Verify power meter accuracy and flow sensor calibration"
                ))
            elif kw_per_ton > 1.5:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    rule_name="kw_per_ton_very_poor",
                    message="kW/ton is very high - poor efficiency",
                    metric_name="kw_per_ton",
                    actual_value=round(kw_per_ton, 3),
                    expected_range="0.5 - 1.2 kW/ton typical",
                    recommendation="Investigate chiller performance - possible fouling, refrigerant, or mechanical issues"
                ))
        
        return issues


def validate_sensor_data(data: Dict[str, Any], strict: bool = False) -> ValidationResult:
    """
    Convenience function to validate sensor data.
    
    Args:
        data: Sensor data dictionary
        strict: If True, treat warnings as errors
        
    Returns:
        ValidationResult
        
    Example:
        result = validate_sensor_data({
            "chw_supply_temp": 6.7,
            "chw_return_temp": 12.2,
            "power_kw": 280
        })
        
        if result.is_valid:
            print("Data accepted")
        else:
            print(f"Data rejected: {result.issues[0].message}")
    """
    guard = PhysicsGuard(strict_mode=strict)
    return guard.validate(data)
