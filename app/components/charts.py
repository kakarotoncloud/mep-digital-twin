"""
Chart Components for Dashboard

This module provides Plotly-based chart components for visualizing
chiller performance data and health metrics.

All charts are designed to be:
- Responsive and interactive
- Consistent in styling
- Informative with proper annotations
- Color-coded for quick interpretation
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from typing import List, Dict, Any, Optional
from datetime import datetime


# =========================================
# Color Schemes
# =========================================

COLORS = {
    "excellent": "#10B981",  # Green
    "good": "#34D399",       # Light green
    "fair": "#FBBF24",       # Yellow
    "poor": "#F97316",       # Orange
    "critical": "#EF4444",   # Red
    "primary": "#3B82F6",    # Blue
    "secondary": "#6B7280",  # Gray
    "background": "#1F2937", # Dark gray
    "text": "#F9FAFB",       # Light text
    "grid": "#374151",       # Grid lines
}

HEALTH_COLORS = {
    "excellent": "#10B981",
    "good": "#34D399", 
    "fair": "#FBBF24",
    "poor": "#F97316",
    "critical": "#EF4444",
}


def get_health_color(score: float) -> str:
    """Get color based on health score."""
    if score >= 90:
        return COLORS["excellent"]
    elif score >= 75:
        return COLORS["good"]
    elif score >= 55:
        return COLORS["fair"]
    elif score >= 30:
        return COLORS["poor"]
    else:
        return COLORS["critical"]


def get_metric_color(metric_name: str, value: float) -> str:
    """Get color based on metric value and thresholds."""
    thresholds = {
        "vibration_rms": [(2.0, "excellent"), (4.0, "good"), (7.0, "fair"), (11.0, "poor")],
        "approach_temp": [(2.0, "excellent"), (3.0, "good"), (4.5, "fair"), (6.0, "poor")],
        "phase_imbalance": [(1.0, "excellent"), (2.0, "good"), (3.5, "fair"), (5.0, "poor")],
        "kw_per_ton": [(0.55, "excellent"), (0.70, "good"), (0.85, "fair"), (1.0, "poor")],
    }
    
    if metric_name not in thresholds:
        return COLORS["primary"]
    
    for threshold, status in thresholds[metric_name]:
        if value <= threshold:
            return HEALTH_COLORS[status]
    
    return HEALTH_COLORS["critical"]


# =========================================
# Chart Layout Defaults
# =========================================

def get_default_layout(title: str = "", height: int = 400) -> dict:
    """Get default chart layout settings."""
    return {
        "title": {
            "text": title,
            "font": {"size": 16, "color": COLORS["text"]},
            "x": 0.5,
            "xanchor": "center"
        },
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "height": height,
        "margin": {"l": 60, "r": 40, "t": 60, "b": 60},
        "font": {"color": COLORS["text"], "size": 12},
        "xaxis": {
            "gridcolor": COLORS["grid"],
            "showgrid": True,
            "zeroline": False,
        },
        "yaxis": {
            "gridcolor": COLORS["grid"],
            "showgrid": True,
            "zeroline": False,
        },
        "legend": {
            "bgcolor": "rgba(0,0,0,0.5)",
            "bordercolor": COLORS["grid"],
            "font": {"color": COLORS["text"]}
        },
        "hovermode": "x unified",
    }


# =========================================
# Health Trend Chart
# =========================================

def create_health_trend_chart(
    times: List[datetime],
    scores: List[float],
    title: str = "Health Score Trend",
    height: int = 350
) -> go.Figure:
    """
    Create a health score trend chart with color-coded zones.
    
    Args:
        times: List of timestamps
        scores: List of health scores (0-100)
        title: Chart title
        height: Chart height in pixels
        
    Returns:
        Plotly Figure object
    """
    fig = go.Figure()
    
    # Add colored background zones
    zone_configs = [
        (90, 100, COLORS["excellent"], "Excellent", 0.15),
        (75, 90, COLORS["good"], "Good", 0.15),
        (55, 75, COLORS["fair"], "Fair", 0.15),
        (30, 55, COLORS["poor"], "Poor", 0.15),
        (0, 30, COLORS["critical"], "Critical", 0.15),
    ]
    
    for y0, y1, color, name, opacity in zone_configs:
        fig.add_hrect(
            y0=y0, y1=y1,
            fillcolor=color,
            opacity=opacity,
            line_width=0,
            annotation_text=name,
            annotation_position="right",
            annotation_font_size=10,
            annotation_font_color=color,
        )
    
    # Add health score line
    colors = [get_health_color(s) for s in scores]
    
    fig.add_trace(go.Scatter(
        x=times,
        y=scores,
        mode="lines+markers",
        name="Health Score",
        line={"color": COLORS["primary"], "width": 2},
        marker={"size": 6, "color": colors},
        hovertemplate="<b>%{y:.1f}</b><br>%{x}<extra></extra>"
    ))
    
    # Update layout
    layout = get_default_layout(title, height)
    layout["yaxis"]["range"] = [0, 105]
    layout["yaxis"]["title"] = "Health Score"
    layout["xaxis"]["title"] = "Time"
    
    fig.update_layout(**layout)
    
    return fig


# =========================================
# Metric Trend Chart
# =========================================

def create_metric_trend_chart(
    times: List[datetime],
    values: List[float],
    metric_name: str,
    unit: str = "",
    thresholds: Optional[Dict[str, float]] = None,
    title: Optional[str] = None,
    height: int = 300
) -> go.Figure:
    """
    Create a trend chart for a single metric with optional thresholds.
    
    Args:
        times: List of timestamps
        values: List of metric values
        metric_name: Name of the metric
        unit: Unit of measurement
        thresholds: Optional dict with 'warning' and 'critical' thresholds
        title: Chart title (defaults to metric name)
        height: Chart height in pixels
        
    Returns:
        Plotly Figure object
    """
    fig = go.Figure()
    
    # Add threshold lines if provided
    if thresholds:
        if "warning" in thresholds:
            fig.add_hline(
                y=thresholds["warning"],
                line_dash="dash",
                line_color=COLORS["fair"],
                annotation_text="Warning",
                annotation_position="right"
            )
        if "critical" in thresholds:
            fig.add_hline(
                y=thresholds["critical"],
                line_dash="dash",
                line_color=COLORS["critical"],
                annotation_text="Critical",
                annotation_position="right"
            )
    
    # Add main trace
    fig.add_trace(go.Scatter(
        x=times,
        y=values,
        mode="lines",
        name=metric_name,
        line={"color": COLORS["primary"], "width": 2},
        fill="tozeroy",
        fillcolor=f"rgba(59, 130, 246, 0.1)",
        hovertemplate=f"<b>%{{y:.2f}}</b> {unit}<br>%{{x}}<extra></extra>"
    ))
    
    # Update layout
    chart_title = title or metric_name.replace("_", " ").title()
    layout = get_default_layout(chart_title, height)
    layout["yaxis"]["title"] = f"{metric_name} ({unit})" if unit else metric_name
    layout["xaxis"]["title"] = "Time"
    layout["showlegend"] = False
    
    fig.update_layout(**layout)
    
    return fig


# =========================================
# Multi-Metric Chart
# =========================================

def create_multi_metric_chart(
    times: List[datetime],
    metrics: Dict[str, List[float]],
    title: str = "Performance Metrics",
    height: int = 400
) -> go.Figure:
    """
    Create a chart with multiple metrics on separate y-axes.
    
    Args:
        times: List of timestamps
        metrics: Dict mapping metric names to value lists
        title: Chart title
        height: Chart height in pixels
        
    Returns:
        Plotly Figure object
    """
    # Define colors for each metric
    metric_colors = {
        "health_score": COLORS["primary"],
        "approach_temp": "#F97316",
        "kw_per_ton": "#10B981",
        "vibration_rms": "#EF4444",
        "power_kw": "#8B5CF6",
        "load_percent": "#6B7280",
        "delta_t": "#06B6D4",
        "phase_imbalance": "#EC4899",
    }
    
    fig = go.Figure()
    
    for i, (metric_name, values) in enumerate(metrics.items()):
        color = metric_colors.get(metric_name, COLORS["primary"])
        
        fig.add_trace(go.Scatter(
            x=times,
            y=values,
            mode="lines",
            name=metric_name.replace("_", " ").title(),
            line={"color": color, "width": 2},
            hovertemplate=f"<b>{metric_name}</b>: %{{y:.2f}}<br>%{{x}}<extra></extra>"
        ))
    
    # Update layout
    layout = get_default_layout(title, height)
    layout["xaxis"]["title"] = "Time"
    layout["legend"]["orientation"] = "h"
    layout["legend"]["yanchor"] = "bottom"
    layout["legend"]["y"] = 1.02
    layout["legend"]["xanchor"] = "center"
    layout["legend"]["x"] = 0.5
    
    fig.update_layout(**layout)
    
    return fig


# =========================================
# Metric Comparison Chart (Bar)
# =========================================

def create_metric_comparison_chart(
    breakdown: List[Dict[str, Any]],
    title: str = "Health Score Breakdown",
    height: int = 300
) -> go.Figure:
    """
    Create a horizontal bar chart showing health score breakdown by metric.
    
    Args:
        breakdown: List of metric breakdown dicts with 'metric_name', 
                  'normalized_score', 'weight', 'status'
        title: Chart title
        height: Chart height in pixels
        
    Returns:
        Plotly Figure object
    """
    if not breakdown:
        # Return empty figure
        fig = go.Figure()
        fig.add_annotation(
            text="No data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font={"size": 16, "color": COLORS["secondary"]}
        )
        fig.update_layout(**get_default_layout(title, height))
        return fig
    
    # Sort by score (lowest first for visibility)
    breakdown = sorted(breakdown, key=lambda x: x.get("normalized_score", 0))
    
    metrics = [b.get("metric_name", "").replace("_", " ").title() for b in breakdown]
    scores = [b.get("normalized_score", 0) for b in breakdown]
    statuses = [b.get("status", "fair") for b in breakdown]
    colors = [HEALTH_COLORS.get(s, COLORS["primary"]) for s in statuses]
    weights = [b.get("weight", 0) * 100 for b in breakdown]
    
    fig = go.Figure()
    
    # Add bars
    fig.add_trace(go.Bar(
        y=metrics,
        x=scores,
        orientation="h",
        marker_color=colors,
        text=[f"{s:.0f}" for s in scores],
        textposition="auto",
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Score: %{x:.1f}/100<br>"
            "<extra></extra>"
        )
    ))
    
    # Add reference line at 70 (fair threshold)
    fig.add_vline(
        x=70,
        line_dash="dash",
        line_color=COLORS["secondary"],
        annotation_text="Fair",
        annotation_position="top"
    )
    
    # Update layout
    layout = get_default_layout(title, height)
    layout["xaxis"]["range"] = [0, 105]
    layout["xaxis"]["title"] = "Score"
    layout["yaxis"]["title"] = ""
    layout["showlegend"] = False
    
    fig.update_layout(**layout)
    
    return fig


# =========================================
# Gauge Chart
# =========================================

def create_gauge_chart(
    value: float,
    title: str = "Health Score",
    min_val: float = 0,
    max_val: float = 100,
    height: int = 250
) -> go.Figure:
    """
    Create a gauge chart for displaying a single value.
    
    Args:
        value: Current value to display
        title: Chart title
        min_val: Minimum value on gauge
        max_val: Maximum value on gauge
        height: Chart height in pixels
        
    Returns:
        Plotly Figure object
    """
    # Determine color based on value (assuming health score)
    color = get_health_color(value)
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=value,
        title={"text": title, "font": {"size": 16, "color": COLORS["text"]}},
        number={"font": {"size": 40, "color": COLORS["text"]}, "suffix": ""},
        gauge={
            "axis": {
                "range": [min_val, max_val],
                "tickwidth": 1,
                "tickcolor": COLORS["text"],
                "tickfont": {"color": COLORS["text"]}
            },
            "bar": {"color": color, "thickness": 0.75},
            "bgcolor": COLORS["background"],
            "borderwidth": 2,
            "bordercolor": COLORS["grid"],
            "steps": [
                {"range": [0, 30], "color": "rgba(239, 68, 68, 0.3)"},
                {"range": [30, 55], "color": "rgba(249, 115, 22, 0.3)"},
                {"range": [55, 75], "color": "rgba(251, 191, 36, 0.3)"},
                {"range": [75, 90], "color": "rgba(52, 211, 153, 0.3)"},
                {"range": [90, 100], "color": "rgba(16, 185, 129, 0.3)"},
            ],
            "threshold": {
                "line": {"color": COLORS["text"], "width": 2},
                "thickness": 0.75,
                "value": value
            }
        }
    ))
    
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": COLORS["text"]},
        height=height,
        margin={"l": 30, "r": 30, "t": 60, "b": 30}
    )
    
    return fig


# =========================================
# Sparkline Chart
# =========================================

def create_sparkline(
    values: List[float],
    color: str = None,
    height: int = 60,
    width: int = 150
) -> go.Figure:
    """
    Create a minimal sparkline chart.
    
    Args:
        values: List of values
        color: Line color (auto-determined if None)
        height: Chart height
        width: Chart width
        
    Returns:
        Plotly Figure object
    """
    if not values:
        values = [0]
    
    if color is None:
        # Color based on trend
        if len(values) > 1:
            if values[-1] > values[0]:
                color = COLORS["good"]
            elif values[-1] < values[0]:
                color = COLORS["poor"]
            else:
                color = COLORS["secondary"]
        else:
            color = COLORS["primary"]
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        y=values,
        mode="lines",
        line={"color": color, "width": 2},
        fill="tozeroy",
        fillcolor=f"rgba({int(color[1:3], 16)}, {int(color[3:5], 16)}, {int(color[5:7], 16)}, 0.1)",
        hoverinfo="skip"
    ))
    
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=height,
        width=width,
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
        xaxis={"visible": False},
        yaxis={"visible": False},
        showlegend=False
    )
    
    return fig


# =========================================
# Scenario Progression Chart
# =========================================

def create_scenario_progression_chart(
    times: List[datetime],
    health_scores: List[float],
    scenario_name: str,
    annotations: Optional[List[Dict[str, Any]]] = None,
    height: int = 400
) -> go.Figure:
    """
    Create a chart showing scenario progression with annotations.
    
    Args:
        times: List of timestamps
        health_scores: List of health scores
        scenario_name: Name of the scenario
        annotations: Optional list of annotation dicts
        height: Chart height
        
    Returns:
        Plotly Figure object
    """
    fig = create_health_trend_chart(
        times, 
        health_scores, 
        title=f"Scenario: {scenario_name}",
        height=height
    )
    
    # Add annotations if provided
    if annotations:
        for ann in annotations:
            fig.add_annotation(
                x=ann.get("x"),
                y=ann.get("y"),
                text=ann.get("text", ""),
                showarrow=True,
                arrowhead=2,
                arrowcolor=COLORS["text"],
                font={"color": COLORS["text"], "size": 10},
                bgcolor="rgba(0,0,0,0.7)",
                bordercolor=COLORS["grid"],
            )
    
    return fig


# =========================================
# Real-time Metrics Dashboard
# =========================================

def create_realtime_dashboard(
    latest_reading: Dict[str, Any],
    height: int = 200
) -> go.Figure:
    """
    Create a dashboard showing current values for key metrics.
    
    Args:
        latest_reading: Dict with current sensor values
        height: Chart height
        
    Returns:
        Plotly Figure with indicator tiles
    """
    metrics = [
        ("Health", latest_reading.get("health_score", 0), "", 0, 100),
        ("Approach", latest_reading.get("approach_temp", 0), "°C", 0, 10),
        ("kW/Ton", latest_reading.get("kw_per_ton", 0), "", 0, 1.5),
        ("Vibration", latest_reading.get("vibration_rms", 0), "mm/s", 0, 15),
        ("Load", latest_reading.get("load_percent", 0), "%", 0, 100),
        ("Power", latest_reading.get("power_kw", 0), "kW", 0, 500),
    ]
    
    fig = make_subplots(
        rows=1, cols=len(metrics),
        specs=[[{"type": "indicator"}] * len(metrics)],
        horizontal_spacing=0.05
    )
    
    for i, (name, value, unit, min_v, max_v) in enumerate(metrics, 1):
        color = get_health_color(value) if name == "Health" else COLORS["primary"]
        
        fig.add_trace(
            go.Indicator(
                mode="number",
                value=value if value else 0,
                title={"text": f"{name}", "font": {"size": 12}},
                number={
                    "font": {"size": 24, "color": color},
                    "suffix": f" {unit}" if unit else ""
                },
            ),
            row=1, col=i
        )
    
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=height,
        margin={"l": 20, "r": 20, "t": 40, "b": 20},
        font={"color": COLORS["text"]}
    )
    
    return fig
