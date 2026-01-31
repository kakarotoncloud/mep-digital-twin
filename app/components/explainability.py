"""
Explainability Components

This module provides components for explaining health scores,
displaying recommendations, and showing failure scenario stories.

Explainability is crucial for building trust with maintenance teams
and enabling informed decision-making.
"""

import streamlit as st
from typing import List, Dict, Any, Optional


# =========================================
# Color and Status Utilities
# =========================================

STATUS_COLORS = {
    "excellent": "#10B981",
    "good": "#34D399",
    "fair": "#FBBF24",
    "poor": "#F97316",
    "critical": "#EF4444",
}

STATUS_EMOJIS = {
    "excellent": "✅",
    "good": "✅",
    "fair": "⚠️",
    "poor": "🔶",
    "critical": "🔴",
}


def get_status_color(status: str) -> str:
    """Get color for a status."""
    return STATUS_COLORS.get(status.lower(), "#6B7280")


def get_status_emoji(status: str) -> str:
    """Get emoji for a status."""
    return STATUS_EMOJIS.get(status.lower(), "❓")


# =========================================
# Health Breakdown Component
# =========================================

def render_health_breakdown(
    breakdown: List[Dict[str, Any]],
    show_weights: bool = True,
    show_details: bool = True
) -> None:
    """
    Render a detailed breakdown of health score contributions.
    
    Args:
        breakdown: List of metric breakdown dicts
        show_weights: Whether to show weight percentages
        show_details: Whether to show expandable details
    """
    if not breakdown:
        st.info("No health breakdown data available")
        return
    
    st.markdown("### 📊 Health Score Breakdown")
    
    # Sort by score (worst first for attention)
    sorted_breakdown = sorted(breakdown, key=lambda x: x.get("normalized_score", 0))
    
    for item in sorted_breakdown:
        metric_name = item.get("metric_name", "Unknown")
        raw_value = item.get("raw_value", 0)
        score = item.get("normalized_score", 0)
        weight = item.get("weight", 0)
        status = item.get("status", "fair")
        message = item.get("message", "")
        
        color = get_status_color(status)
        emoji = get_status_emoji(status)
        
        # Display name formatting
        display_name = metric_name.replace("_", " ").title()
        
        # Create the breakdown item
        breakdown_html = f"""
        <div style="
            padding: 12px;
            background: rgba(31, 41, 55, 0.6);
            border-radius: 8px;
            border-left: 4px solid {color};
            margin-bottom: 10px;
        ">
            <div style="
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 8px;
            ">
                <div style="
                    display: flex;
                    align-items: center;
                    gap: 8px;
                ">
                    <span style="font-size: 1.1rem;">{emoji}</span>
                    <span style="
                        font-weight: 600;
                        color: #F3F4F6;
                    ">{display_name}</span>
                    {f'<span style="font-size: 0.75rem; color: #6B7280;">({weight*100:.0f}% weight)</span>' if show_weights else ''}
                </div>
                <div style="
                    display: flex;
                    align-items: center;
                    gap: 12px;
                ">
                    <span style="
                        font-size: 0.9rem;
                        color: #9CA3AF;
                    ">Value: <strong style="color: #F3F4F6;">{raw_value:.2f}</strong></span>
                    <span style="
                        font-size: 1.1rem;
                        font-weight: bold;
                        color: {color};
                    ">{score:.0f}/100</span>
                </div>
            </div>
            <div style="
                height: 6px;
                background: #374151;
                border-radius: 3px;
                overflow: hidden;
            ">
                <div style="
                    width: {score}%;
                    height: 100%;
                    background: {color};
                    border-radius: 3px;
                "></div>
            </div>
            {f'<div style="margin-top: 8px; font-size: 0.85rem; color: #9CA3AF;">{message}</div>' if show_details and message else ''}
        </div>
        """
        
        st.markdown(breakdown_html, unsafe_allow_html=True)


# =========================================
# Recommendations Component
# =========================================

def render_recommendations(
    recommendations: List[str],
    title: str = "🔧 Recommended Actions",
    severity: str = "warning"
) -> None:
    """
    Render a list of recommendations.
    
    Args:
        recommendations: List of recommendation strings
        title: Section title
        severity: "info", "warning", or "critical" for styling
    """
    if not recommendations:
        return
    
    severity_config = {
        "info": {"border": "#3B82F6", "bg": "rgba(59, 130, 246, 0.1)"},
        "warning": {"border": "#FBBF24", "bg": "rgba(251, 191, 36, 0.1)"},
        "critical": {"border": "#EF4444", "bg": "rgba(239, 68, 68, 0.1)"},
    }
    
    config = severity_config.get(severity, severity_config["warning"])
    
    st.markdown(f"### {title}")
    
    recommendations_html = f"""
    <div style="
        padding: 16px;
        background: {config['bg']};
        border: 1px solid {config['border']}40;
        border-radius: 10px;
    ">
    """
    
    for i, rec in enumerate(recommendations, 1):
        # Check if it's an urgent recommendation
        is_urgent = rec.startswith("⚠️") or rec.startswith("🚨") or "URGENT" in rec
        
        recommendations_html += f"""
        <div style="
            display: flex;
            gap: 12px;
            padding: 10px 0;
            {'border-bottom: 1px solid #37415180;' if i < len(recommendations) else ''}
        ">
            <span style="
                display: flex;
                align-items: center;
                justify-content: center;
                width: 24px;
                height: 24px;
                background: {config['border']}30;
                color: {config['border']};
                border-radius: 50%;
                font-size: 0.85rem;
                font-weight: bold;
                flex-shrink: 0;
            ">{i}</span>
            <span style="
                color: {'#FBBF24' if is_urgent else '#E5E7EB'};
                font-size: 0.95rem;
                line-height: 1.5;
                {'font-weight: 600;' if is_urgent else ''}
            ">{rec}</span>
        </div>
        """
    
    recommendations_html += "</div>"
    
    st.markdown(recommendations_html, unsafe_allow_html=True)


# =========================================
# Scenario Story Component
# =========================================

def render_scenario_story(
    scenario_name: str,
    story: str,
    affected_metrics: List[str] = None,
    duration_days: int = None
) -> None:
    """
    Render a failure scenario story with formatting.
    
    Args:
        scenario_name: Name of the scenario
        story: The story text (may contain markdown-like formatting)
        affected_metrics: List of metrics affected by this scenario
        duration_days: Duration of the scenario in days
    """
    st.markdown(f"### 📖 Scenario: {scenario_name}")
    
    # Metadata pills
    if affected_metrics or duration_days:
        pills_html = '<div style="display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 16px;">'
        
        if duration_days:
            pills_html += f"""
            <span style="
                background: #374151;
                color: #9CA3AF;
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 0.8rem;
            ">⏱️ {duration_days} days</span>
            """
        
        if affected_metrics:
            for metric in affected_metrics:
                pills_html += f"""
                <span style="
                    background: #1E3A5F;
                    color: #60A5FA;
                    padding: 4px 12px;
                    border-radius: 20px;
                    font-size: 0.8rem;
                ">{metric.replace('_', ' ').title()}</span>
                """
        
        pills_html += "</div>"
        st.markdown(pills_html, unsafe_allow_html=True)
    
    # Process and display story
    # Convert some simple formatting
    formatted_story = story.strip()
    
    # Create story container
    story_html = f"""
    <div style="
        padding: 20px;
        background: linear-gradient(135deg, rgba(31, 41, 55, 0.8), rgba(17, 24, 39, 0.95));
        border-radius: 12px;
        border: 1px solid #374151;
        font-family: 'Courier New', monospace;
        font-size: 0.9rem;
        line-height: 1.6;
        color: #D1D5DB;
        white-space: pre-wrap;
        max-height: 500px;
        overflow-y: auto;
    ">{formatted_story}</div>
    """
    
    st.markdown(story_html, unsafe_allow_html=True)


# =========================================
# Insight Card Component
# =========================================

def render_insight_card(
    title: str,
    value: str,
    description: str,
    icon: str = "💡",
    color: str = "#3B82F6"
) -> None:
    """
    Render an insight card with icon, value, and description.
    
    Args:
        title: Card title
        value: Main value/insight to display
        description: Longer description
        icon: Emoji icon
        color: Accent color
    """
    card_html = f"""
    <div style="
        padding: 16px;
        background: rgba(31, 41, 55, 0.7);
        border-radius: 10px;
        border: 1px solid {color}40;
    ">
        <div style="
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 10px;
        ">
            <span style="font-size: 1.5rem;">{icon}</span>
            <span style="
                font-size: 0.9rem;
                color: #9CA3AF;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            ">{title}</span>
        </div>
        <div style="
            font-size: 1.5rem;
            font-weight: bold;
            color: {color};
            margin-bottom: 8px;
        ">{value}</div>
        <div style="
            font-size: 0.9rem;
            color: #9CA3AF;
            line-height: 1.5;
        ">{description}</div>
    </div>
    """
    
    st.markdown(card_html, unsafe_allow_html=True)


# =========================================
# Why This Matters Component
# =========================================

def render_why_this_matters(
    metric_name: str,
    status: str,
    value: float
) -> None:
    """
    Render an explanation of why a metric's status matters.
    
    Args:
        metric_name: Name of the metric
        status: Current status
        value: Current value
    """
    explanations = {
        "vibration_rms": {
            "excellent": "Vibration is in excellent range. The compressor bearings and mechanical components are in great condition.",
            "good": "Vibration is within normal limits. Continue routine monitoring.",
            "fair": "Vibration is elevated. This could indicate early bearing wear or alignment issues. Schedule vibration analysis.",
            "poor": "Vibration is concerning. Bearing damage or mechanical issues likely developing. Plan inspection within 1-2 weeks.",
            "critical": "Vibration is critical! Risk of imminent mechanical failure. Reduce load and inspect immediately.",
        },
        "approach_temp": {
            "excellent": "Excellent heat transfer efficiency. Condenser tubes are clean and refrigerant charge is optimal.",
            "good": "Good condenser performance. Heat transfer is efficient.",
            "fair": "Condenser efficiency is degrading. Possible early fouling. Consider scheduling tube cleaning.",
            "poor": "Significant condenser fouling likely. Energy waste of 10-15%. Schedule tube cleaning soon.",
            "critical": "Severe condenser fouling! Energy waste exceeds 20%. Immediate cleaning required.",
        },
        "phase_imbalance": {
            "excellent": "Excellent electrical balance. Power supply and connections are in good condition.",
            "good": "Electrical balance is acceptable. No concerns.",
            "fair": "Phase imbalance is elevated. Check electrical connections and power supply quality.",
            "poor": "Significant phase imbalance. Motor is running hot and life is being reduced. Investigate electrical supply.",
            "critical": "Critical phase imbalance! Motor at risk of damage. Reduce load and check electrical immediately.",
        },
        "kw_per_ton": {
            "excellent": "Excellent efficiency! The chiller is performing at or above design specifications.",
            "good": "Good efficiency. Normal operation.",
            "fair": "Efficiency is below optimal. Check for fouling, refrigerant charge, or control issues.",
            "poor": "Poor efficiency. Multiple issues may be present. Full diagnostic recommended.",
            "critical": "Critical efficiency loss! Major mechanical or system issues. Investigate immediately.",
        },
    }
    
    metric_explanations = explanations.get(metric_name, {})
    explanation = metric_explanations.get(status.lower(), "Status information not available for this metric.")
    
    color = get_status_color(status)
    emoji = get_status_emoji(status)
    
    display_name = metric_name.replace("_", " ").title()
    
    html = f"""
    <div style="
        padding: 16px;
        background: {color}10;
        border-left: 4px solid {color};
        border-radius: 0 8px 8px 0;
        margin: 12px 0;
    ">
        <div style="
            font-weight: 600;
            color: {color};
            margin-bottom: 8px;
            font-size: 1rem;
        ">{emoji} {display_name}: {status.title()}</div>
        <div style="
            color: #D1D5DB;
            font-size: 0.95rem;
            line-height: 1.6;
        ">{explanation}</div>
    </div>
    """
    
    st.markdown(html, unsafe_allow_html=True)


# =========================================
# Cost Impact Component
# =========================================

def render_cost_impact(
    issue_type: str,
    severity: str,
    estimated_impact: Optional[str] = None
) -> None:
    """
    Render estimated cost impact of an issue.
    
    Args:
        issue_type: Type of issue (e.g., "tube_fouling")
        severity: Severity level
        estimated_impact: Optional custom impact string
    """
    # Default cost impacts
    cost_impacts = {
        "tube_fouling": {
            "fair": ("$5,000 - $15,000/year", "Energy waste beginning"),
            "poor": ("$25,000 - $50,000/year", "Significant energy waste"),
            "critical": ("$50,000 - $150,000/year", "Major efficiency loss"),
        },
        "bearing_wear": {
            "fair": ("$5,000 - $10,000", "Planned bearing replacement"),
            "poor": ("$15,000 - $30,000", "Urgent repair needed"),
            "critical": ("$50,000 - $200,000", "Compressor replacement risk"),
        },
        "electrical_issue": {
            "fair": ("$500 - $2,000", "Electrical inspection"),
            "poor": ("$5,000 - $15,000", "Motor rewinding possible"),
            "critical": ("$25,000 - $75,000", "Motor replacement risk"),
        },
    }
    
    impacts = cost_impacts.get(issue_type, {})
    impact_data = impacts.get(severity.lower(), (estimated_impact or "Unknown", "Impact not estimated"))
    
    cost, description = impact_data
    
    severity_color = get_status_color(severity)
    
    html = f"""
    <div style="
        padding: 16px;
        background: rgba(31, 41, 55, 0.8);
        border-radius: 10px;
        border: 1px solid {severity_color}40;
    ">
        <div style="
            font-size: 0.85rem;
            color: #9CA3AF;
            margin-bottom: 8px;
        ">💰 Estimated Cost Impact</div>
        <div style="
            font-size: 1.5rem;
            font-weight: bold;
            color: {severity_color};
            margin-bottom: 8px;
        ">{cost}</div>
        <div style="
            font-size: 0.9rem;
            color: #D1D5DB;
        ">{description}</div>
    </div>
    """
    
    st.markdown(html, unsafe_allow_html=True)


# =========================================
# Comparison Panel Component
# =========================================

def render_comparison_panel(
    current: Dict[str, float],
    baseline: Dict[str, float],
    title: str = "Current vs Baseline"
) -> None:
    """
    Render a comparison panel showing current values vs baseline.
    
    Args:
        current: Current metric values
        baseline: Baseline/expected values
        title: Panel title
    """
    st.markdown(f"### {title}")
    
    for metric_name, current_value in current.items():
        baseline_value = baseline.get(metric_name, current_value)
        diff = current_value - baseline_value
        diff_pct = (diff / baseline_value * 100) if baseline_value != 0 else 0
        
        is_worse = diff > 0 if metric_name in ["vibration_rms", "approach_temp", "kw_per_ton", "phase_imbalance"] else diff < 0
        
        color = "#EF4444" if is_worse and abs(diff_pct) > 10 else "#10B981" if not is_worse else "#FBBF24"
        arrow = "↑" if diff > 0 else "↓" if diff < 0 else "→"
        
        display_name = metric_name.replace("_", " ").title()
        
        html = f"""
        <div style="
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 0;
            border-bottom: 1px solid #37415150;
        ">
            <span style="color: #9CA3AF;">{display_name}</span>
            <div style="display: flex; align-items: center; gap: 16px;">
                <span style="color: #6B7280;">{baseline_value:.2f}</span>
                <span style="color: {color}; font-weight: 600;">
                    {arrow} {current_value:.2f}
                </span>
                <span style="
                    color: {color};
                    font-size: 0.85rem;
                    background: {color}20;
                    padding: 2px 8px;
                    border-radius: 4px;
                ">{diff_pct:+.1f}%</span>
            </div>
        </div>
        """
        
        st.markdown(html, unsafe_allow_html=True)
