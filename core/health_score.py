"""
Health Score Engine for Chiller Systems

This module calculates a composite health score (0-100) based on
multiple indicators, each weighted by their diagnostic importance.

Philosophy:
- Score 100 = Perfect health
- Score 0 = Complete failure
- Leading indicators weighted more heavily (catch problems early)
- Fully explainable (know which metrics contributed to score)

Key Features:
- Weighted multi-metric scoring
- Configurable thresholds
- Actionable recommendations
- Explainable breakdowns for each metric
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum


class HealthCategory(Enum):
    """Health categories for easy interpretation."""
    EXCELLENT = "excellent"   # 90-100: No action needed
    GOOD = "good"            # 75-89: Normal operation
    FAIR = "fair"            # 55-74: Monitor closely
    POOR = "poor"            # 30-54: Action recommended
    CRITICAL = "critical"    # 0-29: Immediate action required


@dataclass
class MetricScore:
    """
    Score breakdown for an individual metric.
    
    This provides full transparency into how each metric
    contributed to the overall health score.
    """
    metric_name: str
    raw_value: float           # Actual sensor/calculated value
    normalized_score: float    # 0-100 score for this metric
    weighted_contribution: float  # Points contributed to overall
    weight: float              # Weight used (0-1)
    status: str                # excellent/good/fair/poor/critical
    message: str               # Human-readable explanation
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "metric_name": self.metric_name,
            "raw_value": round(self.raw_value, 3),
            "normalized_score": round(self.normalized_score, 1),
            "weighted_contribution": round(self.weighted_contribution, 2),
            "weight": round(self.weight, 2),
            "status": self.status,
            "message": self.message,
        }


@dataclass
class HealthScore:
    """
    Complete health assessment result.
    
    Contains the overall score, category, detailed breakdown,
    and actionable recommendations.
    """
    overall_score: float                          # 0-100
    category: HealthCategory                       # Classification
    breakdown: List[MetricScore]                   # Per-metric details
    primary_concern: Optional[str] = None          # Worst metric
    recommendations: List[str] = field(default_factory=list)  # Actions
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "overall_score": round(self.overall_score, 1),
            "category": self.category.value,
            "primary_concern": self.primary_concern,
            "recommendations": self.recommendations,
            "breakdown": [m.to_dict() for m in self.breakdown],
        }


class HealthScoreEngine:
    """
    Engine for calculating health scores from chiller metrics.
    
    Weights are assigned based on:
    1. Leading vs lagging indicator nature
    2. Criticality of the failure mode
    3. Ease of remediation
    4. Cost impact of failure
    
    Default Weights:
    - Vibration (0.35): Leading indicator, catches mechanical issues early
    - Approach (0.25): Performance indicator, shows heat transfer health
    - Phase Imbalance (0.20): Electrical health, immediate damage risk
    - kW/Ton (0.15): Efficiency trend, economic impact
    - Delta-T (0.05): System balance, supports other diagnostics
    
    Example:
        engine = HealthScoreEngine()
        result = engine.calculate({
            "vibration_rms": 2.5,
            "approach_temp": 2.8,
            "phase_imbalance": 1.2,
            "kw_per_ton": 0.65,
            "delta_t": 5.5
        })
        print(f"Health: {result.overall_score}/100 ({result.category.value})")
    """
    
    def __init__(self, weights: Optional[Dict[str, float]] = None):
        """
        Initialize the health score engine.
        
        Args:
            weights: Custom weights for each metric (must sum to 1.0).
                    If None, uses research-based defaults.
        """
        self.weights = weights or {
            "vibration_rms": 0.35,
            "approach_temp": 0.25,
            "phase_imbalance": 0.20,
            "kw_per_ton": 0.15,
            "delta_t": 0.05,
        }
        
        # Thresholds for each metric
        # Format: excellent/good/fair/poor boundaries
        # Values beyond 'poor' are critical
        self.thresholds = {
            "vibration_rms": {
                "excellent": 2.0,    # mm/s - like new
                "good": 4.0,         # mm/s - acceptable
                "fair": 7.0,         # mm/s - monitor
                "poor": 11.0,        # mm/s - action needed
                "unit": "mm/s",
                "direction": "lower_better",
                "description": "Mechanical vibration level"
            },
            "approach_temp": {
                "excellent": 2.0,    # °C - clean condenser
                "good": 3.0,         # °C - normal
                "fair": 4.5,         # °C - early fouling
                "poor": 6.0,         # °C - significant fouling
                "unit": "°C",
                "direction": "lower_better",
                "description": "Condenser heat transfer efficiency"
            },
            "phase_imbalance": {
                "excellent": 1.0,    # % - well balanced
                "good": 2.0,         # % - acceptable
                "fair": 3.5,         # % - investigate
                "poor": 5.0,         # % - motor at risk
                "unit": "%",
                "direction": "lower_better",
                "description": "Electrical supply balance"
            },
            "kw_per_ton": {
                "excellent": 0.55,   # kW/ton - high efficiency
                "good": 0.70,        # kW/ton - good efficiency
                "fair": 0.85,        # kW/ton - average
                "poor": 1.0,         # kW/ton - poor
                "unit": "kW/ton",
                "direction": "lower_better",
                "description": "Energy efficiency"
            },
            "delta_t": {
                # Delta-T has an optimal range, not just lower/higher is better
                "target": 5.5,       # °C - design delta-T
                "excellent_band": 1.0,  # ± from target
                "good_band": 2.0,
                "fair_band": 3.5,
                "poor_band": 5.0,
                "unit": "°C",
                "direction": "target_range",
                "description": "Chilled water temperature differential"
            },
        }
        
        # Recommendations database
        self._init_recommendations()
    
    def _init_recommendations(self):
        """Initialize the recommendations database."""
        self.recommendations_db = {
            "vibration_rms": {
                "fair": [
                    "Schedule vibration analysis within 2 weeks",
                    "Check bearing lubrication levels",
                    "Inspect visible components for looseness",
                ],
                "poor": [
                    "Schedule vibration analysis within 1 week",
                    "Check bearing condition - listen for unusual sounds",
                    "Verify coupling alignment",
                    "Review maintenance history for recent changes",
                ],
                "critical": [
                    "⚠️ URGENT: Reduce load immediately",
                    "Schedule emergency inspection within 24-48 hours",
                    "Prepare for potential bearing replacement",
                    "Check for loose mounting bolts or foundation issues",
                    "Document vibration readings for trending",
                ],
            },
            "approach_temp": {
                "fair": [
                    "Schedule condenser inspection within 1 month",
                    "Check condenser water flow rate",
                    "Verify cooling tower performance",
                ],
                "poor": [
                    "Schedule condenser tube cleaning within 2 weeks",
                    "Check for scaling or biological growth",
                    "Verify water treatment program effectiveness",
                    "Check refrigerant charge",
                ],
                "critical": [
                    "⚠️ URGENT: Condenser severely fouled",
                    "Schedule immediate tube cleaning",
                    "Check for non-condensables (air) in system",
                    "Verify refrigerant charge and purity",
                    "Estimated energy waste: 15-25%",
                ],
            },
            "phase_imbalance": {
                "fair": [
                    "Check utility power quality",
                    "Inspect main electrical connections",
                    "Verify power factor correction equipment",
                ],
                "poor": [
                    "Schedule electrical inspection within 1 week",
                    "Check for loose terminal connections",
                    "Verify all three phases at motor terminals",
                    "Check for single-phasing protection",
                ],
                "critical": [
                    "⚠️ URGENT: Motor damage risk - reduce load",
                    "Immediate electrical inspection required",
                    "Check for single-phasing condition",
                    "Verify utility power quality",
                    "Motor life may be reduced by 50%+ at this imbalance",
                ],
            },
            "kw_per_ton": {
                "fair": [
                    "Compare to baseline/design efficiency",
                    "Check operating conditions vs design",
                    "Review control sequences",
                ],
                "poor": [
                    "Full efficiency audit recommended",
                    "Check refrigerant charge level",
                    "Verify all heat exchangers are clean",
                    "Review control system operation",
                ],
                "critical": [
                    "⚠️ Major efficiency degradation",
                    "Full diagnostic inspection required",
                    "Check compressor condition",
                    "Verify refrigerant charge and oil level",
                    "Estimated excess energy cost: significant",
                ],
            },
            "delta_t": {
                "fair": [
                    "Check chilled water flow rate",
                    "Verify control valve operation",
                    "Review building load distribution",
                ],
                "poor": [
                    "Check pump operation and speed",
                    "Verify no air in chilled water system",
                    "Check for bypass or three-way valve issues",
                    "Review chilled water reset schedule",
                ],
                "critical": [
                    "⚠️ System balance issue",
                    "Check all pumps for proper operation",
                    "Verify no major leaks or bypasses",
                    "Review entire chilled water distribution",
                ],
            },
        }
    
    def calculate(self, metrics: Dict[str, float]) -> HealthScore:
        """
        Calculate the overall health score from metrics.
        
        Args:
            metrics: Dictionary with metric names and values
            
        Returns:
            HealthScore object with complete breakdown
        """
        breakdown: List[MetricScore] = []
        weighted_sum = 0.0
        total_weight = 0.0
        
        # Score each metric
        for metric_name, weight in self.weights.items():
            value = metrics.get(metric_name)
            
            if value is None:
                continue  # Skip missing metrics
            
            # Calculate score for this metric
            score, status, message = self._score_metric(metric_name, value)
            weighted_contribution = score * weight
            
            breakdown.append(MetricScore(
                metric_name=metric_name,
                raw_value=value,
                normalized_score=score,
                weighted_contribution=weighted_contribution,
                weight=weight,
                status=status,
                message=message,
            ))
            
            weighted_sum += weighted_contribution
            total_weight += weight
        
        # Calculate overall score
        if total_weight > 0:
            overall_score = weighted_sum / total_weight
        else:
            overall_score = 50.0  # No data - neutral score
        
        # Determine category
        category = self._get_category(overall_score)
        
        # Find primary concern and get recommendations
        primary_concern = None
        recommendations: List[str] = []
        
        if breakdown:
            # Sort by score (lowest first = worst)
            breakdown_sorted = sorted(breakdown, key=lambda x: x.normalized_score)
            worst = breakdown_sorted[0]
            
            if worst.normalized_score < 70:
                primary_concern = worst.metric_name
                recommendations = self._get_recommendations(
                    worst.metric_name, 
                    worst.status
                )
        
        return HealthScore(
            overall_score=overall_score,
            category=category,
            breakdown=breakdown_sorted if breakdown else [],
            primary_concern=primary_concern,
            recommendations=recommendations,
        )
    
    def _score_metric(
        self, 
        metric_name: str, 
        value: float
    ) -> Tuple[float, str, str]:
        """
        Calculate normalized score (0-100) for a single metric.
        
        Args:
            metric_name: Name of the metric
            value: Actual value
            
        Returns:
            Tuple of (score, status, message)
        """
        thresholds = self.thresholds.get(metric_name)
        
        if not thresholds:
            return 50.0, "unknown", f"No thresholds defined for {metric_name}"
        
        direction = thresholds.get("direction", "lower_better")
        unit = thresholds.get("unit", "")
        description = thresholds.get("description", metric_name)
        
        if direction == "lower_better":
            return self._score_lower_better(value, thresholds, unit, description)
        elif direction == "target_range":
            return self._score_target_range(value, thresholds, unit, description)
        else:
            return 50.0, "unknown", "Unknown scoring direction"
    
    def _score_lower_better(
        self,
        value: float,
        thresholds: Dict,
        unit: str,
        description: str
    ) -> Tuple[float, str, str]:
        """Score metric where lower values are better."""
        excellent = thresholds["excellent"]
        good = thresholds["good"]
        fair = thresholds["fair"]
        poor = thresholds["poor"]
        
        if value <= excellent:
            # Excellent range: 90-100
            score = 95.0 + 5.0 * (1.0 - value / excellent) if excellent > 0 else 100.0
            status = "excellent"
            message = f"✅ Excellent {description}: {value:.2f} {unit}"
            
        elif value <= good:
            # Good range: 75-90
            progress = (value - excellent) / (good - excellent)
            score = 90.0 - 15.0 * progress
            status = "good"
            message = f"✅ Good {description}: {value:.2f} {unit}"
            
        elif value <= fair:
            # Fair range: 55-75
            progress = (value - good) / (fair - good)
            score = 75.0 - 20.0 * progress
            status = "fair"
            message = f"⚠️ Fair {description}: {value:.2f} {unit} - Monitor closely"
            
        elif value <= poor:
            # Poor range: 30-55
            progress = (value - fair) / (poor - fair)
            score = 55.0 - 25.0 * progress
            status = "poor"
            message = f"🔶 Poor {description}: {value:.2f} {unit} - Action recommended"
            
        else:
            # Critical: 0-30
            overage = (value - poor) / poor if poor > 0 else 1.0
            score = max(0.0, 30.0 - 30.0 * min(overage, 1.0))
            status = "critical"
            message = f"🔴 Critical {description}: {value:.2f} {unit} - Immediate action required"
        
        return min(100.0, max(0.0, score)), status, message
    
    def _score_target_range(
        self,
        value: float,
        thresholds: Dict,
        unit: str,
        description: str
    ) -> Tuple[float, str, str]:
        """Score metric where a target value/range is optimal."""
        target = thresholds.get("target", 5.5)
        excellent_band = thresholds.get("excellent_band", 1.0)
        good_band = thresholds.get("good_band", 2.0)
        fair_band = thresholds.get("fair_band", 3.5)
        poor_band = thresholds.get("poor_band", 5.0)
        
        deviation = abs(value - target)
        
        if deviation <= excellent_band:
            score = 95.0 + 5.0 * (1.0 - deviation / excellent_band)
            status = "excellent"
            message = f"✅ Excellent {description}: {value:.1f} {unit} (target: {target})"
            
        elif deviation <= good_band:
            progress = (deviation - excellent_band) / (good_band - excellent_band)
            score = 90.0 - 15.0 * progress
            status = "good"
            message = f"✅ Good {description}: {value:.1f} {unit}"
            
        elif deviation <= fair_band:
            progress = (deviation - good_band) / (fair_band - good_band)
            score = 75.0 - 20.0 * progress
            status = "fair"
            message = f"⚠️ Fair {description}: {value:.1f} {unit} - Outside optimal range"
            
        elif deviation <= poor_band:
            progress = (deviation - fair_band) / (poor_band - fair_band)
            score = 55.0 - 25.0 * progress
            status = "poor"
            message = f"🔶 Poor {description}: {value:.1f} {unit} - Investigate"
            
        else:
            overage = (deviation - poor_band) / poor_band
            score = max(0.0, 30.0 - 30.0 * min(overage, 1.0))
            status = "critical"
            message = f"🔴 Critical {description}: {value:.1f} {unit} - System issue"
        
        return min(100.0, max(0.0, score)), status, message
    
    def _get_category(self, score: float) -> HealthCategory:
        """Convert numeric score to category."""
        if score >= 90:
            return HealthCategory.EXCELLENT
        elif score >= 75:
            return HealthCategory.GOOD
        elif score >= 55:
            return HealthCategory.FAIR
        elif score >= 30:
            return HealthCategory.POOR
        else:
            return HealthCategory.CRITICAL
    
    def _get_recommendations(
        self, 
        metric_name: str, 
        status: str
    ) -> List[str]:
        """Get actionable recommendations for a metric in a given state."""
        metric_recs = self.recommendations_db.get(metric_name, {})
        return metric_recs.get(status, ["Monitor and investigate as needed"])


def calculate_health_score(
    metrics: Dict[str, float],
    weights: Optional[Dict[str, float]] = None
) -> HealthScore:
    """
    Convenience function to calculate health score.
    
    Args:
        metrics: Dictionary of metric values
        weights: Optional custom weights
        
    Returns:
        HealthScore object
        
    Example:
        result = calculate_health_score({
            "vibration_rms": 3.5,
            "approach_temp": 2.8,
            "phase_imbalance": 1.5,
            "kw_per_ton": 0.68,
            "delta_t": 5.2
        })
        print(f"Score: {result.overall_score}")
        print(f"Status: {result.category.value}")
    """
    engine = HealthScoreEngine(weights)
    return engine.calculate(metrics)
