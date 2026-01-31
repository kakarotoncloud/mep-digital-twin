"""
Tests for Physics-Guard Validation

These tests verify that the validation logic correctly identifies
physically impossible data and generates appropriate warnings.

Run with: pytest tests/test_validators.py -v
"""

import pytest
from core.validators import (
    PhysicsGuard,
    ValidationResult,
    ValidationIssue,
    ValidationSeverity,
    validate_sensor_data
)


class TestValidationSeverity:
    """Test validation severity enum."""
    
    def test_severity_values(self):
        """Test all severity values exist."""
        assert ValidationSeverity.ERROR.value == "error"
        assert ValidationSeverity.WARNING.value == "warning"
        assert ValidationSeverity.INFO.value == "info"


class TestValidationResult:
    """Test ValidationResult dataclass."""
    
    def test_valid_result(self):
        """Test creating a valid result."""
        result = ValidationResult(
            is_valid=True,
            status="accepted",
            issues=[]
        )
        
        assert result.is_valid
        assert result.status == "accepted"
        assert len(result.issues) == 0
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        result = ValidationResult(
            is_valid=False,
            status="rejected",
            issues=[
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    rule_name="test_rule",
                    message="Test message"
                )
            ]
        )
        
        d = result.to_dict()
        
        assert d["is_valid"] == False
        assert d["status"] == "rejected"
        assert d["error_count"] == 1
        assert d["warning_count"] == 0
        assert len(d["issues"]) == 1


class TestThermalDirectionality:
    """Test thermal direction validation rules."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.guard = PhysicsGuard()
    
    def test_valid_chw_direction(self):
        """Test valid CHW thermal direction (return > supply)."""
        result = self.guard.validate({
            "chw_supply_temp": 6.7,
            "chw_return_temp": 12.2
        })
        
        # Should not have thermal direction errors
        errors = [i for i in result.issues 
                 if i.severity == ValidationSeverity.ERROR 
                 and "thermal" in i.rule_name]
        assert len(errors) == 0
    
    def test_invalid_chw_direction(self):
        """Test invalid CHW thermal direction (return < supply)."""
        result = self.guard.validate({
            "chw_supply_temp": 12.2,  # Higher than return!
            "chw_return_temp": 6.7    # Lower than supply!
        })
        
        assert not result.is_valid
        assert result.status == "rejected"
        
        # Should have CHW thermal direction error
        chw_errors = [i for i in result.issues 
                     if "chw_thermal_direction" in i.rule_name]
        assert len(chw_errors) == 1
        assert chw_errors[0].severity == ValidationSeverity.ERROR
    
    def test_valid_cdw_direction(self):
        """Test valid CDW thermal direction (outlet > inlet)."""
        result = self.guard.validate({
            "cdw_inlet_temp": 29.4,
            "cdw_outlet_temp": 35.0
        })
        
        # Should not have CDW thermal direction errors
        errors = [i for i in result.issues 
                 if i.severity == ValidationSeverity.ERROR 
                 and "cdw_thermal" in i.rule_name]
        assert len(errors) == 0
    
    def test_invalid_cdw_direction(self):
        """Test invalid CDW thermal direction (outlet < inlet)."""
        result = self.guard.validate({
            "cdw_inlet_temp": 35.0,   # Higher than outlet!
            "cdw_outlet_temp": 29.4   # Lower than inlet!
        })
        
        assert not result.is_valid
        
        cdw_errors = [i for i in result.issues 
                     if "cdw_thermal_direction" in i.rule_name]
        assert len(cdw_errors) == 1
    
    def test_equal_temps_rejected(self):
        """Test that equal supply/return temps are rejected."""
        result = self.guard.validate({
            "chw_supply_temp": 6.7,
            "chw_return_temp": 6.7  # Equal to supply
        })
        
        assert not result.is_valid


class TestAbsoluteBounds:
    """Test absolute bounds validation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.guard = PhysicsGuard()
    
    def test_valid_load_percent(self):
        """Test valid load percentage."""
        result = self.guard.validate({
            "load_percent": 75.0
        })
        
        errors = [i for i in result.issues 
                 if i.severity == ValidationSeverity.ERROR 
                 and "load_percent" in i.rule_name]
        assert len(errors) == 0
    
    def test_negative_load_percent(self):
        """Test negative load percentage is rejected."""
        result = self.guard.validate({
            "load_percent": -10.0
        })
        
        assert not result.is_valid
        
        errors = [i for i in result.issues 
                 if "load_percent" in i.rule_name]
        assert len(errors) == 1
    
    def test_over_100_load_percent(self):
        """Test over 100% load is rejected."""
        result = self.guard.validate({
            "load_percent": 150.0
        })
        
        assert not result.is_valid
    
    def test_negative_power(self):
        """Test negative power is rejected."""
        result = self.guard.validate({
            "power_kw": -50.0
        })
        
        assert not result.is_valid
        
        errors = [i for i in result.issues 
                 if "power" in i.rule_name.lower()]
        assert len(errors) == 1
    
    def test_negative_vibration(self):
        """Test negative vibration is rejected."""
        result = self.guard.validate({
            "vibration_rms": -1.0
        })
        
        assert not result.is_valid
    
    def test_negative_current(self):
        """Test negative current values are rejected."""
        result = self.guard.validate({
            "current_r": -100.0,
            "current_y": 200.0,
            "current_b": 200.0
        })
        
        assert not result.is_valid
        
        errors = [i for i in result.issues 
                 if "current_r" in i.rule_name]
        assert len(errors) == 1
    
    def test_negative_runtime(self):
        """Test negative runtime hours is rejected."""
        result = self.guard.validate({
            "runtime_hours": -100.0
        })
        
        assert not result.is_valid


class TestDerivedMetrics:
    """Test derived metric validation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.guard = PhysicsGuard()
    
    def test_negative_approach_temp(self):
        """Test negative approach temperature is rejected."""
        result = self.guard.validate({
            "approach_temp": -2.0
        })
        
        assert not result.is_valid
        
        errors = [i for i in result.issues 
                 if "approach" in i.rule_name]
        assert len(errors) == 1
    
    def test_valid_approach_temp(self):
        """Test valid approach temperature is accepted."""
        result = self.guard.validate({
            "approach_temp": 3.0
        })
        
        errors = [i for i in result.issues 
                 if i.severity == ValidationSeverity.ERROR 
                 and "approach" in i.rule_name]
        assert len(errors) == 0


class TestOperationalConsistency:
    """Test operational consistency validation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.guard = PhysicsGuard()
    
    def test_zero_power_high_load_warning(self):
        """Test warning when power is zero but load is high."""
        result = self.guard.validate({
            "power_kw": 0.0,
            "load_percent": 80.0
        })
        
        # Should be accepted but with warning
        assert result.is_valid
        assert result.status == "accepted_with_warnings"
        
        warnings = [i for i in result.issues 
                   if "power_load_consistency" in i.rule_name]
        assert len(warnings) == 1
    
    def test_zero_power_high_vibration_warning(self):
        """Test warning when power is zero but vibration is high."""
        result = self.guard.validate({
            "power_kw": 0.0,
            "vibration_rms": 8.0
        })
        
        assert result.is_valid
        
        warnings = [i for i in result.issues 
                   if "vibration" in i.rule_name]
        assert len(warnings) >= 1


class TestTypicalRanges:
    """Test typical range validation (soft warnings)."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.guard = PhysicsGuard()
    
    def test_normal_values_no_warnings(self):
        """Test that normal values don't trigger warnings."""
        result = self.guard.validate({
            "chw_supply_temp": 6.7,
            "chw_return_temp": 12.2,
            "vibration_rms": 2.0,
            "power_kw": 280.0
        })
        
        # Should be accepted without significant warnings
        assert result.is_valid
        
        # Count non-info issues
        significant_issues = [i for i in result.issues 
                            if i.severity != ValidationSeverity.INFO]
        assert len(significant_issues) == 0
    
    def test_high_vibration_warning(self):
        """Test that high vibration triggers warning."""
        result = self.guard.validate({
            "vibration_rms": 20.0  # Way above normal
        })
        
        assert result.is_valid  # Still accepted
        
        warnings = [i for i in result.issues 
                   if "vibration" in i.rule_name.lower() 
                   and i.severity == ValidationSeverity.WARNING]
        assert len(warnings) >= 1
    
    def test_kw_per_ton_too_good(self):
        """Test that suspiciously good kW/ton triggers warning."""
        result = self.guard.validate({
            "kw_per_ton": 0.30  # Too efficient to be true
        })
        
        assert result.is_valid
        
        warnings = [i for i in result.issues 
                   if "kw_per_ton" in i.rule_name and "too" in i.rule_name]
        assert len(warnings) == 1
    
    def test_kw_per_ton_very_poor(self):
        """Test that very poor kW/ton triggers warning."""
        result = self.guard.validate({
            "kw_per_ton": 2.0  # Very poor efficiency
        })
        
        assert result.is_valid
        
        warnings = [i for i in result.issues 
                   if "kw_per_ton" in i.rule_name]
        assert len(warnings) >= 1


class TestStrictMode:
    """Test strict mode functionality."""
    
    def test_strict_mode_rejects_warnings(self):
        """Test that strict mode converts warnings to errors."""
        guard = PhysicsGuard(strict_mode=True)
        
        result = guard.validate({
            "power_kw": 0.0,
            "load_percent": 80.0  # Inconsistent - would be warning
        })
        
        # In strict mode, this should be rejected
        assert not result.is_valid
        assert result.status == "rejected"
    
    def test_normal_mode_accepts_warnings(self):
        """Test that normal mode accepts data with warnings."""
        guard = PhysicsGuard(strict_mode=False)
        
        result = guard.validate({
            "power_kw": 0.0,
            "load_percent": 80.0
        })
        
        # In normal mode, this should be accepted with warnings
        assert result.is_valid
        assert result.status == "accepted_with_warnings"


class TestValidateSensorDataFunction:
    """Test the convenience function."""
    
    def test_convenience_function_valid(self):
        """Test convenience function with valid data."""
        result = validate_sensor_data({
            "chw_supply_temp": 6.7,
            "chw_return_temp": 12.2,
            "power_kw": 280.0
        })
        
        assert result.is_valid
    
    def test_convenience_function_invalid(self):
        """Test convenience function with invalid data."""
        result = validate_sensor_data({
            "chw_supply_temp": 12.2,
            "chw_return_temp": 6.7  # Invalid!
        })
        
        assert not result.is_valid
    
    def test_convenience_function_strict(self):
        """Test convenience function with strict mode."""
        result = validate_sensor_data({
            "power_kw": 0.0,
            "load_percent": 80.0
        }, strict=True)
        
        # Strict mode should reject
        assert not result.is_valid


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.guard = PhysicsGuard()
    
    def test_empty_data(self):
        """Test validation of empty data."""
        result = self.guard.validate({})
        
        # Empty data should be accepted (no rules violated)
        assert result.is_valid
    
    def test_none_values_ignored(self):
        """Test that None values are ignored."""
        result = self.guard.validate({
            "chw_supply_temp": None,
            "chw_return_temp": None,
            "power_kw": 280.0
        })
        
        # Should be accepted - None values don't violate rules
        assert result.is_valid
    
    def test_partial_thermal_data(self):
        """Test validation with only partial thermal data."""
        result = self.guard.validate({
            "chw_supply_temp": 6.7
            # Missing return temp
        })
        
        # Should be accepted - can't check direction with one value
        assert result.is_valid
    
    def test_boundary_load_100(self):
        """Test boundary condition: exactly 100% load."""
        result = self.guard.validate({
            "load_percent": 100.0
        })
        
        errors = [i for i in result.issues 
                 if i.severity == ValidationSeverity.ERROR]
        assert len(errors) == 0
    
    def test_boundary_load_0(self):
        """Test boundary condition: exactly 0% load."""
        result = self.guard.validate({
            "load_percent": 0.0
        })
        
        errors = [i for i in result.issues 
                 if i.severity == ValidationSeverity.ERROR]
        assert len(errors) == 0
    
    def test_very_small_positive_values(self):
        """Test very small positive values are accepted."""
        result = self.guard.validate({
            "power_kw": 0.001,
            "vibration_rms": 0.001,
            "current_r": 0.001
        })
        
        errors = [i for i in result.issues 
                 if i.severity == ValidationSeverity.ERROR]
        assert len(errors) == 0


class TestRecommendations:
    """Test that validation issues include helpful recommendations."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.guard = PhysicsGuard()
    
    def test_chw_direction_recommendation(self):
        """Test CHW direction error includes recommendation."""
        result = self.guard.validate({
            "chw_supply_temp": 12.0,
            "chw_return_temp": 6.0
        })
        
        issue = result.issues[0]
        assert issue.recommendation is not None
        assert len(issue.recommendation) > 0
        assert "sensor" in issue.recommendation.lower() or "wiring" in issue.recommendation.lower()
    
    def test_power_error_recommendation(self):
        """Test power error includes recommendation."""
        result = self.guard.validate({
            "power_kw": -100.0
        })
        
        issue = result.issues[0]
        assert issue.recommendation is not None


class TestIssueDetails:
    """Test that validation issues contain proper details."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.guard = PhysicsGuard()
    
    def test_issue_contains_actual_value(self):
        """Test that issues contain the actual problematic value."""
        result = self.guard.validate({
            "load_percent": 150.0
        })
        
        issue = next(i for i in result.issues if "load_percent" in i.rule_name)
        assert issue.actual_value == 150.0
    
    def test_issue_contains_expected_range(self):
        """Test that issues contain expected range."""
        result = self.guard.validate({
            "load_percent": 150.0
        })
        
        issue = next(i for i in result.issues if "load_percent" in i.rule_name)
        assert issue.expected_range is not None
        assert "100" in issue.expected_range
    
    def test_issue_contains_metric_name(self):
        """Test that issues identify the problematic metric."""
        result = self.guard.validate({
            "vibration_rms": -5.0
        })
        
        issue = next(i for i in result.issues if "vibration" in i.rule_name)
        assert issue.metric_name == "vibration_rms"
