"""
MEP Digital Twin - Streamlit Cloud Version
Standalone dashboard that works without external database
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
import math
import random
import json

# =============================================
# PAGE CONFIGURATION
# =============================================

st.set_page_config(
    page_title="MEP Digital Twin",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================
# CUSTOM CSS
# =============================================

st.markdown("""
<style>
    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    .stMetric {
        background: linear-gradient(135deg, #1e3a5f 0%, #0d1b2a 100%);
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #2d4a6f;
    }
    .health-excellent { color: #10B981; }
    .health-good { color: #34D399; }
    .health-fair { color: #FBBF24; }
    .health-poor { color: #F97316; }
    .health-critical { color: #EF4444; }
</style>
""", unsafe_allow_html=True)

# =============================================
# PHYSICS CALCULATOR
# =============================================

class PhysicsCalculator:
    """Physics calculations for chiller metrics."""
    
    @staticmethod
    def calculate_delta_t(chw_return: float, chw_supply: float) -> float:
        return chw_return - chw_supply
    
    @staticmethod
    def calculate_cooling_tons(delta_t: float, flow_gpm: float = 1000) -> float:
        delta_t_f = delta_t * 9.0 / 5.0
        tons = (flow_gpm * delta_t_f * 500) / 12000
        return max(tons, 0.1)
    
    @staticmethod
    def calculate_kw_per_ton(power_kw: float, delta_t: float, flow_gpm: float = 1000) -> float:
        if power_kw <= 0:
            return 0.0
        tons = PhysicsCalculator.calculate_cooling_tons(delta_t, flow_gpm)
        return power_kw / tons if tons > 0.1 else 0.0
    
    @staticmethod
    def calculate_approach(cdw_outlet: float, offset: float = 3.0) -> float:
        return offset
    
    @staticmethod
    def calculate_phase_imbalance(i_r: float, i_y: float, i_b: float) -> float:
        currents = [i_r, i_y, i_b]
        avg = sum(currents) / 3
        if avg < 0.1:
            return 0.0
        max_dev = max(abs(c - avg) for c in currents)
        return (max_dev / avg) * 100
    
    @staticmethod
    def calculate_cop(delta_t: float, power_kw: float, flow_gpm: float = 1000) -> float:
        if power_kw <= 0:
            return 0.0
        tons = PhysicsCalculator.calculate_cooling_tons(delta_t, flow_gpm)
        cooling_kw = tons * 3.517
        return cooling_kw / power_kw

# =============================================
# HEALTH SCORE ENGINE
# =============================================

class HealthScoreEngine:
    """Calculate health scores from metrics."""
    
    def __init__(self):
        self.weights = {
            "vibration_rms": 0.35,
            "approach_temp": 0.25,
            "phase_imbalance": 0.20,
            "kw_per_ton": 0.15,
            "delta_t": 0.05,
        }
        
        self.thresholds = {
            "vibration_rms": {"excellent": 2.0, "good": 4.0, "fair": 7.0, "poor": 11.0},
            "approach_temp": {"excellent": 2.0, "good": 3.0, "fair": 4.5, "poor": 6.0},
            "phase_imbalance": {"excellent": 1.0, "good": 2.0, "fair": 3.5, "poor": 5.0},
            "kw_per_ton": {"excellent": 0.55, "good": 0.70, "fair": 0.85, "poor": 1.0},
        }
    
    def score_metric(self, name: str, value: float) -> tuple:
        if name not in self.thresholds:
            if name == "delta_t":
                target = 5.5
                deviation = abs(value - target)
                if deviation <= 1.0:
                    return 95.0, "excellent"
                elif deviation <= 2.0:
                    return 80.0, "good"
                elif deviation <= 3.5:
                    return 60.0, "fair"
                elif deviation <= 5.0:
                    return 40.0, "poor"
                else:
                    return 20.0, "critical"
            return 50.0, "unknown"
        
        t = self.thresholds[name]
        if value <= t["excellent"]:
            return 95.0, "excellent"
        elif value <= t["good"]:
            return 80.0, "good"
        elif value <= t["fair"]:
            return 60.0, "fair"
        elif value <= t["poor"]:
            return 40.0, "poor"
        else:
            return 20.0, "critical"
    
    def calculate(self, metrics: Dict[str, float]) -> Dict[str, Any]:
        breakdown = []
        total_score = 0
        total_weight = 0
        
        for name, weight in self.weights.items():
            if name in metrics and metrics[name] is not None:
                value = metrics[name]
                score, status = self.score_metric(name, value)
                contribution = score * weight
                total_score += contribution
                total_weight += weight
                breakdown.append({
                    "metric": name,
                    "value": value,
                    "score": score,
                    "status": status,
                    "weight": weight,
                    "contribution": contribution
                })
        
        overall = total_score / total_weight if total_weight > 0 else 50.0
        
        if overall >= 90:
            category = "excellent"
        elif overall >= 75:
            category = "good"
        elif overall >= 55:
            category = "fair"
        elif overall >= 30:
            category = "poor"
        else:
            category = "critical"
        
        breakdown.sort(key=lambda x: x["score"])
        primary_concern = breakdown[0]["metric"] if breakdown and breakdown[0]["score"] < 70 else None
        
        return {
            "overall_score": overall,
            "category": category,
            "breakdown": breakdown,
            "primary_concern": primary_concern
        }

# =============================================
# DATA GENERATOR
# =============================================

class ChillerDataGenerator:
    """Generate synthetic chiller data with failure scenarios."""
    
    def __init__(self, asset_id: str = "CH-001"):
        self.asset_id = asset_id
        self.baseline = {
            "chw_supply_temp": 6.7,
            "chw_return_temp": 12.2,
            "cdw_inlet_temp": 29.4,
            "cdw_outlet_temp": 35.0,
            "ambient_temp": 25.0,
            "vibration_rms": 2.0,
            "power_kw": 280.0,
            "current_r": 200.0,
            "current_y": 200.0,
            "current_b": 200.0,
            "load_percent": 80.0,
            "chw_flow_gpm": 1000.0,
        }
    
    def generate_healthy(self, days: int = 7, interval_minutes: int = 30) -> pd.DataFrame:
        records = []
        start_time = datetime.now() - timedelta(days=days)
        current_time = start_time
        
        while current_time < datetime.now():
            hour = current_time.hour
            load_factor = self._get_load_factor(hour)
            
            record = self._generate_record(current_time, load_factor, 0, 0)
            records.append(record)
            current_time += timedelta(minutes=interval_minutes)
        
        return pd.DataFrame(records)
    
    def generate_scenario(self, scenario: str, days: int = 14, interval_minutes: int = 30) -> pd.DataFrame:
        records = []
        start_time = datetime.now() - timedelta(days=days)
        current_time = start_time
        total_minutes = days * 24 * 60
        
        while current_time < datetime.now():
            hour = current_time.hour
            load_factor = self._get_load_factor(hour)
            
            elapsed = (current_time - start_time).total_seconds() / 60
            progress = elapsed / total_minutes
            
            day_num = int(elapsed / (24 * 60))
            record = self._generate_record(current_time, load_factor, progress, day_num, scenario)
            records.append(record)
            current_time += timedelta(minutes=interval_minutes)
        
        return pd.DataFrame(records)
    
    def _get_load_factor(self, hour: int) -> float:
        if 0 <= hour < 6:
            return 0.3 + random.uniform(0, 0.1)
        elif 6 <= hour < 9:
            return 0.4 + (hour - 6) * 0.15 + random.uniform(-0.05, 0.05)
        elif 9 <= hour < 18:
            return 0.75 + random.uniform(-0.1, 0.15)
        elif 18 <= hour < 22:
            return 0.6 - (hour - 18) * 0.08 + random.uniform(-0.05, 0.05)
        else:
            return 0.35 + random.uniform(0, 0.1)
    
    def _generate_record(self, timestamp: datetime, load_factor: float, progress: float, day: int, scenario: str = None) -> Dict:
        b = self.baseline
        
        chw_supply = b["chw_supply_temp"] + random.gauss(0, 0.2)
        delta_t = (b["chw_return_temp"] - b["chw_supply_temp"]) * load_factor * 0.9
        delta_t = max(delta_t, 2.0) + random.gauss(0, 0.3)
        chw_return = chw_supply + delta_t
        
        cdw_inlet = b["cdw_inlet_temp"] + random.gauss(0, 0.5)
        cdw_outlet = cdw_inlet + 5.0 + random.gauss(0, 0.3)
        
        power = b["power_kw"] * (load_factor / 0.8) + random.gauss(0, 5)
        power = max(50, power)
        
        vibration = b["vibration_rms"] + random.gauss(0, 0.2)
        vibration = max(0.5, vibration)
        
        current_base = b["current_r"] * (load_factor / 0.8)
        current_r = current_base * (1 + random.gauss(0, 0.01))
        current_y = current_base * (1 + random.gauss(0, 0.01))
        current_b = current_base * (1 + random.gauss(0, 0.01))
        
        approach = 3.0 + random.gauss(0, 0.2)
        
        if scenario == "tube_fouling":
            approach = 2.5 + 4.5 * (progress ** 1.3) + random.gauss(0, 0.2)
            cdw_outlet += 3.0 * progress
            power *= (1 + 0.15 * progress)
        elif scenario == "bearing_wear":
            vibration = 2.0 + 10.0 * (progress ** 2) + random.gauss(0, 0.3)
        elif scenario == "refrigerant_leak":
            power *= (1 + 0.25 * progress)
            delta_t = max(2.0, delta_t - 2.0 * progress)
        elif scenario == "electrical_issue":
            imbalance_factor = 0.15 * progress
            current_r *= (1 + imbalance_factor)
            current_y *= (1 - imbalance_factor * 0.5)
        elif scenario == "post_maintenance":
            if day == 0:
                vibration = 7.0 + random.gauss(0, 0.5)
            else:
                vibration = 7.0 + 0.5 * day + random.gauss(0, 0.3)
        
        calc = PhysicsCalculator()
        kw_per_ton = calc.calculate_kw_per_ton(power, delta_t, b["chw_flow_gpm"])
        phase_imbalance = calc.calculate_phase_imbalance(current_r, current_y, current_b)
        cop = calc.calculate_cop(delta_t, power, b["chw_flow_gpm"])
        
        health_engine = HealthScoreEngine()
        health_result = health_engine.calculate({
            "vibration_rms": vibration,
            "approach_temp": approach,
            "phase_imbalance": phase_imbalance,
            "kw_per_ton": kw_per_ton,
            "delta_t": delta_t
        })
        
        return {
            "timestamp": timestamp,
            "asset_id": self.asset_id,
            "chw_supply_temp": round(chw_supply, 2),
            "chw_return_temp": round(chw_return, 2),
            "cdw_inlet_temp": round(cdw_inlet, 2),
            "cdw_outlet_temp": round(cdw_outlet, 2),
            "delta_t": round(delta_t, 2),
            "approach_temp": round(approach, 2),
            "vibration_rms": round(vibration, 2),
            "power_kw": round(power, 1),
            "current_r": round(current_r, 1),
            "current_y": round(current_y, 1),
            "current_b": round(current_b, 1),
            "load_percent": round(load_factor * 100, 1),
            "kw_per_ton": round(kw_per_ton, 3),
            "phase_imbalance": round(phase_imbalance, 2),
            "cop": round(cop, 2),
            "health_score": round(health_result["overall_score"], 1),
            "health_category": health_result["category"],
        }

# =============================================
# VISUALIZATION FUNCTIONS
# =============================================

def get_health_color(score: float) -> str:
    if score >= 90:
        return "#10B981"
    elif score >= 75:
        return "#34D399"
    elif score >= 55:
        return "#FBBF24"
    elif score >= 30:
        return "#F97316"
    else:
        return "#EF4444"

def get_health_emoji(score: float) -> str:
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

def create_gauge_chart(score: float) -> go.Figure:
    color = get_health_color(score)
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        title={"text": "Health Score", "font": {"size": 20, "color": "white"}},
        number={"font": {"size": 50, "color": "white"}},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": "white", "tickfont": {"color": "white"}},
            "bar": {"color": color, "thickness": 0.75},
            "bgcolor": "#1F2937",
            "borderwidth": 2,
            "bordercolor": "#374151",
            "steps": [
                {"range": [0, 30], "color": "rgba(239, 68, 68, 0.3)"},
                {"range": [30, 55], "color": "rgba(249, 115, 22, 0.3)"},
                {"range": [55, 75], "color": "rgba(251, 191, 36, 0.3)"},
                {"range": [75, 90], "color": "rgba(52, 211, 153, 0.3)"},
                {"range": [90, 100], "color": "rgba(16, 185, 129, 0.3)"},
            ],
        }
    ))
    
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "white"},
        height=250,
        margin={"l": 20, "r": 20, "t": 50, "b": 20}
    )
    
    return fig

def create_trend_chart(df: pd.DataFrame, y_col: str, title: str, color: str = "#3B82F6") -> go.Figure:
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df["timestamp"],
        y=df[y_col],
        mode="lines",
        name=title,
        line={"color": color, "width": 2},
        fill="tozeroy",
        fillcolor=f"rgba{tuple(list(int(color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)) + [0.1])}"
    ))
    
    fig.update_layout(
        title={"text": title, "font": {"color": "white", "size": 14}},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "white"},
        height=300,
        margin={"l": 40, "r": 20, "t": 40, "b": 40},
        xaxis={"gridcolor": "#374151", "showgrid": True},
        yaxis={"gridcolor": "#374151", "showgrid": True},
        showlegend=False
    )
    
    return fig

def create_health_trend_chart(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    
    fig.add_hrect(y0=90, y1=100, fillcolor="#10B981", opacity=0.1, line_width=0)
    fig.add_hrect(y0=75, y1=90, fillcolor="#34D399", opacity=0.1, line_width=0)
    fig.add_hrect(y0=55, y1=75, fillcolor="#FBBF24", opacity=0.1, line_width=0)
    fig.add_hrect(y0=30, y1=55, fillcolor="#F97316", opacity=0.1, line_width=0)
    fig.add_hrect(y0=0, y1=30, fillcolor="#EF4444", opacity=0.1, line_width=0)
    
    colors = [get_health_color(s) for s in df["health_score"]]
    
    fig.add_trace(go.Scatter(
        x=df["timestamp"],
        y=df["health_score"],
        mode="lines+markers",
        name="Health Score",
        line={"color": "#3B82F6", "width": 2},
        marker={"size": 4, "color": colors}
    ))
    
    fig.update_layout(
        title={"text": "Health Score Trend", "font": {"color": "white", "size": 16}},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "white"},
        height=350,
        margin={"l": 40, "r": 20, "t": 50, "b": 40},
        xaxis={"gridcolor": "#374151", "showgrid": True},
        yaxis={"gridcolor": "#374151", "showgrid": True, "range": [0, 105]},
        showlegend=False
    )
    
    return fig

def create_breakdown_chart(breakdown: List[Dict]) -> go.Figure:
    metrics = [b["metric"].replace("_", " ").title() for b in breakdown]
    scores = [b["score"] for b in breakdown]
    colors = [get_health_color(s) for s in scores]
    
    fig = go.Figure(go.Bar(
        y=metrics,
        x=scores,
        orientation="h",
        marker_color=colors,
        text=[f"{s:.0f}" for s in scores],
        textposition="auto"
    ))
    
    fig.add_vline(x=70, line_dash="dash", line_color="#6B7280")
    
    fig.update_layout(
        title={"text": "Health Breakdown", "font": {"color": "white", "size": 14}},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "white"},
        height=250,
        margin={"l": 100, "r": 20, "t": 40, "b": 40},
        xaxis={"range": [0, 105], "gridcolor": "#374151"},
        yaxis={"gridcolor": "#374151"},
        showlegend=False
    )
    
    return fig

# =============================================
# MAIN APPLICATION
# =============================================

def main():
    # Initialize session state
    if "data" not in st.session_state:
        st.session_state.data = None
    if "scenario" not in st.session_state:
        st.session_state.scenario = "healthy"
    
    # Sidebar
    with st.sidebar:
        st.title("🏭 MEP Digital Twin")
        st.markdown("---")
        
        st.subheader("📊 Data Generation")
        
        scenario = st.selectbox(
            "Select Scenario",
            options=["healthy", "tube_fouling", "bearing_wear", "refrigerant_leak", "electrical_issue", "post_maintenance"],
            format_func=lambda x: {
                "healthy": "✅ Healthy Operation",
                "tube_fouling": "🔴 Tube Fouling",
                "bearing_wear": "⚙️ Bearing Wear",
                "refrigerant_leak": "❄️ Refrigerant Leak",
                "electrical_issue": "⚡ Electrical Issue",
                "post_maintenance": "🔧 Post-Maintenance Misalignment"
            }.get(x, x)
        )
        
        days = st.slider("Duration (days)", 7, 30, 14)
        
        if st.button("🚀 Generate Data", use_container_width=True, type="primary"):
            with st.spinner("Generating data..."):
                generator = ChillerDataGenerator()
                if scenario == "healthy":
                    st.session_state.data = generator.generate_healthy(days=days)
                else:
                    st.session_state.data = generator.generate_scenario(scenario, days=days)
                st.session_state.scenario = scenario
            st.success(f"Generated {len(st.session_state.data)} readings!")
        
        st.markdown("---")
        
        st.subheader("ℹ️ Scenarios")
        st.markdown("""
        - **Healthy**: Normal operation
        - **Tube Fouling**: Condenser degradation
        - **Bearing Wear**: Mechanical failure
        - **Refrigerant Leak**: Efficiency loss
        - **Electrical Issue**: Phase imbalance
        - **Post-Maintenance**: Vibration spike
        """)
        
        st.markdown("---")
        st.markdown("### 💡 About")
        st.markdown("""
        This demo shows physics-based
        predictive maintenance for
        chiller systems.
        
        [View on GitHub](https://github.com)
        """)
    
    # Main content
    st.title("📊 Physics-Aware Chiller Monitoring")
    
    if st.session_state.data is None:
        st.info("👈 Click **'Generate Data'** in the sidebar to start!")
        
        st.markdown("---")
        st.markdown("## 🎯 What This Demo Shows")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            ### 🔬 Physics-Based Analysis
            - **Approach Temperature**: Detects condenser fouling
            - **kW/Ton**: Measures energy efficiency
            - **Vibration**: Catches mechanical issues
            - **Phase Imbalance**: Monitors electrical health
            """)
        
        with col2:
            st.markdown("""
            ### 💰 Business Value
            - Early detection saves **$50,000-$150,000+** annually
            - Prevents catastrophic failures
            - Extends equipment life by **20-40%**
            - Reduces energy waste by **10-30%**
            """)
        
        st.markdown("---")
        st.markdown("## 🧪 Try These Scenarios")
        
        scenarios_info = {
            "Tube Fouling": "Watch approach temperature rise and health score drop over time",
            "Bearing Wear": "See vibration increase gradually, indicating mechanical degradation",
            "Refrigerant Leak": "Observe efficiency (kW/Ton) getting worse",
            "Electrical Issue": "Notice phase imbalance increasing, risking motor damage",
        }
        
        for name, desc in scenarios_info.items():
            st.markdown(f"**{name}**: {desc}")
        
        return
    
    # Dashboard with data
    df = st.session_state.data
    latest = df.iloc[-1]
    
    # Top metrics row
    st.markdown("### 📈 Current Status")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        score = latest["health_score"]
        emoji = get_health_emoji(score)
        st.metric("Health Score", f"{emoji} {score:.1f}")
    
    with col2:
        st.metric("Approach Temp", f"{latest['approach_temp']:.1f} °C")
    
    with col3:
        st.metric("kW/Ton", f"{latest['kw_per_ton']:.2f}")
    
    with col4:
        st.metric("Vibration", f"{latest['vibration_rms']:.1f} mm/s")
    
    with col5:
        st.metric("Load", f"{latest['load_percent']:.0f}%")
    
    st.markdown("---")
    
    # Health gauge and breakdown
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.plotly_chart(create_gauge_chart(latest["health_score"]), use_container_width=True)
        
        category = latest["health_category"].upper()
        color = get_health_color(latest["health_score"])
        st.markdown(f"<h3 style='text-align: center; color: {color};'>{category}</h3>", unsafe_allow_html=True)
    
    with col2:
        engine = HealthScoreEngine()
        health_result = engine.calculate({
            "vibration_rms": latest["vibration_rms"],
            "approach_temp": latest["approach_temp"],
            "phase_imbalance": latest["phase_imbalance"],
            "kw_per_ton": latest["kw_per_ton"],
            "delta_t": latest["delta_t"]
        })
        st.plotly_chart(create_breakdown_chart(health_result["breakdown"]), use_container_width=True)
    
    st.markdown("---")
    
    # Trend charts
    st.markdown("### 📊 Trends")
    
    tab1, tab2, tab3, tab4 = st.tabs(["Health Score", "Efficiency", "Mechanical", "Thermal"])
    
    with tab1:
        st.plotly_chart(create_health_trend_chart(df), use_container_width=True)
    
    with tab2:
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(create_trend_chart(df, "kw_per_ton", "kW/Ton (Efficiency)", "#10B981"), use_container_width=True)
        with col2:
            st.plotly_chart(create_trend_chart(df, "cop", "COP", "#3B82F6"), use_container_width=True)
    
    with tab3:
        st.plotly_chart(create_trend_chart(df, "vibration_rms", "Vibration RMS (mm/s)", "#EF4444"), use_container_width=True)
    
    with tab4:
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(create_trend_chart(df, "approach_temp", "Approach Temperature (°C)", "#F97316"), use_container_width=True)
        with col2:
            st.plotly_chart(create_trend_chart(df, "delta_t", "Delta-T (°C)", "#8B5CF6"), use_container_width=True)
    
    st.markdown("---")
    
    # Recommendations
    if health_result["primary_concern"]:
        st.markdown("### ⚠️ Recommendations")
        
        concern = health_result["primary_concern"]
        recommendations = {
            "vibration_rms": [
                "Schedule vibration analysis",
                "Check bearing condition",
                "Inspect coupling alignment",
                "Review maintenance history"
            ],
            "approach_temp": [
                "Schedule condenser tube cleaning",
                "Check condenser water flow",
                "Verify cooling tower performance",
                "Check refrigerant charge"
            ],
            "phase_imbalance": [
                "Check electrical connections",
                "Verify power supply quality",
                "Inspect motor terminals",
                "Check for loose wiring"
            ],
            "kw_per_ton": [
                "Review operating efficiency",
                "Check for system issues",
                "Verify sensor calibration",
                "Compare to design specs"
            ]
        }
        
        recs = recommendations.get(concern, ["Monitor closely"])
        
        for i, rec in enumerate(recs, 1):
            st.warning(f"{i}. {rec}")
    else:
        st.success("✅ All systems operating normally. No immediate action required.")
    
    st.markdown("---")
    
    # Data table
    with st.expander("📋 View Raw Data"):
        st.dataframe(df.tail(50), use_container_width=True)

if __name__ == "__main__":
    main()
