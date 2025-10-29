import pytest
import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.config import Settings
from app.models import User, Dependency, Folder, File, ActionLog, BackupRecord, RefreshToken

# Test database URL
TEST_DATABASE_URL = "sqlite:///./test.db"

@pytest.fixture(scope="session")
def test_settings():
    """Test settings with SQLite database"""
    return Settings(
        database_url=TEST_DATABASE_URL,
        storage_path="/tmp/test_storage",
        backup_path="/tmp/test_backups",
        jwt_secret_key="test-secret-key-for-testing-only",
        system_user_id="00000000-0000-0000-0000-000000000000"
    )

@pytest.fixture(scope="session")
def engine(test_settings):
    """Create test database engine"""
    engine = create_engine(
        test_settings.database_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    return engine

@pytest.fixture(scope="session")
def tables(engine):
    """Create all tables"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db_session(engine, tables):
    """Create test database session"""
    connection = engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection)()

    yield session

    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def client(db_session):
    """Create test client"""
    from fastapi.testclient import TestClient
    from app.main import app

    # Override the get_db dependency
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()

@pytest.fixture
def super_admin_user(db_session):
    """Create a super admin user for testing"""
    from app.core.security import get_password_hash

    user = User(
        id="test-super-admin-id",
        email="superadmin@test.com",
        full_name="Test Super Admin",
        password_hash=get_password_hash("testpassword"),
        role="SUPER_ADMIN",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def admin_dep_user(db_session):
    """Create an admin dependency user for testing"""
    from app.core.security import get_password_hash

    # Create dependency first
    dependency = Dependency(
        id="test-dependency-id",
        name="Test Dependency",
        code="TEST"
    )
    db_session.add(dependency)

    user = User(
        id="test-admin-dep-id",
        email="admindep@test.com",
        full_name="Test Admin Dep",
        password_hash=get_password_hash("testpassword"),
        role="ADMIN_DEP",
        dependency_id=dependency.id,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def worker_user(db_session, admin_dep_user):
    """Create a worker user for testing"""
    from app.core.security import get_password_hash

    user = User(
        id="test-worker-id",
        email="worker@test.com",
        full_name="Test Worker",
        password_hash=get_password_hash("testpassword"),
        role="WORKER",
        dependency_id=admin_dep_user.dependency_id,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def test_dependency(db_session):
    """Create a test dependency"""
    dependency = Dependency(
        id="test-dep-id",
        name="Test Department",
        code="TESTDEP"
    )
    db_session.add(dependency)
    db_session.commit()
    db_session.refresh(dependency)
    return dependency

@pytest.fixture
def auth_headers_super_admin(client, super_admin_user):
    """Get authentication headers for super admin"""
    response = client.post("/auth/login", json={
        "email": super_admin_user.email,
        "password": "testpassword"
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def auth_headers_admin_dep(client, admin_dep_user):
    """Get authentication headers for admin dep"""
    response = client.post("/auth/login", json={
        "email": admin_dep_user.email,
        "password": "testpassword"
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def auth_headers_worker(client, worker_user):
    """Get authentication headers for worker"""
    response = client.post("/auth/login", json={
        "email": worker_user.email,
        "password": "testpassword"
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
