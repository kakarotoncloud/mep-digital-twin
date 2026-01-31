# 🏭 Physics-Aware MEP Digital Twin & Predictive Maintenance SaaS

<div align="center">

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-00a393.svg)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-FF4B4B.svg)](https://streamlit.io/)
[![TimescaleDB](https://img.shields.io/badge/TimescaleDB-2.x-FDB515.svg)](https://www.timescale.com/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Transform reactive maintenance into predictive intelligence for critical building systems.**

[Features](#-features) • [Quick Start](#-quick-start) • [Architecture](#-architecture) • [API Docs](#-api-documentation) • [Demo](#-demo-walkthrough)

</div>

---

## 🎯 The Problem We Solve

### The Hidden Cost of Reactive Maintenance

Modern buildings rely on complex MEP (Mechanical, Electrical, Plumbing) systems that are often maintained reactively—fixing things after they break. This approach leads to:

| Problem | Impact |
|---------|--------|
| 🔴 Unplanned Downtime | 15-20% of operating time |
| 💰 Emergency Repairs | 3-5x cost of planned maintenance |
| ⚡ Energy Waste | 10-30% inefficiency goes undetected |
| 🏭 Equipment Lifespan | Reduced by 20-40% |

### Our Solution: Physics-Informed Predictive Maintenance

This project demonstrates a **production-ready approach** to predictive maintenance that combines:

1. **First-Principles Physics** - Not just ML pattern matching, but real thermodynamic understanding
2. **Real-Time Validation** - Reject impossible data before it corrupts your analytics
3. **Explainable Health Scores** - Know exactly *why* equipment is degrading
4. **Actionable Recommendations** - Not just alerts, but what to do about them

---

## 💡 The Million-Dollar Insight: Condenser Tube Fouling

Here's a real example of how early detection saves money:

| Timeline | Approach Temperature | Status | Action |
|----------|---------------------|--------|--------|
| Week 1 | 2.5°C | ✅ Normal | Continue monitoring |
| Week 4 | 3.8°C | ⚠️ Early Warning | **WE DETECT HERE!** |
| Week 8 | 5.2°C | 🔴 Action Required | Schedule cleaning |
| Week 12 | 7.0°C | 💥 Critical | Emergency repair needed |

**Without Detection:**
- Energy waste: 15-25%
- Annual cost impact: $50,000 - $150,000+
- Risk of compressor damage

**With Our System (Detection at Week 4):**
- Simple tube cleaning: $5,000 - $15,000
- Energy saved: $40,000+/year
- Avoided emergency repairs and downtime

---

## ✨ Features

### 🛡️ Physics-Guard Validation

Our API doesn't just accept any data—it validates against physical laws:

**Example: Invalid Data (Will Be Rejected)**

Request:
```json
{
    "chw_supply_temp": 12.0,
    "chw_return_temp": 6.0
}
```

Response:
```json
{
    "status": "rejected",
    "reason": "Chilled water return must be warmer than supply",
    "recommendation": "Check sensor wiring - supply and return may be swapped"
}
```

This is physically impossible because the chilled water return temperature cannot be lower than the supply temperature - heat must flow from the building into the water.

### 📊 Explainable Health Scores

Not a black box—know exactly what's contributing to the score:

| Metric | Weight | Why It Matters |
|--------|--------|---------------|
| Vibration | 35% | Leading indicator for mechanical issues |
| Approach Temp | 25% | Heat transfer efficiency (fouling detection) |
| Phase Imbalance | 20% | Electrical health, motor protection |
| kW/Ton | 15% | Energy efficiency trending |
| Delta-T | 5% | System balance indicator |

Each metric is scored 0-100, weighted, and combined into an overall health score with full transparency into what's driving the assessment.

### 🧪 Failure Scenario Simulation

Generate realistic failure patterns for testing and demos:

| Scenario | Description | Duration | Key Indicator |
|----------|-------------|----------|---------------|
| Tube Fouling | Gradual condenser degradation | 60 days | Rising approach temp |
| Bearing Wear | Progressive mechanical failure | 45 days | Increasing vibration |
| Refrigerant Leak | Capacity and efficiency loss | 30 days | Rising kW/ton |
| Electrical Issues | Phase imbalance progression | 14 days | Current imbalance |
| Post-Maintenance Misalignment | Sudden vibration increase | 7 days | Vibration spike |

---

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose installed
- Git installed
- 4GB RAM minimum

### One-Command Setup

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/mep-digital-twin.git
cd mep-digital-twin

# 2. Copy environment file
cp .env.example .env

# 3. Launch everything
docker-compose up --build
```

### Access Points

| Service | URL | Description |
|---------|-----|-------------|
| 🎨 **Streamlit Dashboard** | http://localhost:8501 | Main visualization interface |
| 📚 **API Documentation** | http://localhost:8000/docs | Interactive Swagger UI |
| 🔍 **API Health Check** | http://localhost:8000/health | System status |

### First Steps

1. Open the Dashboard at http://localhost:8501
2. Click "Generate Demo Data" in the sidebar
3. Watch the health score respond to simulated failures
4. Explore the API docs at http://localhost:8000/docs

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                      STREAMLIT DASHBOARD                            │
│  ┌───────────┐  ┌────────────────┐  ┌──────────────────────────┐   │
│  │  Health   │  │     Trend      │  │    Scenario Simulator    │   │
│  │   Gauge   │  │    Charts      │  │    (Failure Stories)     │   │
│  └───────────┘  └────────────────┘  └──────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         FASTAPI BACKEND                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌────────────────────┐  │
│  │  POST /ingest   │  │ GET /health/:id │  │ GET /latest/:id    │  │
│  │  (with Physics  │  │ (Health Score   │  │ (Current Values)   │  │
│  │   Validation)   │  │  + Breakdown)   │  │                    │  │
│  └─────────────────┘  └─────────────────┘  └────────────────────┘  │
│                                │                                    │
│                    ┌───────────▼───────────┐                       │
│                    │    PHYSICS-GUARD      │                       │
│                    │   Validation Layer    │                       │
│                    └───────────────────────┘                       │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         TIMESCALEDB                                 │
│             Hypertable: sensor_data (time-series)                  │
│           Continuous Aggregates | Retention Policies               │
└─────────────────────────────────────────────────────────────────────┘
                                ▲
                                │
┌─────────────────────────────────────────────────────────────────────┐
│                    SYNTHETIC DATA ENGINE                            │
│  ┌──────────────┐  ┌───────────────┐  ┌─────────────────────────┐  │
│  │   Healthy    │  │  Tube Fouling │  │     Bearing Wear        │  │
│  │  Operation   │  │   Scenario    │  │       Scenario          │  │
│  └──────────────┘  └───────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
mep-digital-twin/
├── README.md                       # You are here
├── docker-compose.yml              # Container orchestration
├── Dockerfile.api                  # API container
├── Dockerfile.streamlit            # Dashboard container
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment template
│
├── core/                           # Core business logic
│   ├── __init__.py                 # Module exports
│   ├── physics.py                  # Physics calculations
│   ├── validators.py               # Physics-Guard validation
│   └── health_score.py             # Health scoring engine
│
├── engine/                         # Synthetic data generation
│   ├── __init__.py                 # Module exports
│   ├── generator.py                # Data generator
│   └── failure_scenarios.py        # Failure mode definitions
│
├── api/                            # FastAPI backend
│   ├── __init__.py                 # Module exports
│   ├── main.py                     # Application entry
│   ├── models.py                   # Pydantic schemas
│   ├── database.py                 # TimescaleDB connection
│   └── routes/                     # API endpoints
│       ├── __init__.py             # Route exports
│       ├── ingest.py               # Data ingestion
│       ├── health.py               # Health queries
│       ├── query.py                # Data queries
│       └── scenarios.py            # Scenario generation
│
├── app/                            # Streamlit dashboard
│   ├── __init__.py                 # Module exports
│   ├── dashboard.py                # Main application
│   └── components/                 # UI components
│       ├── __init__.py             # Component exports
│       ├── charts.py               # Plotly visualizations
│       ├── gauge.py                # Health gauge display
│       └── explainability.py       # Insight panels
│
├── scripts/                        # Database scripts
│   └── init_db.sql                 # Schema initialization
│
├── datasets/                       # Sample data
│   ├── sample_healthy.csv          # Healthy operation
│   ├── sample_fouling.csv          # Fouling scenario
│   └── sample_bearing.csv          # Bearing wear scenario
│
└── tests/                          # Test suite
    ├── __init__.py                 # Test configuration
    ├── test_physics.py             # Physics calculation tests
    ├── test_validators.py          # Validation tests
    └── test_health_score.py        # Health scoring tests
```

---

## 📚 API Documentation

### Core Endpoints

#### Ingest Sensor Data

**Endpoint:** `POST /api/v1/ingest`

**Example Request:**
```bash
curl -X POST http://localhost:8000/api/v1/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "asset_id": "CH-001",
    "chw_supply_temp": 6.7,
    "chw_return_temp": 12.2,
    "cdw_inlet_temp": 29.4,
    "cdw_outlet_temp": 35.0,
    "power_kw": 280,
    "vibration_rms": 2.1
  }'
```

**Example Response:**
```json
{
  "success": true,
  "message": "Data ingested successfully",
  "asset_id": "CH-001",
  "validation": {
    "is_valid": true,
    "status": "accepted"
  },
  "derived_metrics": {
    "delta_t": 5.5,
    "kw_per_ton": 0.58,
    "approach_temp": 3.0,
    "cop": 6.1
  },
  "health_score": 89.5
}
```

#### Get Health Score

**Endpoint:** `GET /api/v1/health/{asset_id}`

**Example Request:**
```bash
curl http://localhost:8000/api/v1/health/CH-001
```

**Example Response:**
```json
{
  "asset_id": "CH-001",
  "overall_score": 87.5,
  "category": "good",
  "primary_concern": null,
  "recommendations": [],
  "breakdown": [
    {
      "metric_name": "vibration_rms",
      "raw_value": 2.1,
      "normalized_score": 94.5,
      "weighted_contribution": 33.1,
      "weight": 0.35,
      "status": "excellent",
      "message": "Excellent Mechanical vibration level: 2.10 mm/s"
    },
    {
      "metric_name": "approach_temp",
      "raw_value": 2.8,
      "normalized_score": 88.0,
      "weighted_contribution": 22.0,
      "weight": 0.25,
      "status": "good",
      "message": "Good Condenser heat transfer efficiency: 2.80 C"
    }
  ]
}
```

#### Get Latest Reading

**Endpoint:** `GET /api/v1/query/latest/{asset_id}`

**Example Request:**
```bash
curl http://localhost:8000/api/v1/query/latest/CH-001
```

#### Generate Failure Scenario

**Endpoint:** `POST /api/v1/scenarios/generate`

**Example Request:**
```bash
curl -X POST http://localhost:8000/api/v1/scenarios/generate \
  -H "Content-Type: application/json" \
  -d '{
    "scenario_type": "tube_fouling",
    "duration_days": 30,
    "asset_id": "CH-001",
    "ingest": true
  }'
```

**Example Response:**
```json
{
  "success": true,
  "scenario": {
    "name": "Condenser Tube Fouling",
    "type": "tube_fouling",
    "duration_days": 30,
    "affected_metrics": ["approach_temp", "kw_per_ton", "cdw_outlet_temp"]
  },
  "readings_generated": 8640,
  "readings_ingested": 8640,
  "message": "Generated 8640 readings, ingested 8640"
}
```

#### Setup Demo Environment

**Endpoint:** `POST /api/v1/scenarios/demo/setup`

**Example Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/scenarios/demo/setup?asset_id=CH-001"
```

### Validation Endpoint

**Endpoint:** `POST /api/v1/ingest/validate`

Test data validation without storing:

```bash
curl -X POST http://localhost:8000/api/v1/ingest/validate \
  -H "Content-Type: application/json" \
  -d '{
    "chw_supply_temp": 15.0,
    "chw_return_temp": 6.0
  }'
```

### Full API Documentation

Visit http://localhost:8000/docs for interactive Swagger documentation with all endpoints.

---

## 🎮 Demo Walkthrough

### Step 1: Setup Demo Environment

```bash
curl -X POST "http://localhost:8000/api/v1/scenarios/demo/setup?asset_id=CH-001"
```

This generates 7 days of healthy data followed by 14 days of tube fouling progression.

### Step 2: View Dashboard

Open http://localhost:8501 and observe:

- Health score dropping from 90+ to below 60
- Approach temperature trending upward
- Recommendations appearing as health degrades
- Color-coded status indicators changing

### Step 3: Try Physics-Guard

Send impossible data and see it rejected:

```bash
curl -X POST http://localhost:8000/api/v1/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "asset_id": "CH-001",
    "chw_supply_temp": 15.0,
    "chw_return_temp": 6.0
  }'
```

### Step 4: Explore Different Scenarios

Available scenarios:

| Scenario Type | Description |
|--------------|-------------|
| `healthy` | Normal operation baseline |
| `tube_fouling` | Condenser degradation over time |
| `bearing_wear` | Mechanical failure progression |
| `refrigerant_leak` | Efficiency loss pattern |
| `electrical_issue` | Phase imbalance development |
| `post_maintenance_misalignment` | Sudden vibration after maintenance |

---

## 🔬 Physics Deep Dive

### Key Metrics Explained

#### Approach Temperature

**Definition:** The difference between refrigerant condensing temperature and leaving condenser water temperature.

**Formula:** `Approach = Refrigerant Saturation Temp - CDW Outlet Temp`

**What it means:**
- Lower is better (more efficient heat transfer)
- Rising approach indicates fouling, scaling, or refrigerant issues
- Each 1°C increase causes approximately 2-3% efficiency loss

**Thresholds:**

| Range | Status | Action |
|-------|--------|--------|
| < 2.0°C | Excellent | Continue monitoring |
| 2.0 - 3.0°C | Good | Normal operation |
| 3.0 - 4.5°C | Fair | Schedule inspection |
| 4.5 - 6.0°C | Poor | Plan tube cleaning |
| > 6.0°C | Critical | Immediate cleaning required |

#### kW/Ton (Efficiency)

**Definition:** Power consumed per ton of cooling produced.

**Formula:** 
```
Tons = (GPM × Delta-T × 500) / 12000
kW/Ton = Power (kW) / Tons
```

**Typical ranges:**

| Range | Status | Description |
|-------|--------|-------------|
| < 0.55 kW/ton | Excellent | High efficiency operation |
| 0.55 - 0.70 kW/ton | Good | Normal efficient operation |
| 0.70 - 0.85 kW/ton | Fair | Below optimal efficiency |
| 0.85 - 1.00 kW/ton | Poor | Significant efficiency loss |
| > 1.00 kW/ton | Critical | Major issues present |

#### Phase Imbalance

**Definition:** The percentage deviation of phase currents from the average.

**Formula:** `Imbalance = (Max Deviation from Average / Average) × 100%`

**Impact (per NEMA MG-1):**
- 1% voltage imbalance causes 6-10% current imbalance
- Motor heating increases with the square of imbalance
- Greater than 5% imbalance can reduce motor life by 50%

**Thresholds:**

| Range | Status | Action |
|-------|--------|--------|
| < 1.0% | Excellent | Normal operation |
| 1.0 - 2.0% | Good | Monitor periodically |
| 2.0 - 3.5% | Fair | Investigate power supply |
| 3.5 - 5.0% | Poor | Check connections |
| > 5.0% | Critical | Immediate electrical inspection |

#### Delta-T (Temperature Differential)

**Definition:** The temperature difference between chilled water return and supply.

**Formula:** `Delta-T = CHW Return Temp - CHW Supply Temp`

**Typical design:** 10°F (5.6°C) for comfort cooling

**Issues:**
- Too low: Possible flow issues, bypassing, or control problems
- Too high: Flow restriction or very high load
- Target: Design delta-T at current load conditions

---

## 🧪 Testing

### Run All Tests

```bash
docker-compose exec api pytest tests/ -v
```

### Run With Coverage

```bash
docker-compose exec api pytest tests/ --cov=core --cov-report=html
```

### Run Specific Test File

```bash
docker-compose exec api pytest tests/test_physics.py -v
```

### Run Specific Test Class

```bash
docker-compose exec api pytest tests/test_validators.py::TestThermalDirectionality -v
```

### Test Categories

| Test File | What It Tests |
|-----------|---------------|
| `test_physics.py` | Delta-T, kW/Ton, Approach temp, Phase imbalance, COP calculations |
| `test_validators.py` | Physics-Guard validation rules, rejection logic, warnings |
| `test_health_score.py` | Health scoring, category assignment, recommendations |

---

## ⚙️ Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://postgres:postgres@timescaledb:5432/mep_digital_twin` | TimescaleDB connection string |
| `POSTGRES_USER` | `postgres` | Database user |
| `POSTGRES_PASSWORD` | `postgres` | Database password |
| `POSTGRES_DB` | `mep_digital_twin` | Database name |
| `API_HOST` | `0.0.0.0` | API bind address |
| `API_PORT` | `8000` | API port |
| `LOG_LEVEL` | `INFO` | Logging verbosity (DEBUG, INFO, WARNING, ERROR) |
| `PHYSICS_STRICT_MODE` | `false` | If true, warnings are treated as errors |
| `STREAMLIT_SERVER_PORT` | `8501` | Dashboard port |

### Customizing Health Weights

Default weights prioritize leading indicators:

```python
default_weights = {
    "vibration_rms": 0.35,      # Mechanical health
    "approach_temp": 0.25,      # Heat transfer efficiency
    "phase_imbalance": 0.20,    # Electrical health
    "kw_per_ton": 0.15,         # Energy efficiency
    "delta_t": 0.05             # System balance
}
```

You can customize via the API or by modifying the HealthScoreEngine initialization.

---

## 🐳 Docker Commands

### Start Services

```bash
# Start all services in background
docker-compose up -d

# Start with build (after code changes)
docker-compose up --build

# Start specific service
docker-compose up api
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api
docker-compose logs -f dashboard
docker-compose logs -f timescaledb
```

### Manage Services

```bash
# Restart a service
docker-compose restart api

# Stop all services
docker-compose down

# Stop and remove volumes (clean database)
docker-compose down -v

# Check service status
docker-compose ps
```

### Access Containers

```bash
# API container shell
docker-compose exec api bash

# Database shell
docker-compose exec timescaledb psql -U postgres -d mep_digital_twin

# Run Python commands
docker-compose exec api python -c "from core.physics import PhysicsCalculator; print('OK')"
```

---

## 🔧 Troubleshooting

### Database Connection Failed

**Symptoms:** API fails to start, database connection errors

**Solutions:**
```bash
# Check if TimescaleDB is running
docker-compose ps

# View database logs
docker-compose logs timescaledb

# Restart database
docker-compose restart timescaledb

# Wait for database to be ready, then restart API
sleep 10 && docker-compose restart api
```

### API Not Responding

**Symptoms:** Cannot access http://localhost:8000

**Solutions:**
```bash
# Check API logs
docker-compose logs api

# Check if port is in use
lsof -i :8000

# Restart API
docker-compose restart api
```

### Dashboard Shows "API Disconnected"

**Symptoms:** Streamlit dashboard cannot connect to API

**Solutions:**
```bash
# Ensure API is running
curl http://localhost:8000/health

# Check network
docker network ls

# Restart both services
docker-compose restart api dashboard
```

### No Data in Dashboard

**Symptoms:** Dashboard loads but shows no data

**Solutions:**
```bash
# Generate demo data via API
curl -X POST "http://localhost:8000/api/v1/scenarios/demo/setup"

# Or click "Generate Demo Data" button in sidebar

# Check if data exists
curl http://localhost:8000/api/v1/query/latest/CH-001
```

### Tests Failing

**Symptoms:** pytest shows failures

**Solutions:**
```bash
# Run with verbose output
docker-compose exec api pytest tests/ -v --tb=long

# Run single test for debugging
docker-compose exec api pytest tests/test_physics.py::TestDeltaT -v
```

---

## 📈 Roadmap

### Phase 1: MVP (Current Release)

- [x] Physics-based validation layer (Physics-Guard)
- [x] Real-time health scoring with explanations
- [x] Synthetic data generation with failure scenarios
- [x] TimescaleDB time-series storage with hypertables
- [x] Streamlit monitoring dashboard
- [x] Failure scenario simulation (6 scenarios)
- [x] Comprehensive test suite (physics, validators, health scoring)
- [x] Docker Compose deployment
- [x] Interactive API documentation

### Phase 2: Production Hardening

- [ ] JWT authentication and authorization
- [ ] Multi-tenancy (organizations, sites, assets)
- [ ] Real-time data ingestion (MQTT, Kafka)
- [ ] Email and SMS alerting
- [ ] Audit logging for compliance
- [ ] Rate limiting and API throttling
- [ ] Database backup and recovery procedures

### Phase 3: Advanced Analytics

- [ ] Machine learning anomaly detection (complementing physics)
- [ ] SHAP-based model explainability
- [ ] Remaining Useful Life (RUL) prediction
- [ ] Maintenance scheduling optimization
- [ ] Cost impact analysis and ROI tracking
- [ ] Comparative benchmarking across assets

### Phase 4: Enterprise Scale

- [ ] Kubernetes deployment with Helm charts
- [ ] Prometheus metrics and Grafana dashboards
- [ ] React/Next.js production frontend
- [ ] Mobile application (iOS/Android)
- [ ] Multi-region deployment support
- [ ] SSO integration (SAML, OAuth)

---

## 🤝 Contributing

Contributions are welcome! Here's how to get started:

### Development Setup

```bash
# Fork and clone
git clone https://github.com/YOUR_USERNAME/mep-digital-twin.git
cd mep-digital-twin

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run tests locally
pytest tests/ -v
```

### Contribution Process

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes
4. Run tests: `pytest tests/ -v`
5. Commit: `git commit -m 'Add amazing feature'`
6. Push: `git push origin feature/amazing-feature`
7. Open a Pull Request

### Code Style

- Follow PEP 8 for Python code
- Use type hints where possible
- Write docstrings for public functions
- Add tests for new functionality

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **ASHRAE** - For chiller performance standards and guidelines
- **TimescaleDB** - For excellent time-series database and documentation
- **Streamlit** - For rapid dashboard prototyping capabilities
- **FastAPI** - For modern, fast API framework
- **Building Automation Community** - For domain knowledge and best practices

---

## 📞 Contact

- **Issues:** Open an issue on GitHub for bugs or feature requests
- **Discussions:** Use GitHub Discussions for questions and ideas

---

<div align="center">

### Built with 🔬 Physics + 💻 Code + ❤️ Passion for Building Systems

**Star ⭐ this repo if you find it useful!**

[Back to Top](#-physics-aware-mep-digital-twin--predictive-maintenance-saas)

</div>
```

---
