"""
Tests for Physics Calculations

These tests verify that all physics calculations are correct
and handle edge cases appropriately.

Run with: pytest tests/test_physics.py -v
"""

import pytest
import math
from core.physics import PhysicsCalculator, PhysicsConstants, quick_physics_check


class TestPhysicsConstants:
    """Test physics constants are reasonable."""
    
    def test_constants_exist(self):
        """Verify all required constants are defined."""
        constants = PhysicsConstants()
        
        assert constants.WATER_SPECIFIC_HEAT == 1.0
        assert constants.WATER_DENSITY == 8.33
        assert constants.BTU_PER_TON_HOUR == 12000
        assert constants.KW_PER_TON == 3.517
        assert constants.GPM_FACTOR == 500
    
    def test_typical_ranges_are_reasonable(self):
        """Verify typical operating ranges make sense."""
        constants = PhysicsConstants()
        
        # Approach temp should be positive and reasonable
        assert constants.TYPICAL_APPROACH_MIN > 0
        assert constants.TYPICAL_APPROACH_MAX < 15
        
        # kW/ton should be in reasonable efficiency range
        assert constants.TYPICAL_KW_PER_TON_MIN > 0.3
        assert constants.TYPICAL_KW_PER_TON_MAX < 2.0


class TestDeltaT:
    """Tests for delta-T calculation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.calc = PhysicsCalculator()
    
    def test_normal_delta_t(self):
        """Test normal operating delta-T."""
        delta_t = self.calc.calculate_delta_t(
            chw_return_temp=12.2,
            chw_supply_temp=6.7
        )
        
        assert delta_t == pytest.approx(5.5, rel=0.01)
    
    def test_high_load_delta_t(self):
        """Test high load produces higher delta-T."""
        delta_t = self.calc.calculate_delta_t(
            chw_return_temp=15.0,
            chw_supply_temp=6.7
        )
        
        assert delta_t == pytest.approx(8.3, rel=0.01)
        assert delta_t > 5.5  # Higher than normal
    
    def test_low_load_delta_t(self):
        """Test low load produces lower delta-T."""
        delta_t = self.calc.calculate_delta_t(
            chw_return_temp=9.0,
            chw_supply_temp=6.7
        )
        
        assert delta_t == pytest.approx(2.3, rel=0.01)
        assert delta_t < 5.5  # Lower than normal
    
    def test_zero_delta_t(self):
        """Test zero delta-T (no load or bypass)."""
        delta_t = self.calc.calculate_delta_t(
            chw_return_temp=6.7,
            chw_supply_temp=6.7
        )
        
        assert delta_t == 0.0
    
    def test_negative_delta_t_possible(self):
        """Test that calculation allows negative (for validation to catch)."""
        # This is physically impossible but the calculator should compute it
        # The validator will catch this
        delta_t = self.calc.calculate_delta_t(
            chw_return_temp=5.0,
            chw_supply_temp=6.7
        )
        
        assert delta_t < 0  # Negative - validator should catch this


class TestCoolingTons:
    """Tests for cooling capacity calculation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.calc = PhysicsCalculator()
    
    def test_design_capacity(self):
        """Test capacity at design conditions."""
        # Design: 1000 GPM, 10°F delta (5.56°C)
        tons = self.calc.calculate_cooling_tons(
            delta_t=5.56,
            chw_flow_gpm=1000
        )
        
        # Should be approximately 500 tons
        assert tons == pytest.approx(500, rel=0.05)
    
    def test_half_load(self):
        """Test capacity at half load."""
        tons = self.calc.calculate_cooling_tons(
            delta_t=2.78,  # Half delta-T
            chw_flow_gpm=1000
        )
        
        # Should be approximately 250 tons
        assert tons == pytest.approx(250, rel=0.05)
    
    def test_default_flow(self):
        """Test that default flow is used when not specified."""
        tons = self.calc.calculate_cooling_tons(delta_t=5.56)
        
        # Should calculate with default 1000 GPM
        assert tons > 0
    
    def test_zero_delta_t_returns_minimum(self):
        """Test that zero delta-T returns minimum value (not zero)."""
        tons = self.calc.calculate_cooling_tons(
            delta_t=0,
            chw_flow_gpm=1000
        )
        
        # Should return minimum to prevent division by zero later
        assert tons >= 0.1
    
    def test_varying_flow_rates(self):
        """Test capacity scales with flow rate."""
        tons_low = self.calc.calculate_cooling_tons(delta_t=5.0, chw_flow_gpm=500)
        tons_high = self.calc.calculate_cooling_tons(delta_t=5.0, chw_flow_gpm=1000)
        
        # Double flow should give double capacity
        assert tons_high == pytest.approx(tons_low * 2, rel=0.01)


class TestKwPerTon:
    """Tests for efficiency (kW/Ton) calculation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.calc = PhysicsCalculator()
    
    def test_good_efficiency(self):
        """Test good efficiency calculation."""
        kw_per_ton = self.calc.calculate_kw_per_ton(
            power_kw=280,
            delta_t=5.56,
            chw_flow_gpm=1000
        )
        
        # 280 kW / ~500 tons = ~0.56 kW/ton
        assert kw_per_ton == pytest.approx(0.56, rel=0.1)
        assert kw_per_ton < 0.7  # Good efficiency
    
    def test_poor_efficiency(self):
        """Test poor efficiency (high kW/ton)."""
        kw_per_ton = self.calc.calculate_kw_per_ton(
            power_kw=500,
            delta_t=5.56,
            chw_flow_gpm=1000
        )
        
        # 500 kW / ~500 tons = ~1.0 kW/ton
        assert kw_per_ton == pytest.approx(1.0, rel=0.1)
        assert kw_per_ton >= 0.9  # Poor efficiency
    
    def test_zero_power_returns_zero(self):
        """Test that zero power returns zero efficiency."""
        kw_per_ton = self.calc.calculate_kw_per_ton(
            power_kw=0,
            delta_t=5.56,
            chw_flow_gpm=1000
        )
        
        assert kw_per_ton == 0.0
    
    def test_low_delta_t_increases_kw_per_ton(self):
        """Test that low delta-T (low load) shows higher kW/ton."""
        kw_per_ton_normal = self.calc.calculate_kw_per_ton(
            power_kw=280,
            delta_t=5.56,
            chw_flow_gpm=1000
        )
        
        kw_per_ton_low_load = self.calc.calculate_kw_per_ton(
            power_kw=150,  # Lower power but...
            delta_t=2.0,   # Much lower delta-T
            chw_flow_gpm=1000
        )
        
        # Low load often has worse kW/ton
        assert kw_per_ton_low_load > kw_per_ton_normal


class TestApproachTemperature:
    """Tests for approach temperature calculation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.calc = PhysicsCalculator()
    
    def test_normal_approach(self):
        """Test normal approach temperature."""
        approach = self.calc.calculate_approach_temperature(
            cdw_outlet_temp=35.0,
            refrigerant_sat_temp=38.0  # 3°C above outlet
        )
        
        assert approach == pytest.approx(3.0, rel=0.01)
    
    def test_clean_condenser_approach(self):
        """Test clean condenser (low approach)."""
        approach = self.calc.calculate_approach_temperature(
            cdw_outlet_temp=35.0,
            refrigerant_sat_temp=36.5  # Only 1.5°C above
        )
        
        assert approach == pytest.approx(1.5, rel=0.01)
        assert approach < 2.0  # Excellent
    
    def test_fouled_condenser_approach(self):
        """Test fouled condenser (high approach)."""
        approach = self.calc.calculate_approach_temperature(
            cdw_outlet_temp=35.0,
            refrigerant_sat_temp=42.0  # 7°C above - severe fouling
        )
        
        assert approach == pytest.approx(7.0, rel=0.01)
        assert approach > 5.0  # Critical
    
    def test_default_approximation(self):
        """Test default approximation when no refrigerant temp provided."""
        approach = self.calc.calculate_approach_temperature(
            cdw_outlet_temp=35.0,
            refrigerant_sat_temp=None  # Use approximation
        )
        
        # Default offset is 3.0°C
        assert approach == pytest.approx(3.0, rel=0.01)
    
    def test_approach_cannot_be_negative(self):
        """Test that approach is clamped to zero minimum."""
        approach = self.calc.calculate_approach_temperature(
            cdw_outlet_temp=40.0,
            refrigerant_sat_temp=38.0  # Below outlet (impossible)
        )
        
        # Should be clamped to 0, not negative
        assert approach == 0.0


class TestPhaseImbalance:
    """Tests for phase imbalance calculation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.calc = PhysicsCalculator()
    
    def test_perfect_balance(self):
        """Test perfectly balanced three-phase."""
        imbalance = self.calc.calculate_phase_imbalance(
            current_r=200.0,
            current_y=200.0,
            current_b=200.0
        )
        
        assert imbalance == 0.0
    
    def test_slight_imbalance(self):
        """Test slight natural imbalance."""
        imbalance = self.calc.calculate_phase_imbalance(
            current_r=200.0,
            current_y=202.0,
            current_b=198.0
        )
        
        # Should be around 1%
        assert imbalance == pytest.approx(1.0, rel=0.2)
        assert imbalance < 2.0  # Still good
    
    def test_significant_imbalance(self):
        """Test significant imbalance."""
        imbalance = self.calc.calculate_phase_imbalance(
            current_r=200.0,
            current_y=180.0,
            current_b=220.0
        )
        
        # Should be around 10%
        assert imbalance > 5.0  # Critical level
    
    def test_zero_current_returns_zero(self):
        """Test zero current returns zero imbalance."""
        imbalance = self.calc.calculate_phase_imbalance(
            current_r=0.0,
            current_y=0.0,
            current_b=0.0
        )
        
        assert imbalance == 0.0
    
    def test_very_low_current(self):
        """Test very low current (motor starting or stopped)."""
        imbalance = self.calc.calculate_phase_imbalance(
            current_r=0.05,
            current_y=0.05,
            current_b=0.05
        )
        
        # Should return 0 for very low current
        assert imbalance == 0.0


class TestCOP:
    """Tests for Coefficient of Performance calculation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.calc = PhysicsCalculator()
    
    def test_good_cop(self):
        """Test good COP for water-cooled chiller."""
        cop = self.calc.calculate_cop(
            delta_t=5.56,
            power_kw=280,
            chw_flow_gpm=1000
        )
        
        # Good water-cooled chiller: COP 5.5-7.0
        assert cop > 5.0
        assert cop < 8.0
    
    def test_cop_inverse_of_kw_per_ton(self):
        """Test COP relationship to kW/ton."""
        delta_t = 5.56
        power_kw = 280
        chw_flow_gpm = 1000
        
        cop = self.calc.calculate_cop(delta_t, power_kw, chw_flow_gpm)
        kw_per_ton = self.calc.calculate_kw_per_ton(power_kw, delta_t, chw_flow_gpm)
        
        # COP = 3.517 / kW_per_ton
        expected_cop = 3.517 / kw_per_ton
        assert cop == pytest.approx(expected_cop, rel=0.01)
    
    def test_zero_power_returns_zero_cop(self):
        """Test that zero power returns zero COP."""
        cop = self.calc.calculate_cop(
            delta_t=5.56,
            power_kw=0,
            chw_flow_gpm=1000
        )
        
        assert cop == 0.0


class TestCalculateAllMetrics:
    """Tests for the combined metrics calculation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.calc = PhysicsCalculator()
    
    def test_all_metrics_returned(self):
        """Test that all metrics are calculated and returned."""
        metrics = self.calc.calculate_all_metrics(
            chw_supply_temp=6.7,
            chw_return_temp=12.2,
            cdw_inlet_temp=29.4,
            cdw_outlet_temp=35.0,
            power_kw=280,
            current_r=200,
            current_y=200,
            current_b=200,
            chw_flow_gpm=1000
        )
        
        assert "delta_t" in metrics
        assert "cooling_tons" in metrics
        assert "kw_per_ton" in metrics
        assert "approach_temp" in metrics
        assert "phase_imbalance" in metrics
        assert "cop" in metrics
    
    def test_metrics_are_rounded(self):
        """Test that metrics are properly rounded."""
        metrics = self.calc.calculate_all_metrics(
            chw_supply_temp=6.7,
            chw_return_temp=12.2,
            cdw_inlet_temp=29.4,
            cdw_outlet_temp=35.0,
            power_kw=280,
            current_r=200,
            current_y=202,
            current_b=198
        )
        
        # Check reasonable decimal places
        assert len(str(metrics["delta_t"]).split(".")[-1]) <= 3
        assert len(str(metrics["kw_per_ton"]).split(".")[-1]) <= 3
    
    def test_metrics_values_are_reasonable(self):
        """Test that calculated metrics are in reasonable ranges."""
        metrics = self.calc.calculate_all_metrics(
            chw_supply_temp=6.7,
            chw_return_temp=12.2,
            cdw_inlet_temp=29.4,
            cdw_outlet_temp=35.0,
            power_kw=280,
            current_r=200,
            current_y=200,
            current_b=200,
            chw_flow_gpm=1000
        )
        
        assert 4.0 < metrics["delta_t"] < 7.0
        assert 400 < metrics["cooling_tons"] < 600
        assert 0.4 < metrics["kw_per_ton"] < 0.8
        assert 2.0 < metrics["approach_temp"] < 5.0
        assert metrics["phase_imbalance"] < 2.0
        assert 4.0 < metrics["cop"] < 8.0


class TestQuickPhysicsCheck:
    """Tests for the convenience function."""
    
    def test_quick_check_with_dict(self):
        """Test quick physics check with dictionary input."""
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
        
        assert "delta_t" in metrics
        assert "kw_per_ton" in metrics
        assert metrics["delta_t"] > 0
    
    def test_quick_check_with_missing_values(self):
        """Test quick check handles missing values."""
        data = {
            "chw_supply_temp": 6.7,
            "chw_return_temp": 12.2,
            "power_kw": 280
            # Missing other values - should use defaults
        }
        
        metrics = quick_physics_check(data)
        
        assert "delta_t" in metrics
        assert metrics["delta_t"] > 0
    
    def test_quick_check_with_empty_dict(self):
        """Test quick check with empty dictionary."""
        metrics = quick_physics_check({})
        
        # Should return metrics with zero/default values
        assert "delta_t" in metrics
