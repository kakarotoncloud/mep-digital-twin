"""
Dashboard Components Module

Reusable UI components for the Streamlit dashboard.

Components:
- charts: Plotly-based visualization components
- gauge: Health score gauge display
- explainability: Insight and recommendation panels
"""

from .charts import (
    create_health_trend_chart,
    create_metric_trend_chart,
    create_multi_metric_chart,
    create_metric_comparison_chart,
    create_gauge_chart,
)
from .gauge import (
    render_health_gauge,
    render_metric_card,
    render_status_indicator,
)
from .explainability import (
    render_health_breakdown,
    render_recommendations,
    render_scenario_story,
)

__all__ = [
    # Charts
    "create_health_trend_chart",
    "create_metric_trend_chart",
    "create_multi_metric_chart",
    "create_metric_comparison_chart",
    "create_gauge_chart",
    
    # Gauge
    "render_health_gauge",
    "render_metric_card",
    "render_status_indicator",
    
    # Explainability
    "render_health_breakdown",
    "render_recommendations",
    "render_scenario_story",
]
