from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy import text
import logging

from .config import settings

logger = logging.getLogger(__name__)

# Database connection parameters
DATABASE_URL = settings.database_url
DB_SCHEMA = settings.db_schema

# Create SQLAlchemy engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,  # Maximum number of connections in the pool
    max_overflow=20,  # Maximum number of connections that can be created beyond pool_size
    pool_timeout=30,  # Timeout for getting a connection from the pool
    pool_recycle=3600,  # Recycle connections after 1 hour
    echo=False  # Set to True for SQL query logging in development
)

# Create SessionLocal factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class for models
Base = declarative_base(metadata=MetaData(schema=DB_SCHEMA))

def get_db() -> Session:
    """
    Dependency to get database session.
    Automatically closes the session after the request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """
    Initialize the database:
    1. Create schema if DB_SCHEMA != 'public'
    2. Import all models to ensure they are registered with Base
    3. Create all tables using Base.metadata.create_all()
    4. Optionally apply migrations
    """
    logger.info("Initializing database...")

    # Create database connection to check/create schema
    with engine.connect() as conn:
        # Create schema if it doesn't exist and is not 'public'
        if DB_SCHEMA != "public":
            logger.info(f"Creating schema '{DB_SCHEMA}' if it doesn't exist...")
            conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {DB_SCHEMA}"))
            conn.commit()
            logger.info(f"Schema '{DB_SCHEMA}' ready")

        # Set search_path to our schema
        if DB_SCHEMA != "public":
            conn.execute(text(f"SET search_path TO {DB_SCHEMA}, public"))
            conn.commit()

    # Import all models to register them with Base
    # This must be done before calling create_all()
    try:
        # Models are now imported in app/models/__init__.py
        # Just import the module to trigger the imports
        import app.models
        logger.info("Models imported successfully")
    except ImportError as e:
        logger.warning(f"Could not import all models: {e}. This might be expected during initial setup.")

    # Create all tables
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine, checkfirst=True)
    logger.info("Database tables created successfully")

    logger.info("Database initialization completed")

def create_database_schema():
    """
    Create the database schema if it doesn't exist.
    This is separate from init_db() for cases where you only want to create the schema.
    """
    with engine.connect() as conn:
        if DB_SCHEMA != "public":
            logger.info(f"Creating schema '{DB_SCHEMA}'...")
            conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {DB_SCHEMA}"))
            conn.commit()
            logger.info(f"Schema '{DB_SCHEMA}' created")

def test_connection():
    """
    Test database connection
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection test successful")
        return True
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False
