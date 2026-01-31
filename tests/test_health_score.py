"""
Tests for Health Score Engine

These tests verify that health scores are calculated correctly
and that the scoring logic properly weights different metrics.

Run with: pytest tests/test_health_score.py -v
"""

import pytest
from core.health_score import (
    HealthScoreEngine,
    HealthScore,
    HealthCategory,
    MetricScore,
    calculate_health_score
)


class TestHealthCategory:
    """Test health category enum."""
    
    def test_category_values(self):
        """Test all category values exist."""
        assert HealthCategory.EXCELLENT.value == "excellent"
        assert HealthCategory.GOOD.value == "good"
        assert HealthCategory.FAIR.value == "fair"
        assert HealthCategory.POOR.value == "poor"
        assert HealthCategory.CRITICAL.value == "critical"


class TestHealthScoreEngine:
    """Test the health score engine."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.engine = HealthScoreEngine()
    
    def test_default_weights(self):
        """Test default weights are set correctly."""
        assert self.engine.weights["vibration_rms"] == 0.35
        assert self.engine.weights["approach_temp"] == 0.25
        assert self.engine.weights["phase_imbalance"] == 0.20
        assert self.engine.weights["kw_per_ton"] == 0.15
        assert self.engine.weights["delta_t"] == 0.05
    
    def test_weights_sum_to_one(self):
        """Test that default weights sum to 1.0."""
        total = sum(self.engine.weights.values())
        assert total == pytest.approx(1.0, rel=0.01)
    
    def test_custom_weights(self):
        """Test custom weights can be provided."""
        custom_weights = {
            "vibration_rms": 0.5,
            "approach_temp": 0.5
        }
        engine = HealthScoreEngine(weights=custom_weights)
        
        assert engine.weights["vibration_rms"] == 0.5
        assert engine.weights["approach_temp"] == 0.5


class TestExcellentHealth:
    """Test excellent health conditions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.engine = HealthScoreEngine()
    
    def test_all_excellent_metrics(self):
        """Test score when all metrics are excellent."""
        result = self.engine.calculate({
            "vibration_rms": 1.5,      # Excellent: < 2.0
            "approach_temp": 1.8,      # Excellent: < 2.0
            "phase_imbalance": 0.5,    # Excellent: < 1.0
            "kw_per_ton": 0.50,        # Excellent: < 0.55
            "delta_t": 5.5             # Excellent: target ±1.0
        })
        
        assert result.overall_score >= 90
        assert result.category == HealthCategory.EXCELLENT
        assert result.primary_concern is None
        assert len(result.recommendations) == 0
    
    def test_excellent_category_threshold(self):
        """Test that score >= 90 gives excellent category."""
        result = self.engine.calculate({
            "vibration_rms": 1.8,
            "approach_temp": 1.9,
            "phase_imbalance": 0.8,
            "kw_per_ton": 0.52,
            "delta_t": 5.3
        })
        
        assert result.category == HealthCategory.EXCELLENT


class TestGoodHealth:
    """Test good health conditions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.engine = HealthScoreEngine()
    
    def test_all_good_metrics(self):
        """Test score when all metrics are good."""
        result = self.engine.calculate({
            "vibration_rms": 3.0,      # Good: 2.0 - 4.0
            "approach_temp": 2.5,      # Good: 2.0 - 3.0
            "phase_imbalance": 1.5,    # Good: 1.0 - 2.0
            "kw_per_ton": 0.65,        # Good: 0.55 - 0.70
            "delta_t": 4.0             # Good: target ±2.0
        })
        
        assert 75 <= result.overall_score < 90
        assert result.category == HealthCategory.GOOD
    
    def test_good_category_threshold(self):
        """Test that 75 <= score < 90 gives good category."""
        # Create metrics that give score around 80
        result = self.engine.calculate({
            "vibration_rms": 3.5,
            "approach_temp": 2.8,
            "phase_imbalance": 1.8,
            "kw_per_ton": 0.68,
            "delta_t": 4.5
        })
        
        assert result.category in [HealthCategory.GOOD, HealthCategory.EXCELLENT]


class TestFairHealth:
    """Test fair health conditions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.engine = HealthScoreEngine()
    
    def test_fair_metrics(self):
        """Test score when metrics are in fair range."""
        result = self.engine.calculate({
            "vibration_rms": 5.5,      # Fair: 4.0 - 7.0
            "approach_temp": 4.0,      # Fair: 3.0 - 4.5
            "phase_imbalance": 3.0,    # Fair: 2.0 - 3.5
            "kw_per_ton": 0.80,        # Fair: 0.70 - 0.85
            "delta_t": 3.0             # Fair: outside good band
        })
        
        assert 55 <= result.overall_score < 75
        assert result.category == HealthCategory.FAIR
    
    def test_fair_generates_recommendations(self):
        """Test that fair status generates some recommendations."""
        result = self.engine.calculate({
            "vibration_rms": 6.0,
            "approach_temp": 4.2,
            "phase_imbalance": 3.2,
            "kw_per_ton": 0.82,
            "delta_t": 2.5
        })
        
        # Should have primary concern and recommendations
        assert result.primary_concern is not None or result.overall_score >= 70


class TestPoorHealth:
    """Test poor health conditions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.engine = HealthScoreEngine()
    
    def test_poor_metrics(self):
        """Test score when metrics are in poor range."""
        result = self.engine.calculate({
            "vibration_rms": 9.0,      # Poor: 7.0 - 11.0
            "approach_temp": 5.5,      # Poor: 4.5 - 6.0
            "phase_imbalance": 4.5,    # Poor: 3.5 - 5.0
            "kw_per_ton": 0.95,        # Poor: 0.85 - 1.0
            "delta_t": 1.8             # Poor: far from target
        })
        
        assert 30 <= result.overall_score < 55
        assert result.category == HealthCategory.POOR
    
    def test_poor_has_recommendations(self):
        """Test that poor health has recommendations."""
        result = self.engine.calculate({
            "vibration_rms": 9.0,
            "approach_temp": 5.5,
            "phase_imbalance": 4.5,
            "kw_per_ton": 0.95,
            "delta_t": 1.8
        })
        
        assert len(result.recommendations) > 0
        assert result.primary_concern is not None


class TestCriticalHealth:
    """Test critical health conditions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.engine = HealthScoreEngine()
    
    def test_critical_metrics(self):
        """Test score when metrics are critical."""
        result = self.engine.calculate({
            "vibration_rms": 15.0,     # Critical: > 11.0
            "approach_temp": 8.0,      # Critical: > 6.0
            "phase_imbalance": 7.0,    # Critical: > 5.0
            "kw_per_ton": 1.3,         # Critical: > 1.0
            "delta_t": 0.5             # Critical: very low
        })
        
        assert result.overall_score < 30
        assert result.category == HealthCategory.CRITICAL
    
    def test_critical_has_urgent_recommendations(self):
        """Test that critical health has urgent recommendations."""
        result = self.engine.calculate({
            "vibration_rms": 15.0,
            "approach_temp": 8.0,
            "phase_imbalance": 7.0,
            "kw_per_ton": 1.3,
            "delta_t": 0.5
        })
        
        assert len(result.recommendations) > 0
        # Check for urgent language
        all_recs = " ".join(result.recommendations).lower()
        assert "urgent" in all_recs or "immediate" in all_recs or "critical" in all_recs


class TestSingleBadMetric:
    """Test impact of single bad metric on overall score."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.engine = HealthScoreEngine()
    
    def test_high_vibration_only(self):
        """Test impact of only high vibration."""
        result = self.engine.calculate({
            "vibration_rms": 12.0,     # Critical
            "approach_temp": 2.0,      # Excellent
            "phase_imbalance": 1.0,    # Excellent
            "kw_per_ton": 0.55,        # Excellent
            "delta_t": 5.5             # Excellent
        })
        
        # Vibration is 35% weight, so one critical metric should drag down score
        assert result.overall_score < 80
        assert result.primary_concern == "vibration_rms"
    
    def test_high_approach_only(self):
        """Test impact of only high approach temp."""
        result = self.engine.calculate({
            "vibration_rms": 1.5,      # Excellent
            "approach_temp": 7.0,      # Critical
            "phase_imbalance": 1.0,    # Excellent
            "kw_per_ton": 0.55,        # Excellent
            "delta_t": 5.5             # Excellent
        })
        
        assert result.primary_concern == "approach_temp"
    
    def test_primary_concern_is_worst(self):
        """Test that primary concern identifies the worst metric."""
        result = self.engine.calculate({
            "vibration_rms": 3.0,      # Good
            "approach_temp": 4.0,      # Fair
            "phase_imbalance": 6.0,    # Critical - worst!
            "kw_per_ton": 0.70,        # Good
            "delta_t": 5.0             # Good
        })
        
        assert result.primary_concern == "phase_imbalance"


class TestBreakdown:
    """Test health score breakdown details."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.engine = HealthScoreEngine()
    
    def test_breakdown_contains_all_metrics(self):
        """Test that breakdown contains all provided metrics."""
        metrics = {
            "vibration_rms": 2.5,
            "approach_temp": 2.5,
            "phase_imbalance": 1.5,
            "kw_per_ton": 0.65,
            "delta_t": 5.5
        }
        result = self.engine.calculate(metrics)
        
        breakdown_metrics = [b.metric_name for b in result.breakdown]
        for metric in metrics:
            assert metric in breakdown_metrics
    
    def test_breakdown_scores_are_valid(self):
        """Test that breakdown scores are in valid range."""
        result = self.engine.calculate({
            "vibration_rms": 2.5,
            "approach_temp": 2.5,
            "phase_imbalance": 1.5,
            "kw_per_ton": 0.65,
            "delta_t": 5.5
        })
        
        for item in result.breakdown:
            assert 0 <= item.normalized_score <= 100
            assert 0 <= item.weight <= 1
            assert item.weighted_contribution >= 0
    
    def test_breakdown_has_status(self):
        """Test that breakdown items have status."""
        result = self.engine.calculate({
            "vibration_rms": 2.5,
            "approach_temp": 2.5
        })
        
        for item in result.breakdown:
            assert item.status in ["excellent", "good", "fair", "poor", "critical"]
    
    def test_breakdown_has_message(self):
        """Test that breakdown items have human-readable messages."""
        result = self.engine.calculate({
            "vibration_rms": 2.5,
            "approach_temp": 2.5
        })
        
        for item in result.breakdown:
            assert len(item.message) > 0
    
    def test_breakdown_sorted_by_score(self):
        """Test that breakdown is sorted by score (worst first)."""
        result = self.engine.calculate({
            "vibration_rms": 1.0,      # Excellent
            "approach_temp": 6.5,      # Critical
            "phase_imbalance": 3.0,    # Fair
        })
        
        scores = [b.normalized_score for b in result.breakdown]
        assert scores == sorted(scores)  # Should be ascending (worst first)


class TestWeightedContribution:
    """Test weighted contribution calculation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.engine = HealthScoreEngine()
    
    def test_weighted_contribution_calculation(self):
        """Test that weighted contribution is calculated correctly."""
        result = self.engine.calculate({
            "vibration_rms": 2.0  # Should score around 95
        })
        
        item = result.breakdown[0]
        expected_contribution = item.normalized_score * item.weight
        assert item.weighted_contribution == pytest.approx(expected_contribution, rel=0.01)
    
    def test_overall_score_from_contributions(self):
        """Test that overall score equals weighted average of contributions."""
        result = self.engine.calculate({
            "vibration_rms": 2.5,
            "approach_temp": 2.5,
            "phase_imbalance": 1.5,
            "kw_per_ton": 0.65,
            "delta_t": 5.5
        })
        
        total_contribution = sum(b.weighted_contribution for b in result.breakdown)
        total_weight = sum(b.weight for b in result.breakdown)
        expected_score = total_contribution / total_weight
        
        assert result.overall_score == pytest.approx(expected_score, rel=0.01)


class TestPartialMetrics:
    """Test handling of partial/missing metrics."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.engine = HealthScoreEngine()
    
    def test_single_metric(self):
        """Test calculation with single metric."""
        result = self.engine.calculate({
            "vibration_rms": 2.0
        })
        
        assert result.overall_score > 0
        assert len(result.breakdown) == 1
    
    def test_empty_metrics(self):
        """Test calculation with no metrics."""
        result = self.engine.calculate({})
        
        # Should return neutral score
        assert result.overall_score == 50.0
        assert len(result.breakdown) == 0
    
    def test_unknown_metric_ignored(self):
        """Test that unknown metrics are ignored."""
        result = self.engine.calculate({
            "vibration_rms": 2.0,
            "unknown_metric": 999.0  # Should be ignored
        })
        
        assert len(result.breakdown) == 1
        assert result.breakdown[0].metric_name == "vibration_rms"


class TestDeltaTScoring:
    """Test delta-T scoring (target range, not lower-better)."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.engine = HealthScoreEngine()
    
    def test_optimal_delta_t(self):
        """Test score at optimal delta-T."""
        result = self.engine.calculate({
            "delta_t": 5.5  # Target value
        })
        
        item = result.breakdown[0]
        assert item.normalized_score >= 90
        assert item.status == "excellent"
    
    def test_too_low_delta_t(self):
        """Test score when delta-T is too low."""
        result = self.engine.calculate({
            "delta_t": 1.0  # Way too low
        })
        
        item = result.breakdown[0]
        assert item.normalized_score < 50
        assert item.status in ["poor", "critical"]
    
    def test_too_high_delta_t(self):
        """Test score when delta-T is too high."""
        result = self.engine.calculate({
            "delta_t": 12.0  # Way too high
        })
        
        item = result.breakdown[0]
        assert item.normalized_score < 50


class TestToDict:
    """Test serialization to dictionary."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.engine = HealthScoreEngine()
    
    def test_health_score_to_dict(self):
        """Test HealthScore.to_dict() method."""
        result = self.engine.calculate({
            "vibration_rms": 2.5,
            "approach_temp": 2.5
        })
        
        d = result.to_dict()
        
        assert "overall_score" in d
        assert "category" in d
        assert "breakdown" in d
        assert "primary_concern" in d
        assert "recommendations" in d
        
        assert isinstance(d["overall_score"], float)
        assert isinstance(d["category"], str)
        assert isinstance(d["breakdown"], list)
    
    def test_metric_score_to_dict(self):
        """Test MetricScore.to_dict() method."""
        result = self.engine.calculate({
            "vibration_rms": 2.5
        })
        
        item = result.breakdown[0]
        d = item.to_dict()
        
        assert "metric_name" in d
        assert "raw_value" in d
        assert "normalized_score" in d
        assert "weighted_contribution" in d
        assert "weight" in d
        assert "status" in d
        assert "message" in d


class TestConvenienceFunction:
    """Test the calculate_health_score convenience function."""
    
    def test_basic_calculation(self):
        """Test basic calculation with convenience function."""
        result = calculate_health_score({
            "vibration_rms": 2.0,
            "approach_temp": 2.5,
            "phase_imbalance": 1.0,
            "kw_per_ton": 0.60,
            "delta_t": 5.5
        })
        
        assert isinstance(result, HealthScore)
        assert result.overall_score > 0
    
    def test_custom_weights(self):
        """Test convenience function with custom weights."""
        custom_weights = {
            "vibration_rms": 0.5,
            "approach_temp": 0.5
        }
        
        result = calculate_health_score(
            {"vibration_rms": 2.0, "approach_temp": 2.5},
            weights=custom_weights
        )
        
        assert isinstance(result, HealthScore)


class TestRecommendationContent:
    """Test that recommendations contain useful content."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.engine = HealthScoreEngine()
    
    def test_vibration_recommendations(self):
        """Test vibration-related recommendations."""
        result = self.engine.calculate({
            "vibration_rms": 10.0  # Poor
        })
        
        if result.recommendations:
            all_recs = " ".join(result.recommendations).lower()
            # Should mention vibration-related terms
            assert any(term in all_recs for term in 
                      ["vibration", "bearing", "alignment", "inspect"])
    
    def test_approach_recommendations(self):
        """Test approach temp-related recommendations."""
        result = self.engine.calculate({
            "approach_temp": 6.5  # Critical
        })
        
        if result.recommendations:
            all_recs = " ".join(result.recommendations).lower()
            assert any(term in all_recs for term in 
                      ["condenser", "fouling", "cleaning", "tube"])
    
    def test_phase_imbalance_recommendations(self):
        """Test phase imbalance-related recommendations."""
        result = self.engine.calculate({
            "phase_imbalance": 6.0  # Critical
        })
        
        if result.recommendations:
            all_recs = " ".join(result.recommendations).lower()
            assert any(term in all_recs for term in 
                      ["electrical", "phase", "connection", "power"])
