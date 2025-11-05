"""
Database connection and session management.
"""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from gambler_ai.storage.models import Base
from gambler_ai.utils.config import get_config


class DatabaseManager:
    """Manage database connections and sessions."""

    def __init__(self, db_type: str = "timeseries"):
        """
        Initialize database manager.

        Args:
            db_type: Type of database ('timeseries' or 'analytics')
        """
        self.config = get_config()
        self.db_type = db_type

        if db_type == "timeseries":
            self.db_url = self.config.timeseries_db_url
        elif db_type == "analytics":
            self.db_url = self.config.analytics_db_url
        else:
            raise ValueError(f"Invalid db_type: {db_type}")

        # Create engine
        self.engine = create_engine(
            self.db_url,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,  # Verify connections before using
            echo=False,  # Set to True for SQL debugging
        )

        # Create session factory
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )

    def create_tables(self):
        """Create all tables in the database."""
        Base.metadata.create_all(bind=self.engine)

    def drop_tables(self):
        """Drop all tables in the database (CAUTION!)."""
        Base.metadata.drop_all(bind=self.engine)

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Get a database session with automatic cleanup.

        Usage:
            with db_manager.get_session() as session:
                # Use session here
                session.query(...)
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def get_session_direct(self) -> Session:
        """
        Get a database session (manual management required).

        Usage:
            session = db_manager.get_session_direct()
            try:
                # Use session
                session.commit()
            finally:
                session.close()
        """
        return self.SessionLocal()


# Global database manager instances
_timeseries_db = None
_analytics_db = None


def get_timeseries_db() -> DatabaseManager:
    """Get global TimescaleDB manager instance (singleton)."""
    global _timeseries_db
    if _timeseries_db is None:
        _timeseries_db = DatabaseManager("timeseries")
    return _timeseries_db


def get_analytics_db() -> DatabaseManager:
    """Get global Analytics DB manager instance (singleton)."""
    global _analytics_db
    if _analytics_db is None:
        _analytics_db = DatabaseManager("analytics")
    return _analytics_db


def init_databases():
    """Initialize all databases by creating tables."""
    print("Initializing TimescaleDB...")
    timeseries_db = get_timeseries_db()
    timeseries_db.create_tables()
    print("✓ TimescaleDB initialized")

    print("Initializing Analytics DB...")
    analytics_db = get_analytics_db()
    analytics_db.create_tables()
    print("✓ Analytics DB initialized")

    print("\n✓ All databases initialized successfully")
