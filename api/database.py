"""
Database Connection and Session Management

This module handles connections to TimescaleDB and provides
session management for the FastAPI application.

Features:
- Connection pooling
- Async support ready (for future scaling)
- Health checking
- Automatic table verification
"""

import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from contextlib import contextmanager

from sqlalchemy import create_engine, text, Column, Float, String, Integer, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

# =========================================
# Database Configuration
# =========================================

def get_database_url() -> str:
    """Get database URL from environment."""
    return os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/mep_digital_twin"
    )


# Create SQLAlchemy engine with connection pooling
engine = create_engine(
    get_database_url(),
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,  # Verify connections before use
    echo=os.getenv("SQL_ECHO", "false").lower() == "true"
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for ORM models
Base = declarative_base()


# =========================================
# Dependency for FastAPI
# =========================================

def get_db():
    """
    Dependency that provides a database session.
    
    Usage in FastAPI:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_session():
    """
    Context manager for database sessions.
    
    Usage:
        with get_db_session() as db:
            db.execute(query)
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# =========================================
# Database Operations
# =========================================

class DatabaseManager:
    """
    Manager class for database operations.
    
    Provides high-level methods for common database operations
    used by the API endpoints.
    """
    
    def __init__(self, session: Optional[Session] = None):
        """
        Initialize with optional session.
        
        Args:
            session: SQLAlchemy session (creates new if None)
        """
        self._session = session
        self._owns_session = session is None
    
    @property
    def session(self) -> Session:
        """Get or create session."""
        if self._session is None:
            self._session = SessionLocal()
        return self._session
    
    def close(self):
        """Close session if we own it."""
        if self._owns_session and self._session:
            self._session.close()
            self._session = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.session.rollback()
        self.close()
    
    # =========================================
    # Health Check Operations
    # =========================================
    
    def check_connection(self) -> bool:
        """Check if database connection is working."""
        try:
            self.session.execute(text("SELECT 1"))
            return True
        except SQLAlchemyError as e:
            logger.error(f"Database connection check failed: {e}")
            return False
    
    def get_table_info(self) -> Dict[str, Any]:
        """Get information about database tables."""
        try:
            result = self.session.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """))
            tables = [row[0] for row in result]
            
            # Check if hypertable exists
            hypertable_check = self.session.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM timescaledb_information.hypertables 
                    WHERE hypertable_name = 'sensor_data'
                )
            """))
            is_hypertable = hypertable_check.scalar()
            
            return {
                "tables": tables,
                "sensor_data_is_hypertable": is_hypertable,
                "status": "ok"
            }
        except SQLAlchemyError as e:
            logger.error(f"Failed to get table info: {e}")
            return {"status": "error", "error": str(e)}
    
    # =========================================
    # Sensor Data Operations
    # =========================================
    
    def insert_sensor_data(self, data: Dict[str, Any]) -> bool:
        """
        Insert a sensor reading into the database.
        
        Args:
            data: Dictionary containing sensor values
            
        Returns:
            True if successful
        """
        try:
            # Build column names and values dynamically
            columns = []
            values = []
            params = {}
            
            for key, value in data.items():
                if value is not None:
                    columns.append(key)
                    values.append(f":{key}")
                    params[key] = value
            
            if not columns:
                logger.warning("No data to insert")
                return False
            
            query = text(f"""
                INSERT INTO sensor_data ({', '.join(columns)})
                VALUES ({', '.join(values)})
            """)
            
            self.session.execute(query, params)
            self.session.commit()
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to insert sensor data: {e}")
            self.session.rollback()
            raise
    
    def insert_sensor_data_batch(self, readings: List[Dict[str, Any]]) -> int:
        """
        Insert multiple sensor readings.
        
        Args:
            readings: List of reading dictionaries
            
        Returns:
            Number of readings inserted
        """
        inserted = 0
        for reading in readings:
            try:
                self.insert_sensor_data(reading)
                inserted += 1
            except SQLAlchemyError as e:
                logger.warning(f"Failed to insert reading: {e}")
                continue
        return inserted
    
    def get_latest_reading(self, asset_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the most recent reading for an asset.
        
        Args:
            asset_id: Asset identifier
            
        Returns:
            Dictionary with reading data or None
        """
        try:
            result = self.session.execute(text("""
                SELECT * FROM sensor_data
                WHERE asset_id = :asset_id
                ORDER BY time DESC
                LIMIT 1
            """), {"asset_id": asset_id})
            
            row = result.fetchone()
            if row:
                return dict(row._mapping)
            return None
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get latest reading: {e}")
            return None
    
    def get_readings_range(
        self,
        asset_id: str,
        start_time: datetime,
        end_time: datetime,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Get readings within a time range.
        
        Args:
            asset_id: Asset identifier
            start_time: Start of range
            end_time: End of range
            limit: Maximum readings to return
            
        Returns:
            List of reading dictionaries
        """
        try:
            result = self.session.execute(text("""
                SELECT * FROM sensor_data
                WHERE asset_id = :asset_id
                  AND time >= :start_time
                  AND time <= :end_time
                ORDER BY time ASC
                LIMIT :limit
            """), {
                "asset_id": asset_id,
                "start_time": start_time,
                "end_time": end_time,
                "limit": limit
            })
            
            return [dict(row._mapping) for row in result]
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get readings range: {e}")
            return []
    
    def get_hourly_aggregates(
        self,
        asset_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[Dict[str, Any]]:
        """
        Get hourly aggregated data from continuous aggregate.
        
        Args:
            asset_id: Asset identifier
            start_time: Start of range
            end_time: End of range
            
        Returns:
            List of hourly aggregate dictionaries
        """
        try:
            result = self.session.execute(text("""
                SELECT * FROM sensor_hourly
                WHERE asset_id = :asset_id
                  AND bucket >= :start_time
                  AND bucket <= :end_time
                ORDER BY bucket ASC
            """), {
                "asset_id": asset_id,
                "start_time": start_time,
                "end_time": end_time
            })
            
            return [dict(row._mapping) for row in result]
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get hourly aggregates: {e}")
            return []
    
    def get_reading_count(
        self,
        asset_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> int:
        """
        Get count of readings for an asset.
        
        Args:
            asset_id: Asset identifier
            start_time: Optional start of range
            end_time: Optional end of range
            
        Returns:
            Count of readings
        """
        try:
            if start_time and end_time:
                result = self.session.execute(text("""
                    SELECT COUNT(*) FROM sensor_data
                    WHERE asset_id = :asset_id
                      AND time >= :start_time
                      AND time <= :end_time
                """), {
                    "asset_id": asset_id,
                    "start_time": start_time,
                    "end_time": end_time
                })
            else:
                result = self.session.execute(text("""
                    SELECT COUNT(*) FROM sensor_data
                    WHERE asset_id = :asset_id
                """), {"asset_id": asset_id})
            
            return result.scalar() or 0
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get reading count: {e}")
            return 0
    
    # =========================================
    # Asset Operations
    # =========================================
    
    def get_asset(self, asset_id: str) -> Optional[Dict[str, Any]]:
        """Get asset by ID."""
        try:
            result = self.session.execute(text("""
                SELECT * FROM assets
                WHERE asset_id = :asset_id
            """), {"asset_id": asset_id})
            
            row = result.fetchone()
            if row:
                return dict(row._mapping)
            return None
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get asset: {e}")
            return None
    
    def get_all_assets(self) -> List[Dict[str, Any]]:
        """Get all assets."""
        try:
            result = self.session.execute(text("""
                SELECT * FROM assets
                ORDER BY asset_id
            """))
            
            return [dict(row._mapping) for row in result]
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get assets: {e}")
            return []
    
    def create_asset(self, asset_data: Dict[str, Any]) -> bool:
        """Create a new asset."""
        try:
            self.session.execute(text("""
                INSERT INTO assets (asset_id, asset_name, asset_type, location,
                                   manufacturer, model, capacity_tons)
                VALUES (:asset_id, :asset_name, :asset_type, :location,
                       :manufacturer, :model, :capacity_tons)
                ON CONFLICT (asset_id) DO UPDATE SET
                    asset_name = EXCLUDED.asset_name,
                    asset_type = EXCLUDED.asset_type,
                    updated_at = NOW()
            """), asset_data)
            
            self.session.commit()
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to create asset: {e}")
            self.session.rollback()
            return False
    
    # =========================================
    # Alert Operations
    # =========================================
    
    def create_alert(self, alert_data: Dict[str, Any]) -> bool:
        """Create a new alert."""
        try:
            self.session.execute(text("""
                INSERT INTO alerts (asset_id, alert_type, severity, message,
                                   metric_name, metric_value, threshold_value,
                                   recommendations)
                VALUES (:asset_id, :alert_type, :severity, :message,
                       :metric_name, :metric_value, :threshold_value,
                       :recommendations)
            """), alert_data)
            
            self.session.commit()
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to create alert: {e}")
            self.session.rollback()
            return False
    
    def get_active_alerts(self, asset_id: str) -> List[Dict[str, Any]]:
        """Get unresolved alerts for an asset."""
        try:
            result = self.session.execute(text("""
                SELECT * FROM alerts
                WHERE asset_id = :asset_id
                  AND resolved = FALSE
                ORDER BY time DESC
            """), {"asset_id": asset_id})
            
            return [dict(row._mapping) for row in result]
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get alerts: {e}")
            return []
    
    # =========================================
    # Cleanup Operations
    # =========================================
    
    def delete_asset_data(self, asset_id: str) -> int:
        """
        Delete all sensor data for an asset.
        
        Args:
            asset_id: Asset identifier
            
        Returns:
            Number of rows deleted
        """
        try:
            result = self.session.execute(text("""
                DELETE FROM sensor_data
                WHERE asset_id = :asset_id
            """), {"asset_id": asset_id})
            
            self.session.commit()
            return result.rowcount
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to delete asset data: {e}")
            self.session.rollback()
            return 0


# =========================================
# Utility Functions
# =========================================

def check_database_health() -> Dict[str, Any]:
    """
    Check database health and return status.
    
    Returns:
        Dictionary with health status information
    """
    try:
        with get_db_session() as db:
            # Basic connectivity
            db.execute(text("SELECT 1"))
            
            # Check TimescaleDB extension
            result = db.execute(text("""
                SELECT extversion FROM pg_extension WHERE extname = 'timescaledb'
            """))
            row = result.fetchone()
            timescale_version = row[0] if row else None
            
            # Check table exists
            result = db.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_name = 'sensor_data'
                )
            """))
            sensor_table_exists = result.scalar()
            
            return {
                "status": "healthy",
                "connected": True,
                "timescaledb_version": timescale_version,
                "sensor_table_exists": sensor_table_exists
            }
            
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "connected": False,
            "error": str(e)
        }


def init_database():
    """
    Initialize database tables if they don't exist.
    
    This is called on application startup to ensure
    the database schema is ready.
    """
    try:
        with get_db_session() as db:
            # Check if sensor_data table exists
            result = db.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_name = 'sensor_data'
                )
            """))
            
            if not result.scalar():
                logger.warning(
                    "sensor_data table not found. "
                    "Database should be initialized via init_db.sql"
                )
            else:
                logger.info("Database tables verified")
                
    except Exception as e:
        logger.error(f"Database initialization check failed: {e}")
        raise
