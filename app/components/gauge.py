"""
Gauge and Metric Card Components

This module provides visual components for displaying single values
with context, including health gauges, metric cards, and status indicators.

These components are designed to provide at-a-glance understanding
of system health and performance.
"""

import streamlit as st
from typing import Optional, Tuple


# =========================================
# Color Utilities
# =========================================

def get_health_color(score: float) -> str:
    """Get color hex code based on health score."""
    if score >= 90:
        return "#10B981"  # Green - Excellent
    elif score >= 75:
        return "#34D399"  # Light green - Good
    elif score >= 55:
        return "#FBBF24"  # Yellow - Fair
    elif score >= 30:
        return "#F97316"  # Orange - Poor
    else:
        return "#EF4444"  # Red - Critical


def get_health_category(score: float) -> str:
    """Get category name based on health score."""
    if score >= 90:
        return "Excellent"
    elif score >= 75:
        return "Good"
    elif score >= 55:
        return "Fair"
    elif score >= 30:
        return "Poor"
    else:
        return "Critical"


def get_health_emoji(score: float) -> str:
    """Get emoji based on health score."""
    if score >= 90:
        return "🟢"
    elif score >= 75:
        return "🟢"
    elif score >= 55:
        return "🟡"
    elif score >= 30:
        return "🟠"
    else:
        return "🔴"


def get_metric_status(metric_name: str, value: float) -> Tuple[str, str, str]:
    """
    Get status, color, and emoji for a specific metric value.
    
    Returns:
        Tuple of (status, color, emoji)
    """
    thresholds = {
        "vibration_rms": [
            (2.0, "Excellent", "#10B981", "✅"),
            (4.0, "Good", "#34D399", "✅"),
            (7.0, "Fair", "#FBBF24", "⚠️"),
            (11.0, "Poor", "#F97316", "🔶"),
            (float('inf'), "Critical", "#EF4444", "🔴"),
        ],
        "approach_temp": [
            (2.0, "Excellent", "#10B981", "✅"),
            (3.0, "Good", "#34D399", "✅"),
            (4.5, "Fair", "#FBBF24", "⚠️"),
            (6.0, "Poor", "#F97316", "🔶"),
            (float('inf'), "Critical", "#EF4444", "🔴"),
        ],
        "phase_imbalance": [
            (1.0, "Excellent", "#10B981", "✅"),
            (2.0, "Good", "#34D399", "✅"),
            (3.5, "Fair", "#FBBF24", "⚠️"),
            (5.0, "Poor", "#F97316", "🔶"),
            (float('inf'), "Critical", "#EF4444", "🔴"),
        ],
        "kw_per_ton": [
            (0.55, "Excellent", "#10B981", "✅"),
            (0.70, "Good", "#34D399", "✅"),
            (0.85, "Fair", "#FBBF24", "⚠️"),
            (1.0, "Poor", "#F97316", "🔶"),
            (float('inf'), "Critical", "#EF4444", "🔴"),
        ],
        "health_score": [
            (30, "Critical", "#EF4444", "🔴"),
            (55, "Poor", "#F97316", "🔶"),
            (75, "Fair", "#FBBF24", "⚠️"),
            (90, "Good", "#34D399", "✅"),
            (float('inf'), "Excellent", "#10B981", "✅"),
        ],
    }
    
    if metric_name not in thresholds:
        return ("Unknown", "#6B7280", "❓")
    
    # Health score is reversed (higher is better)
    if metric_name == "health_score":
        for threshold, status, color, emoji in thresholds[metric_name]:
            if value < threshold:
                return (status, color, emoji)
    else:
        for threshold, status, color, emoji in thresholds[metric_name]:
            if value <= threshold:
                return (status, color, emoji)
    
    return ("Unknown", "#6B7280", "❓")


# =========================================
# Health Gauge Component
# =========================================

def render_health_gauge(
    score: float,
    title: str = "Health Score",
    show_category: bool = True,
    size: str = "large"
) -> None:
    """
    Render a health score gauge using Streamlit components.
    
    Args:
        score: Health score (0-100)
        title: Title to display
        show_category: Whether to show the category label
        size: "small", "medium", or "large"
    """
    color = get_health_color(score)
    category = get_health_category(score)
    emoji = get_health_emoji(score)
    
    # Size configurations
    sizes = {
        "small": {"score_size": "2rem", "title_size": "0.9rem", "padding": "0.5rem"},
        "medium": {"score_size": "3rem", "title_size": "1rem", "padding": "1rem"},
        "large": {"score_size": "4rem", "title_size": "1.2rem", "padding": "1.5rem"},
    }
    
    config = sizes.get(size, sizes["medium"])
    
    # Create the gauge display
    gauge_html = f"""
    <div style="
        text-align: center;
        padding: {config['padding']};
        background: linear-gradient(135deg, rgba(31, 41, 55, 0.8), rgba(17, 24, 39, 0.9));
        border-radius: 12px;
        border: 1px solid {color}40;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    ">
        <div style="
            font-size: {config['title_size']};
            color: #9CA3AF;
            margin-bottom: 0.5rem;
            text-transform: uppercase;
            letter-spacing: 1px;
        ">{title}</div>
        <div style="
            font-size: {config['score_size']};
            font-weight: bold;
            color: {color};
            text-shadow: 0 0 20px {color}60;
        ">{score:.1f}</div>
        <div style="
            font-size: 1rem;
            color: {color};
            margin-top: 0.5rem;
        ">{emoji} {category if show_category else ''}</div>
        <div style="
            margin-top: 0.75rem;
            height: 8px;
            background: #374151;
            border-radius: 4px;
            overflow: hidden;
        ">
            <div style="
                width: {score}%;
                height: 100%;
                background: linear-gradient(90deg, {color}, {color}CC);
                border-radius: 4px;
                transition: width 0.5s ease;
            "></div>
        </div>
    </div>
    """
    
    st.markdown(gauge_html, unsafe_allow_html=True)


# =========================================
# Metric Card Component
# =========================================

def render_metric_card(
    title: str,
    value: float,
    unit: str = "",
    metric_name: Optional[str] = None,
    delta: Optional[float] = None,
    delta_suffix: str = "",
    show_status: bool = True,
    help_text: Optional[str] = None
) -> None:
    """
    Render a metric card with value, optional delta, and status indicator.
    
    Args:
        title: Card title
        value: Current value
        unit: Unit of measurement
        metric_name: Name for threshold lookup (if None, uses generic display)
        delta: Optional change value
        delta_suffix: Suffix for delta (e.g., "vs yesterday")
        show_status: Whether to show status indicator
        help_text: Optional help tooltip text
    """
    # Get status if metric_name provided
    if metric_name and show_status:
        status, color, emoji = get_metric_status(metric_name, value)
    else:
        status, color, emoji = ("", "#3B82F6", "")
    
    # Delta display
    delta_html = ""
    if delta is not None:
        delta_color = "#10B981" if delta >= 0 else "#EF4444"
        delta_arrow = "↑" if delta >= 0 else "↓"
        delta_html = f"""
        <div style="
            font-size: 0.85rem;
            color: {delta_color};
            margin-top: 0.25rem;
        ">{delta_arrow} {abs(delta):.2f} {delta_suffix}</div>
        """
    
    # Status badge
    status_html = ""
    if show_status and status:
        status_html = f"""
        <div style="
            display: inline-block;
            font-size: 0.75rem;
            color: {color};
            background: {color}20;
            padding: 2px 8px;
            border-radius: 4px;
            margin-top: 0.5rem;
        ">{emoji} {status}</div>
        """
    
    # Help icon
    help_html = ""
    if help_text:
        help_html = f"""
        <span style="
            font-size: 0.75rem;
            color: #6B7280;
            cursor: help;
        " title="{help_text}">ⓘ</span>
        """
    
    card_html = f"""
    <div style="
        padding: 1rem;
        background: linear-gradient(135deg, rgba(31, 41, 55, 0.6), rgba(17, 24, 39, 0.8));
        border-radius: 10px;
        border: 1px solid #374151;
        transition: transform 0.2s, box-shadow 0.2s;
    ">
        <div style="
            font-size: 0.85rem;
            color: #9CA3AF;
            margin-bottom: 0.5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        ">
            <span>{title}</span>
            {help_html}
        </div>
        <div style="
            font-size: 1.75rem;
            font-weight: bold;
            color: {color};
        ">{value:.2f} <span style="font-size: 1rem; color: #6B7280;">{unit}</span></div>
        {delta_html}
        {status_html}
    </div>
    """
    
    st.markdown(card_html, unsafe_allow_html=True)


# =========================================
# Status Indicator Component
# =========================================

def render_status_indicator(
    status: str,
    message: str = "",
    size: str = "medium"
) -> None:
    """
    Render a status indicator badge.
    
    Args:
        status: One of "excellent", "good", "fair", "poor", "critical"
        message: Optional message to display
        size: "small", "medium", or "large"
    """
    status_config = {
        "excellent": {"color": "#10B981", "emoji": "🟢", "label": "Excellent"},
        "good": {"color": "#34D399", "emoji": "🟢", "label": "Good"},
        "fair": {"color": "#FBBF24", "emoji": "🟡", "label": "Fair"},
        "poor": {"color": "#F97316", "emoji": "🟠", "label": "Poor"},
        "critical": {"color": "#EF4444", "emoji": "🔴", "label": "Critical"},
        "unknown": {"color": "#6B7280", "emoji": "⚪", "label": "Unknown"},
    }
    
    config = status_config.get(status.lower(), status_config["unknown"])
    
    sizes = {
        "small": {"font": "0.75rem", "padding": "2px 6px"},
        "medium": {"font": "0.875rem", "padding": "4px 10px"},
        "large": {"font": "1rem", "padding": "6px 14px"},
    }
    
    size_config = sizes.get(size, sizes["medium"])
    
    display_message = message if message else config["label"]
    
    indicator_html = f"""
    <div style="
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-size: {size_config['font']};
        color: {config['color']};
        background: {config['color']}20;
        padding: {size_config['padding']};
        border-radius: 6px;
        border: 1px solid {config['color']}40;
    ">
        <span>{config['emoji']}</span>
        <span>{display_message}</span>
    </div>
    """
    
    st.markdown(indicator_html, unsafe_allow_html=True)


# =========================================
# Metric Row Component
# =========================================

def render_metric_row(metrics: list) -> None:
    """
    Render a row of metric cards.
    
    Args:
        metrics: List of dicts with keys: title, value, unit, metric_name (optional)
    """
    cols = st.columns(len(metrics))
    
    for col, metric in zip(cols, metrics):
        with col:
            render_metric_card(
                title=metric.get("title", "Metric"),
                value=metric.get("value", 0),
                unit=metric.get("unit", ""),
                metric_name=metric.get("metric_name"),
                delta=metric.get("delta"),
                show_status=metric.get("show_status", True)
            )


# =========================================
# Alert Banner Component
# =========================================

def render_alert_banner(
    message: str,
    severity: str = "warning",
    icon: Optional[str] = None
) -> None:
    """
    Render an alert banner.
    
    Args:
        message: Alert message
        severity: "info", "warning", "error", or "success"
        icon: Optional custom icon
    """
    severity_config = {
        "info": {"color": "#3B82F6", "bg": "#1E3A5F", "icon": "ℹ️"},
        "warning": {"color": "#FBBF24", "bg": "#422006", "icon": "⚠️"},
        "error": {"color": "#EF4444", "bg": "#450A0A", "icon": "🚨"},
        "success": {"color": "#10B981", "bg": "#064E3B", "icon": "✅"},
    }
    
    config = severity_config.get(severity, severity_config["info"])
    display_icon = icon if icon else config["icon"]
    
    banner_html = f"""
    <div style="
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 12px 16px;
        background: {config['bg']};
        border-left: 4px solid {config['color']};
        border-radius: 0 8px 8px 0;
        margin: 8px 0;
    ">
        <span style="font-size: 1.25rem;">{display_icon}</span>
        <span style="color: {config['color']}; font-size: 0.95rem;">{message}</span>
    </div>
    """
    
    st.markdown(banner_html, unsafe_allow_html=True)


# =========================================
# Progress Bar Component
# =========================================

def render_progress_bar(
    value: float,
    max_value: float = 100,
    label: str = "",
    color: Optional[str] = None,
    show_percentage: bool = True
) -> None:
    """
    Render a custom progress bar.
    
    Args:
        value: Current value
        max_value: Maximum value
        label: Optional label
        color: Bar color (auto if None)
        show_percentage: Whether to show percentage
    """
    percentage = min(100, (value / max_value) * 100) if max_value > 0 else 0
    
    if color is None:
        color = get_health_color(percentage)
    
    percentage_text = f"{percentage:.1f}%" if show_percentage else ""
    
    bar_html = f"""
    <div style="margin: 8px 0;">
        <div style="
            display: flex;
            justify-content: space-between;
            margin-bottom: 4px;
            font-size: 0.85rem;
            color: #9CA3AF;
        ">
            <span>{label}</span>
            <span>{percentage_text}</span>
        </div>
        <div style="
            height: 10px;
            background: #374151;
            border-radius: 5px;
            overflow: hidden;
        ">
            <div style="
                width: {percentage}%;
                height: 100%;
                background: linear-gradient(90deg, {color}, {color}BB);
                border-radius: 5px;
                transition: width 0.3s ease;
            "></div>
        </div>
    </div>
    """
    
    st.markdown(bar_html, unsafe_allow_html=True)
