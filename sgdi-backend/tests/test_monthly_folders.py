import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from sqlalchemy.orm import Session

from app.tasks.monthly_folders import create_monthly_folders_for_month
from app.core.database import SessionLocal
from app.models.dependency import Dependency
from app.models.folder import Folder
from app.models.user import User


@pytest.fixture
def db_session():
    """Database session fixture"""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def test_system_user(db_session: Session):
    """Create system user"""
    user = User(
        id="00000000-0000-0000-0000-000000000000",  # SYSTEM_USER_ID
        email="system@sgdi.local",
        full_name="System User",
        role="SUPER_ADMIN",
        password_hash="system_hash"
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def test_dependency(db_session: Session):
    """Create test dependency"""
    dep = Dependency(
        id="test-dep-id",
        name="Test Dependency",
        code="TEST"
    )
    db_session.add(dep)
    db_session.commit()
    return dep


@pytest.fixture
def test_root_folder(db_session: Session, test_dependency: Dependency):
    """Create test root folder"""
    folder = Folder(
        id="test-root-id",
        name=test_dependency.name,
        path=test_dependency.name,
        dependency_id=test_dependency.id,
        created_by="00000000-0000-0000-0000-000000000000",
        updated_by="00000000-0000-0000-0000-000000000000"
    )
    db_session.add(folder)
    db_session.commit()
    return folder


class TestMonthlyFolders:
    """Test monthly folders creation"""

    def test_create_monthly_folders_for_current_month(self, db_session, test_system_user, test_dependency, test_root_folder):
        """Test creating monthly folders for current month"""
        current_year = datetime.utcnow().year
        current_month = datetime.utcnow().month

        # Execute folder creation
        created_folders = create_monthly_folders_for_month()

        # Verify folder was created
        assert len(created_folders) == 1

        folder_data = created_folders[0]
        assert folder_data["name"] == "02d"
        assert folder_data["dependency_id"] == test_dependency.id
        assert folder_data["dependency_code"] == test_dependency.code

        # Verify folder exists in database
        folder = db_session.query(Folder).filter(
            Folder.name == folder_data["name"],
            Folder.dependency_id == test_dependency.id
        ).first()

        assert folder is not None
        assert folder.parent_id == test_root_folder.id
        assert folder.created_by == "00000000-0000-0000-0000-000000000000"

    def test_create_monthly_folders_for_specific_month(self, db_session, test_system_user, test_dependency, test_root_folder):
        """Test creating monthly folders for a specific month"""
        # Use next month
        now = datetime.utcnow()
        if now.month == 12:
            target_year = now.year + 1
            target_month = 1
        else:
            target_year = now.year
            target_month = now.month + 1

        # Execute folder creation
        created_folders = create_monthly_folders_for_month(target_year, target_month)

        # Verify folder was created
        assert len(created_folders) == 1

        folder_data = created_folders[0]
        assert folder_data["name"] == "02d"

        # Verify folder exists in database
        folder = db_session.query(Folder).filter(
            Folder.name == folder_data["name"],
            Folder.dependency_id == test_dependency.id
        ).first()

        assert folder is not None

    def test_idempotency_monthly_folders(self, db_session, test_system_user, test_dependency, test_root_folder):
        """Test that running the job multiple times doesn't create duplicate folders"""
        current_year = datetime.utcnow().year
        current_month = datetime.utcnow().month

        # Run first time
        created_folders_1 = create_monthly_folders_for_month(current_year, current_month)
        assert len(created_folders_1) == 1

        # Run second time - should be idempotent
        created_folders_2 = create_monthly_folders_for_month(current_year, current_month)
        assert len(created_folders_2) == 0  # No new folders created

        # Verify only one folder exists
        folder_count = db_session.query(Folder).filter(
            Folder.name == "02d",
            Folder.dependency_id == test_dependency.id
        ).count()

        assert folder_count == 1

    def test_concurrent_execution_simulation(self, db_session, test_system_user, test_dependency, test_root_folder):
        """Test concurrent execution handling with SELECT FOR UPDATE"""
        import threading
        import time

        results = []
        errors = []

        def run_job():
            try:
                folders = create_monthly_folders_for_month()
                results.append(folders)
            except Exception as e:
                errors.append(str(e))

        # Start multiple threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=run_job)
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Verify no errors occurred
        assert len(errors) == 0

        # Verify only one set of folders was created
        total_folders_created = sum(len(result) for result in results)
        assert total_folders_created == 1  # Only one thread should create folders

        # Verify final state
        folder_count = db_session.query(Folder).filter(
            Folder.name == "02d",
            Folder.dependency_id == test_dependency.id
        ).count()

        assert folder_count == 1

    def test_no_root_folder_dependency(self, db_session, test_system_user):
        """Test behavior when dependency has no root folder"""
        # Create dependency without root folder
        dep = Dependency(
            id="no-root-dep-id",
            name="No Root Dependency",
            code="NOROOT"
        )
        db_session.add(dep)
        db_session.commit()

        # Try to create folders
        created_folders = create_monthly_folders_for_month()

        # Should not create folders for dependencies without root folder
        no_root_folders = [f for f in created_folders if f["dependency_id"] == "no-root-dep-id"]
        assert len(no_root_folders) == 0

    def test_multiple_dependencies(self, db_session, test_system_user):
        """Test creating folders for multiple dependencies"""
        # Create another dependency with root folder
        dep2 = Dependency(
            id="test-dep2-id",
            name="Test Dependency 2",
            code="TEST2"
        )
        db_session.add(dep2)

        root2 = Folder(
            id="test-root2-id",
            name=dep2.name,
            path=dep2.name,
            dependency_id=dep2.id,
            created_by="00000000-0000-0000-0000-000000000000",
            updated_by="00000000-0000-0000-0000-000000000000"
        )
        db_session.add(root2)
        db_session.commit()

        # Create folders
        created_folders = create_monthly_folders_for_month()

        # Should create folders for both dependencies
        assert len(created_folders) == 2

        dependency_ids = {f["dependency_id"] for f in created_folders}
        assert dependency_ids == {"test-dep-id", "test-dep2-id"}
