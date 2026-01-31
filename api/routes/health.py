"""
Health Score Endpoints

This module provides endpoints for querying health scores and
understanding the factors contributing to equipment health.

Key Features:
- Current health score with full breakdown
- Historical health trends
- Explainability (which metrics are driving the score)
- Actionable recommendations
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from api.database import get_db, DatabaseManager
from api.models import (
    HealthScoreResponse,
    HealthCategory,
    MetricBreakdown,
    SensorReading,
)
from core.health_score import HealthScoreEngine, HealthCategory as CoreHealthCategory

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["Health Monitoring"])

# Initialize health engine
health_engine = HealthScoreEngine()


def reading_to_health_metrics(reading: dict) -> dict:
    """
    Extract health-relevant metrics from a sensor reading.
    
    Args:
        reading: Database reading dictionary
        
    Returns:
        Dictionary with metrics for health calculation
    """
    metrics = {}
    
    # Direct sensor values
    if reading.get("vibration_rms") is not None:
        metrics["vibration_rms"] = reading["vibration_rms"]
    
    # Derived metrics (may be pre-calculated and stored)
    if reading.get("approach_temp") is not None:
        metrics["approach_temp"] = reading["approach_temp"]
    if reading.get("phase_imbalance") is not None:
        metrics["phase_imbalance"] = reading["phase_imbalance"]
    if reading.get("kw_per_ton") is not None:
        metrics["kw_per_ton"] = reading["kw_per_ton"]
    if reading.get("delta_t") is not None:
        metrics["delta_t"] = reading["delta_t"]
    
    return metrics


def core_category_to_api(category: CoreHealthCategory) -> HealthCategory:
    """Convert core health category to API model."""
    mapping = {
        CoreHealthCategory.EXCELLENT: HealthCategory.EXCELLENT,
        CoreHealthCategory.GOOD: HealthCategory.GOOD,
        CoreHealthCategory.FAIR: HealthCategory.FAIR,
        CoreHealthCategory.POOR: HealthCategory.POOR,
        CoreHealthCategory.CRITICAL: HealthCategory.CRITICAL,
    }
    return mapping.get(category, HealthCategory.FAIR)


# =========================================
# API Endpoints
# =========================================

@router.get(
    "/{asset_id}",
    response_model=HealthScoreResponse,
    summary="Get current health score",
    description="""
    Get the current health score for an asset based on the latest sensor readings.
    
    The health score (0-100) is calculated from multiple metrics:
    - **Vibration** (35%): Leading indicator for mechanical issues
    - **Approach Temp** (25%): Heat transfer efficiency
    - **Phase Imbalance** (20%): Electrical health
    - **kW/Ton** (15%): Energy efficiency
    - **Delta-T** (5%): System balance
    
    **Categories:**
    - Excellent (90-100): No action needed
    - Good (75-89): Normal operation
    - Fair (55-74): Monitor closely
    - Poor (30-54): Action recommended
    - Critical (0-29): Immediate action required
    
    **Response includes:**
    - Overall score and category
    - Per-metric breakdown with individual scores
    - Primary concern (if any)
    - Actionable recommendations
    """
)
async def get_health_score(
    asset_id: str,
    db: Session = Depends(get_db)
):
    """Get current health score for an asset."""
    with DatabaseManager(db) as db_manager:
        # Get latest reading
        reading = db_manager.get_latest_reading(asset_id)
        
        if not reading:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No data found for asset: {asset_id}"
            )
        
        # Check if health score was pre-calculated
        if reading.get("health_score") is not None and reading.get("health_breakdown"):
            # Use pre-calculated values
            breakdown_data = reading["health_breakdown"]
            
            return HealthScoreResponse(
                asset_id=asset_id,
                timestamp=reading["time"],
                overall_score=reading["health_score"],
                category=HealthCategory(breakdown_data.get("category", "fair")),
                primary_concern=breakdown_data.get("primary_concern"),
                recommendations=breakdown_data.get("recommendations", []),
                breakdown=[
                    MetricBreakdown(**item)
                    for item in breakdown_data.get("breakdown", [])
                ]
            )
        
        # Calculate health score from metrics
        metrics = reading_to_health_metrics(reading)
        
        if not metrics:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Insufficient metrics to calculate health score"
            )
        
        # Calculate health
        health_result = health_engine.calculate(metrics)
        
        return HealthScoreResponse(
            asset_id=asset_id,
            timestamp=reading["time"],
            overall_score=health_result.overall_score,
            category=core_category_to_api(health_result.category),
            primary_concern=health_result.primary_concern,
            recommendations=health_result.recommendations,
            breakdown=[
                MetricBreakdown(
                    metric_name=item.metric_name,
                    raw_value=item.raw_value,
                    normalized_score=item.normalized_score,
                    weighted_contribution=item.weighted_contribution,
                    weight=item.weight,
                    status=item.status,
                    message=item.message
                )
                for item in health_result.breakdown
            ]
        )


@router.get(
    "/{asset_id}/history",
    response_model=List[HealthScoreResponse],
    summary="Get health score history",
    description="""
    Get historical health scores for an asset over a time period.
    
    Useful for:
    - Trending health over time
    - Identifying degradation patterns
    - Correlating with maintenance events
    
    Returns hourly health summaries by default.
    """
)
async def get_health_history(
    asset_id: str,
    hours: int = Query(default=24, ge=1, le=720, description="Hours of history"),
    db: Session = Depends(get_db)
):
    """Get health score history for an asset."""
    with DatabaseManager(db) as db_manager:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        # Try to get hourly aggregates first
        aggregates = db_manager.get_hourly_aggregates(asset_id, start_time, end_time)
        
        if aggregates:
            results = []
            for agg in aggregates:
                # Calculate health from aggregated metrics
                metrics = {}
                if agg.get("avg_vibration_rms") is not None:
                    metrics["vibration_rms"] = agg["avg_vibration_rms"]
                if agg.get("avg_approach_temp") is not None:
                    metrics["approach_temp"] = agg["avg_approach_temp"]
                if agg.get("avg_phase_imbalance") is not None:
                    metrics["phase_imbalance"] = agg["avg_phase_imbalance"]
                if agg.get("avg_kw_per_ton") is not None:
                    metrics["kw_per_ton"] = agg["avg_kw_per_ton"]
                if agg.get("avg_delta_t") is not None:
                    metrics["delta_t"] = agg["avg_delta_t"]
                
                if metrics:
                    health_result = health_engine.calculate(metrics)
                    results.append(HealthScoreResponse(
                        asset_id=asset_id,
                        timestamp=agg["bucket"],
                        overall_score=health_result.overall_score,
                        category=core_category_to_api(health_result.category),
                        primary_concern=health_result.primary_concern,
                        recommendations=[],  # Omit for history
                        breakdown=[]  # Omit for history to reduce payload
                    ))
            
            return results
        
        # Fallback: get raw readings and sample
        readings = db_manager.get_readings_range(asset_id, start_time, end_time, limit=100)
        
        if not readings:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No data found for asset: {asset_id}"
            )
        
        results = []
        for reading in readings:
            if reading.get("health_score") is not None:
                results.append(HealthScoreResponse(
                    asset_id=asset_id,
                    timestamp=reading["time"],
                    overall_score=reading["health_score"],
                    category=HealthCategory.FAIR,  # Simplified for history
                    primary_concern=None,
                    recommendations=[],
                    breakdown=[]
                ))
        
        return results


@router.get(
    "/{asset_id}/summary",
    summary="Get health summary statistics",
    description="""
    Get summary statistics for health over a time period.
    
    Returns:
    - Average, min, max health scores
    - Time in each health category
    - Most common concerns
    """
)
async def get_health_summary(
    asset_id: str,
    days: int = Query(default=7, ge=1, le=90, description="Days of history"),
    db: Session = Depends(get_db)
):
    """Get health summary for an asset."""
    with DatabaseManager(db) as db_manager:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days)
        
        readings = db_manager.get_readings_range(asset_id, start_time, end_time, limit=5000)
        
        if not readings:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No data found for asset: {asset_id}"
            )
        
        # Calculate statistics
        health_scores = [r["health_score"] for r in readings if r.get("health_score") is not None]
        
        if not health_scores:
            return {
                "asset_id": asset_id,
                "period_days": days,
                "message": "No health scores calculated for this period"
            }
        
        # Category counts
        category_counts = {
            "excellent": 0,
            "good": 0,
            "fair": 0,
            "poor": 0,
            "critical": 0
        }
        
        for score in health_scores:
            if score >= 90:
                category_counts["excellent"] += 1
            elif score >= 75:
                category_counts["good"] += 1
            elif score >= 55:
                category_counts["fair"] += 1
            elif score >= 30:
                category_counts["poor"] += 1
            else:
                category_counts["critical"] += 1
        
        total = len(health_scores)
        category_percentages = {
            k: round(v / total * 100, 1) for k, v in category_counts.items()
        }
        
        return {
            "asset_id": asset_id,
            "period_start": start_time.isoformat(),
            "period_end": end_time.isoformat(),
            "period_days": days,
            "reading_count": total,
            "statistics": {
                "average": round(sum(health_scores) / len(health_scores), 1),
                "minimum": round(min(health_scores), 1),
                "maximum": round(max(health_scores), 1),
                "latest": round(health_scores[-1], 1) if health_scores else None
            },
            "category_distribution": category_counts,
            "category_percentages": category_percentages,
            "health_trend": "stable" if max(health_scores) - min(health_scores) < 15 else (
                "improving" if health_scores[-1] > health_scores[0] else "degrading"
            )
        }


@router.get(
    "/{asset_id}/explain",
    summary="Get detailed health explanation",
    description="""
    Get a detailed human-readable explanation of the current health status.
    
    This endpoint is designed for:
    - Dashboards that need to show "why" the health is at a certain level
    - Maintenance technicians who need to understand the situation
    - Reports and documentation
    """
)
async def explain_health(
    asset_id: str,
    db: Session = Depends(get_db)
):
    """Get detailed health explanation."""
    with DatabaseManager(db) as db_manager:
        reading = db_manager.get_latest_reading(asset_id)
        
        if not reading:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No data found for asset: {asset_id}"
            )
        
        metrics = reading_to_health_metrics(reading)
        
        if not metrics:
            return {
                "asset_id": asset_id,
                "explanation": "Insufficient data to generate health explanation",
                "available_metrics": list(reading.keys())
            }
        
        # Calculate health
        health_result = health_engine.calculate(metrics)
        
        # Build explanation
        explanation_parts = []
        
        # Overall status
        if health_result.overall_score >= 90:
            explanation_parts.append(
                f"🟢 **Overall Status: EXCELLENT** (Score: {health_result.overall_score:.1f}/100)\n"
                f"The chiller is operating in excellent condition with all metrics within optimal ranges."
            )
        elif health_result.overall_score >= 75:
            explanation_parts.append(
                f"🟢 **Overall Status: GOOD** (Score: {health_result.overall_score:.1f}/100)\n"
                f"The chiller is operating normally with minor variations from optimal."
            )
        elif health_result.overall_score >= 55:
            explanation_parts.append(
                f"🟡 **Overall Status: FAIR** (Score: {health_result.overall_score:.1f}/100)\n"
                f"The chiller is operational but showing signs that warrant attention."
            )
        elif health_result.overall_score >= 30:
            explanation_parts.append(
                f"🟠 **Overall Status: POOR** (Score: {health_result.overall_score:.1f}/100)\n"
                f"The chiller has significant issues that require action."
            )
        else:
            explanation_parts.append(
                f"🔴 **Overall Status: CRITICAL** (Score: {health_result.overall_score:.1f}/100)\n"
                f"The chiller requires immediate attention to prevent failure or damage."
            )
        
        # Per-metric details
        explanation_parts.append("\n---\n**Metric Analysis:**\n")
        
        for metric in sorted(health_result.breakdown, key=lambda x: x.normalized_score):
            explanation_parts.append(f"- {metric.message}")
        
        # Primary concern
        if health_result.primary_concern:
            explanation_parts.append(
                f"\n---\n**Primary Concern:** {health_result.primary_concern}"
            )
        
        # Recommendations
        if health_result.recommendations:
            explanation_parts.append("\n---\n**Recommended Actions:**")
            for i, rec in enumerate(health_result.recommendations, 1):
                explanation_parts.append(f"{i}. {rec}")
        
        return {
            "asset_id": asset_id,
            "timestamp": reading["time"],
            "health_score": health_result.overall_score,
            "category": health_result.category.value,
            "explanation": "\n".join(explanation_parts),
            "metrics_analyzed": list(metrics.keys()),
            "primary_concern": health_result.primary_concern,
            "recommendations": health_result.recommendations
        }


@router.get(
    "/compare",
    summary="Compare health across assets",
    description="Compare current health scores across multiple assets."
)
async def compare_assets(
    db: Session = Depends(get_db)
):
    """Compare health across all assets."""
    with DatabaseManager(db) as db_manager:
        assets = db_manager.get_all_assets()
        
        if not assets:
            return {"assets": [], "message": "No assets found"}
        
        comparisons = []
        
        for asset in assets:
            asset_id = asset["asset_id"]
            reading = db_manager.get_latest_reading(asset_id)
            
            if reading and reading.get("health_score") is not None:
                comparisons.append({
                    "asset_id": asset_id,
                    "asset_name": asset.get("asset_name", asset_id),
                    "health_score": round(reading["health_score"], 1),
                    "last_reading": reading["time"],
                    "status": (
                        "excellent" if reading["health_score"] >= 90 else
                        "good" if reading["health_score"] >= 75 else
                        "fair" if reading["health_score"] >= 55 else
                        "poor" if reading["health_score"] >= 30 else
                        "critical"
                    )
                })
        
        # Sort by health score (worst first)
        comparisons.sort(key=lambda x: x["health_score"])
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "asset_count": len(comparisons),
            "assets": comparisons,
            "summary": {
                "healthiest": comparisons[-1]["asset_id"] if comparisons else None,
                "most_concerning": comparisons[0]["asset_id"] if comparisons else None,
                "average_score": round(
                    sum(a["health_score"] for a in comparisons) / len(comparisons), 1
                ) if comparisons else None
            }
          }
