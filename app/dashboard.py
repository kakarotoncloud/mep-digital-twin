"""
MEP Digital Twin - Streamlit Dashboard

Main dashboard application for monitoring chiller health,
visualizing trends, and running failure scenarios.

Features:
- Real-time health monitoring
- Interactive trend visualization
- Failure scenario simulation
- Explainable AI insights
- Physics-Guard validation demo

Run with: streamlit run app/dashboard.py
"""

import os
import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import plotly.graph_objects as go

# Import components
from components.charts import (
    create_health_trend_chart,
    create_metric_trend_chart,
    create_multi_metric_chart,
    create_metric_comparison_chart,
    create_gauge_chart,
)
from components.gauge import (
    render_health_gauge,
    render_metric_card,
    render_status_indicator,
    render_alert_banner,
)
from components.explainability import (
    render_health_breakdown,
    render_recommendations,
    render_scenario_story,
    render_why_this_matters,
)


# =========================================
# Configuration
# =========================================

API_URL = os.getenv("API_URL", "http://localhost:8000")
DEFAULT_ASSET_ID = os.getenv("DEFAULT_ASSET_ID", "CH-001")

# Page configuration
st.set_page_config(
    page_title="MEP Digital Twin",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    /* Main container */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #F9FAFB !important;
    }
    
    /* Metrics */
    [data-testid="stMetric"] {
        background: rgba(31, 41, 55, 0.6);
        border-radius: 10px;
        padding: 15px;
        border: 1px solid #374151;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1F2937 0%, #111827 100%);
    }
    
    /* Cards */
    .stCard {
        background: rgba(31, 41, 55, 0.6);
        border-radius: 10px;
        padding: 20px;
        border: 1px solid #374151;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: rgba(31, 41, 55, 0.6);
        border-radius: 8px;
        padding: 10px 20px;
    }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(90deg, #3B82F6, #2563EB);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 10px 20px;
        font-weight: 600;
    }
    
    .stButton > button:hover {
        background: linear-gradient(90deg, #2563EB, #1D4ED8);
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background: rgba(31, 41, 55, 0.6);
        border-radius: 8px;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# =========================================
# API Helper Functions
# =========================================

@st.cache_data(ttl=30)
def fetch_api(endpoint: str) -> Optional[Dict[str, Any]]:
    """Fetch data from API with caching."""
    try:
        response = requests.get(f"{API_URL}{endpoint}", timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"API Error: {e}")
        return None


def post_api(endpoint: str, data: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
    """POST to API."""
    try:
        response = requests.post(f"{API_URL}{endpoint}", json=data, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"API Error: {e}")
        return None


def check_api_health() -> bool:
    """Check if API is available."""
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False


# =========================================
# Sidebar
# =========================================

def render_sidebar():
    """Render the sidebar with controls."""
    with st.sidebar:
        st.image("https://via.placeholder.com/200x60/1F2937/3B82F6?text=MEP+Digital+Twin", width=200)
        st.markdown("---")
        
        # API Status
        api_healthy = check_api_health()
        if api_healthy:
            st.success("🟢 API Connected")
        else:
            st.error("🔴 API Disconnected")
            st.info(f"API URL: {API_URL}")
        
        st.markdown("---")
        
        # Asset Selection
        st.subheader("🏭 Asset Selection")
        
        assets_data = fetch_api("/api/v1/query/assets")
        if assets_data and assets_data.get("assets"):
            asset_options = {a["asset_id"]: f"{a['asset_name']} ({a['asset_id']})" 
                          for a in assets_data["assets"]}
            selected_asset = st.selectbox(
                "Select Asset",
                options=list(asset_options.keys()),
                format_func=lambda x: asset_options[x],
                key="asset_selector"
            )
        else:
            selected_asset = DEFAULT_ASSET_ID
            st.text_input("Asset ID", value=DEFAULT_ASSET_ID, key="asset_selector")
        
        st.markdown("---")
        
        # Time Range
        st.subheader("📅 Time Range")
        time_range = st.selectbox(
            "Select Range",
            options=["1 Hour", "6 Hours", "24 Hours", "7 Days", "30 Days"],
            index=2,
            key="time_range"
        )
        
        time_mapping = {
            "1 Hour": 1,
            "6 Hours": 6,
            "24 Hours": 24,
            "7 Days": 168,
            "30 Days": 720,
        }
        hours = time_mapping[time_range]
        
        st.markdown("---")
        
        # Auto Refresh
        st.subheader("🔄 Auto Refresh")
        auto_refresh = st.checkbox("Enable Auto Refresh", value=False)
        if auto_refresh:
            refresh_rate = st.slider("Refresh Rate (seconds)", 10, 60, 30)
            st.info(f"Refreshing every {refresh_rate}s")
        
        st.markdown("---")
        
        # Quick Actions
        st.subheader("⚡ Quick Actions")
        
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        
        if st.button("🧪 Generate Demo Data", use_container_width=True):
            with st.spinner("Generating demo data..."):
                result = post_api(f"/api/v1/scenarios/demo/setup?asset_id={selected_asset}")
                if result and result.get("success"):
                    st.success("Demo data generated!")
                    st.cache_data.clear()
                else:
                    st.error("Failed to generate demo data")
        
        return selected_asset, hours


# =========================================
# Main Dashboard Page
# =========================================

def render_monitoring_page(asset_id: str, hours: int):
    """Render the main monitoring dashboard."""
    st.title("📊 Real-Time Monitoring")
    
    # Fetch latest data
    latest_data = fetch_api(f"/api/v1/query/latest/{asset_id}")
    health_data = fetch_api(f"/api/v1/health/{asset_id}")
    trends_data = fetch_api(f"/api/v1/query/trends/{asset_id}?hours={hours}&points=100")
    
    if not latest_data or not latest_data.get("reading"):
        render_alert_banner(
            f"No data available for asset {asset_id}. Generate demo data using the sidebar.",
            severity="warning"
        )
        return
    
    reading = latest_data["reading"]
    
    # Row 1: Health Score and Key Metrics
    col1, col2 = st.columns([1, 3])
    
    with col1:
        health_score = reading.get("health_score", 0) or 0
        render_health_gauge(health_score, "Health Score", size="large")
        
        if health_data:
            category = health_data.get("category", "unknown")
            render_status_indicator(category, size="large")
    
    with col2:
        st.markdown("### ⚡ Key Metrics")
        
        metrics_cols = st.columns(4)
        
        with metrics_cols[0]:
            render_metric_card(
                "Approach Temp",
                reading.get("approach_temp") or 0,
                "°C",
                metric_name="approach_temp",
                help_text="Condenser approach temperature"
            )
        
        with metrics_cols[1]:
            render_metric_card(
                "kW/Ton",
                reading.get("kw_per_ton") or 0,
                "",
                metric_name="kw_per_ton",
                help_text="Energy efficiency metric"
            )
        
        with metrics_cols[2]:
            render_metric_card(
                "Vibration",
                reading.get("vibration_rms") or 0,
                "mm/s",
                metric_name="vibration_rms",
                help_text="Vibration RMS velocity"
            )
        
        with metrics_cols[3]:
            render_metric_card(
                "Phase Imbalance",
                reading.get("phase_imbalance") or 0,
                "%",
                metric_name="phase_imbalance",
                help_text="Three-phase current imbalance"
            )
    
    st.markdown("---")
    
    # Row 2: Trend Charts
    st.markdown("### 📈 Trends")
    
    if trends_data and trends_data.get("metrics"):
        metrics = trends_data["metrics"]
        
        tab1, tab2, tab3, tab4 = st.tabs(["Health Score", "Efficiency", "Mechanical", "Electrical"])
        
        with tab1:
            if metrics.get("health_score", {}).get("values"):
                times = [datetime.fromisoformat(t.replace("Z", "")) for t in metrics["health_score"]["times"]]
                values = [v or 0 for v in metrics["health_score"]["values"]]
                fig = create_health_trend_chart(times, values, height=400)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No health score data available")
        
        with tab2:
            col1, col2 = st.columns(2)
            with col1:
                if metrics.get("kw_per_ton", {}).get("values"):
                    times = [datetime.fromisoformat(t.replace("Z", "")) for t in metrics["kw_per_ton"]["times"]]
                    values = [v or 0 for v in metrics["kw_per_ton"]["values"]]
                    fig = create_metric_trend_chart(
                        times, values, "kW/Ton", "",
                        thresholds={"warning": 0.85, "critical": 1.0}
                    )
                    st.plotly_chart(fig, use_container_width=True)
            with col2:
                if metrics.get("approach_temp", {}).get("values"):
                    times = [datetime.fromisoformat(t.replace("Z", "")) for t in metrics["approach_temp"]["times"]]
                    values = [v or 0 for v in metrics["approach_temp"]["values"]]
                    fig = create_metric_trend_chart(
                        times, values, "Approach Temperature", "°C",
                        thresholds={"warning": 4.5, "critical": 6.0}
                    )
                    st.plotly_chart(fig, use_container_width=True)
        
        with tab3:
            if metrics.get("vibration_rms", {}).get("values"):
                times = [datetime.fromisoformat(t.replace("Z", "")) for t in metrics["vibration_rms"]["times"]]
                values = [v or 0 for v in metrics["vibration_rms"]["values"]]
                fig = create_metric_trend_chart(
                    times, values, "Vibration RMS", "mm/s",
                    thresholds={"warning": 7.0, "critical": 11.0}
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with tab4:
            col1, col2 = st.columns(2)
            with col1:
                if metrics.get("power_kw", {}).get("values"):
                    times = [datetime.fromisoformat(t.replace("Z", "")) for t in metrics["power_kw"]["times"]]
                    values = [v or 0 for v in metrics["power_kw"]["values"]]
                    fig = create_metric_trend_chart(times, values, "Power", "kW")
                    st.plotly_chart(fig, use_container_width=True)
            with col2:
                if metrics.get("load_percent", {}).get("values"):
                    times = [datetime.fromisoformat(t.replace("Z", "")) for t in metrics["load_percent"]["times"]]
                    values = [v or 0 for v in metrics["load_percent"]["values"]]
                    fig = create_metric_trend_chart(times, values, "Load", "%")
                    st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No trend data available")
    
    st.markdown("---")
    
    # Row 3: Health Breakdown and Recommendations
    st.markdown("### 🔍 Health Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if health_data and health_data.get("breakdown"):
            render_health_breakdown(health_data["breakdown"])
        else:
            st.info("No health breakdown available")
    
    with col2:
        if health_data:
            if health_data.get("recommendations"):
                render_recommendations(health_data["recommendations"])
            else:
                st.success("✅ No immediate actions required")
            
            if health_data.get("primary_concern"):
                st.markdown("### ⚠️ Primary Concern")
                concern = health_data["primary_concern"]
                # Find the breakdown item for this concern
                breakdown = health_data.get("breakdown", [])
                concern_item = next((b for b in breakdown if b.get("metric_name") == concern), None)
                if concern_item:
                    render_why_this_matters(
                        concern,
                        concern_item.get("status", "fair"),
                        concern_item.get("raw_value", 0)
                    )


# =========================================
# Scenario Simulator Page
# =========================================

def render_scenario_page(asset_id: str):
    """Render the scenario simulation page."""
    st.title("🧪 Failure Scenario Simulator")
    
    st.markdown("""
    Generate synthetic failure scenarios to demonstrate predictive maintenance capabilities.
    Watch how health scores and metrics change as failures progress.
    """)
    
    # Fetch available scenarios
    scenarios_data = fetch_api("/api/v1/scenarios")
    
    if not scenarios_data:
        st.error("Could not fetch scenarios from API")
        return
    
    scenarios = scenarios_data.get("scenarios", [])
    
    # Scenario Selection
    col1, col2 = st.columns([2, 1])
    
    with col1:
        scenario_options = {s["type"]: s["name"] for s in scenarios}
        selected_scenario = st.selectbox(
            "Select Failure Scenario",
            options=list(scenario_options.keys()),
            format_func=lambda x: scenario_options[x]
        )
    
    with col2:
        duration = st.number_input(
            "Duration (days)",
            min_value=1,
            max_value=90,
            value=14
        )
    
    # Scenario Details
    scenario_info = next((s for s in scenarios if s["type"] == selected_scenario), None)
    
    if scenario_info:
        st.markdown("### 📋 Scenario Details")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown(f"**Type:** {scenario_info['name']}")
        with col2:
            st.markdown(f"**Default Duration:** {scenario_info['duration_days']} days")
        with col3:
            st.markdown(f"**Affected Metrics:** {', '.join(scenario_info.get('affected_metrics', []))}")
        
        st.markdown(f"**Description:** {scenario_info['description']}")
        
        # Get full story
        full_scenario = fetch_api(f"/api/v1/scenarios/{selected_scenario}")
        if full_scenario and full_scenario.get("story"):
            with st.expander("📖 View Failure Story", expanded=False):
                render_scenario_story(
                    full_scenario["name"],
                    full_scenario["story"],
                    full_scenario.get("affected_metrics"),
                    full_scenario.get("duration_days")
                )
    
    st.markdown("---")
    
    # Generate Button
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        if st.button("🚀 Generate & Ingest Scenario", use_container_width=True, type="primary"):
            with st.spinner(f"Generating {duration} days of {scenario_options[selected_scenario]} data..."):
                result = post_api("/api/v1/scenarios/generate", {
                    "scenario_type": selected_scenario,
                    "duration_days": duration,
                    "asset_id": asset_id,
                    "ingest": True,
                    "interval_minutes": 5
                })
                
                if result and result.get("success"):
                    st.success(f"✅ Generated {result.get('readings_generated', 0)} readings!")
                    st.cache_data.clear()
                    
                    # Show summary
                    st.markdown("### 📊 Generation Summary")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Readings Generated", result.get("readings_generated", 0))
                    with col2:
                        st.metric("Readings Ingested", result.get("readings_ingested", 0))
                    with col3:
                        st.metric("Duration", f"{duration} days")
                else:
                    st.error("Failed to generate scenario data")
    
    st.markdown("---")
    
    # Preview Section
    st.markdown("### 👁️ Preview Generated Data")
    
    if st.button("Preview Sample Data"):
        preview = fetch_api(f"/api/v1/scenarios/generate/{selected_scenario}/preview?days={duration}&samples=20")
        
        if preview and preview.get("sample_readings"):
            # Convert to dataframe for display
            df = pd.DataFrame(preview["sample_readings"])
            
            # Select key columns
            display_cols = ["time", "health_score", "approach_temp", "kw_per_ton", 
                          "vibration_rms", "power_kw", "load_percent"]
            display_cols = [c for c in display_cols if c in df.columns]
            
            st.dataframe(df[display_cols], use_container_width=True)


# =========================================
# Physics Guard Demo Page
# =========================================

def render_physics_guard_page():
    """Render the Physics Guard demo page."""
    st.title("🛡️ Physics-Guard Validation Demo")
    
    st.markdown("""
    The Physics-Guard validates sensor data against physical laws before accepting it.
    Try entering impossible values to see how the system rejects bad data!
    """)
    
    st.markdown("### 🧪 Test Data Validation")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### ❌ Invalid Example (Will Be Rejected)")
        st.markdown("*CHW Return < Supply (impossible - violates thermodynamics)*")
        
        if st.button("Test Invalid Data", key="invalid"):
            result = post_api("/api/v1/ingest/validate", {
                "asset_id": "CH-001",
                "chw_supply_temp": 12.0,  # Higher than return!
                "chw_return_temp": 6.0,   # Lower than supply!
                "power_kw": 280
            })
            
            if result:
                if not result.get("is_valid"):
                    st.error(f"🚫 Data REJECTED: {result.get('status')}")
                    for issue in result.get("issues", []):
                        st.warning(f"**{issue.get('rule_name')}**: {issue.get('message')}")
                        if issue.get("recommendation"):
                            st.info(f"💡 {issue.get('recommendation')}")
                else:
                    st.success("Data accepted")
    
    with col2:
        st.markdown("#### ✅ Valid Example (Will Be Accepted)")
        st.markdown("*Proper thermal direction - return > supply*")
        
        if st.button("Test Valid Data", key="valid"):
            result = post_api("/api/v1/ingest/validate", {
                "asset_id": "CH-001",
                "chw_supply_temp": 6.7,
                "chw_return_temp": 12.2,
                "cdw_inlet_temp": 29.4,
                "cdw_outlet_temp": 35.0,
                "power_kw": 280,
                "vibration_rms": 2.1
            })
            
            if result:
                if result.get("is_valid"):
                    st.success(f"✅ Data ACCEPTED: {result.get('status')}")
                    if result.get("warning_count", 0) > 0:
                        st.warning(f"With {result.get('warning_count')} warnings")
                else:
                    st.error("Data rejected")
    
    st.markdown("---")
    
    # Custom Validation
    st.markdown("### 🔧 Custom Validation Test")
    
    with st.form("validation_form"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            chw_supply = st.number_input("CHW Supply Temp (°C)", value=6.7)
            chw_return = st.number_input("CHW Return Temp (°C)", value=12.2)
        
        with col2:
            cdw_inlet = st.number_input("CDW Inlet Temp (°C)", value=29.4)
            cdw_outlet = st.number_input("CDW Outlet Temp (°C)", value=35.0)
        
        with col3:
            power = st.number_input("Power (kW)", value=280.0)
            vibration = st.number_input("Vibration RMS (mm/s)", value=2.0)
        
        submitted = st.form_submit_button("Validate Data", type="primary")
        
        if submitted:
            result = post_api("/api/v1/ingest/validate", {
                "asset_id": "CH-001",
                "chw_supply_temp": chw_supply,
                "chw_return_temp": chw_return,
                "cdw_inlet_temp": cdw_inlet,
                "cdw_outlet_temp": cdw_outlet,
                "power_kw": power,
                "vibration_rms": vibration
            })
            
            if result:
                st.markdown("#### Validation Result")
                
                status = result.get("status", "unknown")
                if status == "accepted":
                    st.success("✅ Data is physically valid and accepted!")
                elif status == "accepted_with_warnings":
                    st.warning(f"⚠️ Data accepted with {result.get('warning_count', 0)} warnings")
                else:
                    st.error(f"🚫 Data rejected with {result.get('error_count', 0)} errors")
                
                if result.get("issues"):
                    st.markdown("**Issues Found:**")
                    for issue in result["issues"]:
                        severity_emoji = {"error": "🔴", "warning": "🟡", "info": "🔵"}
                        st.markdown(f"{severity_emoji.get(issue.get('severity'), '⚪')} **{issue.get('rule_name')}**: {issue.get('message')}")


# =========================================
# About Page
# =========================================

def render_about_page():
    """Render the about page."""
    st.title("ℹ️ About MEP Digital Twin")
    
    st.markdown("""
    ## Physics-Aware Predictive Maintenance for MEP Systems
    
    This project demonstrates a production-grade approach to predictive maintenance
    for building mechanical systems, specifically water-cooled chiller plants.
    
    ### 🎯 Key Features
    
    - **Physics-Based Validation**: Sensor data is validated against thermodynamic laws
    - **Explainable Health Scores**: Understand exactly why equipment health is degrading
    - **Failure Scenario Simulation**: Generate realistic failure patterns for testing
    - **Real-Time Monitoring**: Track equipment health continuously
    
    ### 🔬 The Physics Approach
    
    Unlike pure ML approaches, this system uses first-principles physics:
    
    | Metric | What It Measures | Why It Matters |
    |--------|-----------------|----------------|
    | Approach Temp | Condenser heat transfer | Fouling detection ($$$ savings) |
    | kW/Ton | Energy efficiency | Operating cost optimization |
    | Vibration | Mechanical health | Early bearing failure detection |
    | Phase Imbalance | Electrical health | Motor protection |
    
    ### 💰 Business Value
    
    Early detection of issues like condenser fouling can save:
    - **$50,000 - $150,000+** annually in energy costs
    - **Prevent catastrophic failures** costing $200,000+
    - **Extend equipment life** by 20-40%
    
    ### 🛠️ Technology Stack
    
    - **Backend**: FastAPI + Python
    - **Database**: TimescaleDB (time-series optimized)
    - **Frontend**: Streamlit
    - **Deployment**: Docker Compose
    
    ---
    
    Built with 🔬 Physics + 💻 Code + ❤️ Passion for Building Systems
    """)


# =========================================
# Main Application
# =========================================

def main():
    """Main application entry point."""
    # Render sidebar and get selections
    asset_id, hours = render_sidebar()
    
    # Navigation
    st.sidebar.markdown("---")
    st.sidebar.subheader("📍 Navigation")
    
    page = st.sidebar.radio(
        "Go to",
        ["📊 Monitoring", "🧪 Scenario Simulator", "🛡️ Physics-Guard Demo", "ℹ️ About"],
        label_visibility="collapsed"
    )
    
    # Render selected page
    if page == "📊 Monitoring":
        render_monitoring_page(asset_id, hours)
    elif page == "🧪 Scenario Simulator":
        render_scenario_page(asset_id)
    elif page == "🛡️ Physics-Guard Demo":
        render_physics_guard_page()
    elif page == "ℹ️ About":
        render_about_page()


if __name__ == "__main__":
    main()
