-- ===========================================
-- MEP Digital Twin - Database Initialization
-- ===========================================
-- This script runs automatically when TimescaleDB container starts
-- It creates all necessary tables, hypertables, and indexes

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- =========================================
-- Main Sensor Data Table (Hypertable)
-- =========================================
CREATE TABLE IF NOT EXISTS sensor_data (
    -- Timestamp (primary time column for hypertable)
    time TIMESTAMPTZ NOT NULL,
    
    -- Asset identification
    asset_id VARCHAR(50) NOT NULL,
    
    -- Thermal sensors (°C)
    chw_supply_temp DOUBLE PRECISION,      -- Chilled water supply
    chw_return_temp DOUBLE PRECISION,      -- Chilled water return
    cdw_inlet_temp DOUBLE PRECISION,       -- Condenser water inlet
    cdw_outlet_temp DOUBLE PRECISION,      -- Condenser water outlet
    ambient_temp DOUBLE PRECISION,         -- Ambient temperature
    
    -- Mechanical sensors
    vibration_rms DOUBLE PRECISION,        -- Vibration RMS (mm/s)
    vibration_freq DOUBLE PRECISION,       -- Dominant frequency (Hz)
    runtime_hours DOUBLE PRECISION,        -- Total runtime hours
    start_stop_cycles INTEGER,             -- Daily start/stop count
    
    -- Electrical sensors
    current_r DOUBLE PRECISION,            -- R-phase current (A)
    current_y DOUBLE PRECISION,            -- Y-phase current (A)
    current_b DOUBLE PRECISION,            -- B-phase current (A)
    power_kw DOUBLE PRECISION,             -- Power consumption (kW)
    
    -- Operational parameters
    load_percent DOUBLE PRECISION,         -- Load percentage (0-100)
    operating_mode VARCHAR(20),            -- AUTO/MANUAL/STANDBY
    alarm_status INTEGER,                  -- 0=normal, 1=alarm
    chw_flow_gpm DOUBLE PRECISION,         -- Chilled water flow (GPM)
    
    -- Derived metrics (calculated during ingestion)
    delta_t DOUBLE PRECISION,              -- CHW temperature differential
    kw_per_ton DOUBLE PRECISION,           -- Efficiency metric
    approach_temp DOUBLE PRECISION,        -- Condenser approach
    phase_imbalance DOUBLE PRECISION,      -- Electrical imbalance (%)
    cooling_tons DOUBLE PRECISION,         -- Calculated cooling capacity
    cop DOUBLE PRECISION,                  -- Coefficient of Performance
    
    -- Validation metadata
    validation_status VARCHAR(20),         -- accepted/accepted_with_warnings/rejected
    validation_warnings JSONB,             -- Array of warning details
    
    -- Health scoring
    health_score DOUBLE PRECISION,         -- Overall health (0-100)
    health_breakdown JSONB                 -- Per-metric breakdown
);

-- Convert to TimescaleDB hypertable
-- Partitions data by time for efficient time-series queries
SELECT create_hypertable('sensor_data', 'time', 
    if_not_exists => TRUE,
    chunk_time_interval => INTERVAL '1 day'
);

-- =========================================
-- Indexes for Common Query Patterns
-- =========================================

-- Query by asset and time (most common)
CREATE INDEX IF NOT EXISTS idx_sensor_data_asset_time 
    ON sensor_data (asset_id, time DESC);

-- Query by health score (find unhealthy assets)
CREATE INDEX IF NOT EXISTS idx_sensor_data_health 
    ON sensor_data (asset_id, health_score, time DESC);

-- Query by validation status (find rejected data)
CREATE INDEX IF NOT EXISTS idx_sensor_data_validation 
    ON sensor_data (validation_status, time DESC);

-- =========================================
-- Continuous Aggregate for Hourly Stats
-- =========================================
-- Pre-computed hourly statistics for faster dashboard queries

CREATE MATERIALIZED VIEW IF NOT EXISTS sensor_hourly
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('1 hour', time) AS bucket,
    asset_id,
    
    -- Temperature averages
    AVG(chw_supply_temp) AS avg_chw_supply_temp,
    AVG(chw_return_temp) AS avg_chw_return_temp,
    AVG(cdw_inlet_temp) AS avg_cdw_inlet_temp,
    AVG(cdw_outlet_temp) AS avg_cdw_outlet_temp,
    AVG(ambient_temp) AS avg_ambient_temp,
    
    -- Derived metrics
    AVG(delta_t) AS avg_delta_t,
    AVG(approach_temp) AS avg_approach_temp,
    AVG(kw_per_ton) AS avg_kw_per_ton,
    AVG(cop) AS avg_cop,
    
    -- Mechanical
    AVG(vibration_rms) AS avg_vibration_rms,
    MAX(vibration_rms) AS max_vibration_rms,
    
    -- Electrical
    AVG(power_kw) AS avg_power_kw,
    MAX(power_kw) AS max_power_kw,
    AVG(phase_imbalance) AS avg_phase_imbalance,
    MAX(phase_imbalance) AS max_phase_imbalance,
    
    -- Operational
    AVG(load_percent) AS avg_load_percent,
    
    -- Health
    AVG(health_score) AS avg_health_score,
    MIN(health_score) AS min_health_score,
    MAX(health_score) AS max_health_score,
    
    -- Count of readings
    COUNT(*) AS reading_count
    
FROM sensor_data
GROUP BY bucket, asset_id
WITH NO DATA;

-- Refresh policy: update hourly aggregate every hour
SELECT add_continuous_aggregate_policy('sensor_hourly',
    start_offset => INTERVAL '3 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);

-- =========================================
-- Daily Summary View
-- =========================================
CREATE MATERIALIZED VIEW IF NOT EXISTS sensor_daily
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('1 day', time) AS bucket,
    asset_id,
    
    -- Daily averages
    AVG(approach_temp) AS avg_approach_temp,
    AVG(kw_per_ton) AS avg_kw_per_ton,
    AVG(vibration_rms) AS avg_vibration_rms,
    AVG(health_score) AS avg_health_score,
    
    -- Daily extremes
    MIN(health_score) AS min_health_score,
    MAX(vibration_rms) AS max_vibration_rms,
    MAX(approach_temp) AS max_approach_temp,
    
    -- Operational stats
    AVG(load_percent) AS avg_load_percent,
    SUM(power_kw) / COUNT(*) * 24 AS estimated_daily_kwh,
    
    COUNT(*) AS reading_count
    
FROM sensor_data
GROUP BY bucket, asset_id
WITH NO DATA;

SELECT add_continuous_aggregate_policy('sensor_daily',
    start_offset => INTERVAL '3 days',
    end_offset => INTERVAL '1 day',
    schedule_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- =========================================
-- Assets Table (Metadata)
-- =========================================
CREATE TABLE IF NOT EXISTS assets (
    asset_id VARCHAR(50) PRIMARY KEY,
    asset_name VARCHAR(100) NOT NULL,
    asset_type VARCHAR(50) NOT NULL,
    location VARCHAR(100),
    manufacturer VARCHAR(100),
    model VARCHAR(100),
    serial_number VARCHAR(100),
    capacity_tons DOUBLE PRECISION,
    install_date DATE,
    last_maintenance DATE,
    next_maintenance DATE,
    status VARCHAR(20) DEFAULT 'active',
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert default demo asset
INSERT INTO assets (
    asset_id, 
    asset_name, 
    asset_type, 
    location, 
    manufacturer, 
    model, 
    capacity_tons,
    install_date
) VALUES (
    'CH-001', 
    'Chiller Unit 1', 
    'Water-Cooled Centrifugal Chiller', 
    'Central Plant Room A',
    'Carrier',
    '19XR',
    500,
    '2020-01-15'
) ON CONFLICT (asset_id) DO NOTHING;

-- =========================================
-- Alerts Table
-- =========================================
CREATE TABLE IF NOT EXISTS alerts (
    id SERIAL PRIMARY KEY,
    time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    asset_id VARCHAR(50) NOT NULL REFERENCES assets(asset_id),
    
    -- Alert classification
    alert_type VARCHAR(50) NOT NULL,       -- health_degradation, threshold_breach, etc.
    severity VARCHAR(20) NOT NULL,          -- info, warning, critical
    
    -- Alert details
    message TEXT NOT NULL,
    metric_name VARCHAR(50),
    metric_value DOUBLE PRECISION,
    threshold_value DOUBLE PRECISION,
    
    -- Recommendations
    recommendations JSONB,
    
    -- Status tracking
    acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_by VARCHAR(100),
    acknowledged_at TIMESTAMPTZ,
    resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMPTZ,
    resolution_notes TEXT,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for alerts
CREATE INDEX IF NOT EXISTS idx_alerts_asset_time 
    ON alerts (asset_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_unresolved 
    ON alerts (asset_id, resolved, severity, time DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_severity 
    ON alerts (severity, time DESC) WHERE NOT resolved;

-- =========================================
-- Latest Readings View
-- =========================================
-- Quick access to most recent reading per asset
CREATE OR REPLACE VIEW latest_readings AS
SELECT DISTINCT ON (asset_id) *
FROM sensor_data
ORDER BY asset_id, time DESC;

-- =========================================
-- Health Summary View
-- =========================================
CREATE OR REPLACE VIEW health_summary AS
SELECT 
    s.asset_id,
    a.asset_name,
    a.asset_type,
    a.location,
    s.time AS last_reading_time,
    s.health_score,
    s.health_breakdown,
    s.approach_temp,
    s.kw_per_ton,
    s.vibration_rms,
    s.phase_imbalance,
    s.load_percent,
    s.power_kw,
    CASE 
        WHEN s.health_score >= 90 THEN 'excellent'
        WHEN s.health_score >= 75 THEN 'good'
        WHEN s.health_score >= 55 THEN 'fair'
        WHEN s.health_score >= 30 THEN 'poor'
        ELSE 'critical'
    END AS health_category
FROM latest_readings s
JOIN assets a ON s.asset_id = a.asset_id;

-- =========================================
-- Data Retention Policy (Optional)
-- =========================================
-- Uncomment to automatically drop old data after 90 days
-- SELECT add_retention_policy('sensor_data', INTERVAL '90 days', if_not_exists => TRUE);

-- =========================================
-- Comments for Documentation
-- =========================================
COMMENT ON TABLE sensor_data IS 'Main time-series table for chiller sensor readings';
COMMENT ON TABLE assets IS 'Asset metadata and configuration';
COMMENT ON TABLE alerts IS 'Generated alerts from health monitoring system';
COMMENT ON VIEW latest_readings IS 'Most recent reading for each asset';
COMMENT ON VIEW health_summary IS 'Current health status summary per asset';
COMMENT ON MATERIALIZED VIEW sensor_hourly IS 'Pre-aggregated hourly statistics';
COMMENT ON MATERIALIZED VIEW sensor_daily IS 'Pre-aggregated daily statistics';

-- =========================================
-- Grant Permissions (if needed)
-- =========================================
-- GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO app_user;
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_user;

RAISE NOTICE 'MEP Digital Twin database initialized successfully!';
