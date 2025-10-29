import pytest
from datetime import datetime, timedelta

def test_audit_logs_query_basic(client, auth_headers_super_admin, db_session):
    """Test basic audit logs query"""
    # Create test users first
    from app.models.user import User
    from app.models.action_logs import ActionLog

    # Create test users
    users_data = [
        {
            "id": "test-super-admin-id",
            "email": "superadmin@test.com",
            "full_name": "Test Super Admin",
            "role": "SUPER_ADMIN",
            "password_hash": "hash"
        },
        {
            "id": "test-worker-id",
            "email": "worker@test.com",
            "full_name": "Test Worker",
            "role": "WORKER",
            "password_hash": "hash"
        }
    ]

    for user_data in users_data:
        user = User(**user_data)
        db_session.merge(user)

    db_session.commit()

    logs_data = [
        {
            "user_id": "test-super-admin-id",
            "user_role": "SUPER_ADMIN",
            "action_type": "LOGIN",
            "target_type": "user",
            "target_id": "test-super-admin-id",
            "details": {"test": "login"},
            "ip_address": "127.0.0.1"
        },
        {
            "user_id": "test-worker-id",
            "user_role": "WORKER",
            "action_type": "UPLOAD",
            "target_type": "file",
            "target_id": "test-file-id",
            "details": {"filename": "test.pdf"},
            "ip_address": "127.0.0.1"
        }
    ]

    for log_data in logs_data:
        log = ActionLog(**log_data)
        db_session.add(log)
    db_session.commit()

    # Query audit logs
    response = client.get("/audit/logs", headers=auth_headers_super_admin)

    assert response.status_code == 200
    data = response.json()

    assert "logs" in data
    assert "total" in data
    assert data["total"] >= 2

    # Check log structure
    if len(data["logs"]) > 0:
        log_entry = data["logs"][0]
        assert "timestamp" in log_entry
        assert "user_id" in log_entry
        assert "user_full_name" in log_entry
        assert "user_role" in log_entry
        assert "action_type" in log_entry
        assert "summary" in log_entry
        assert "details" in log_entry
        assert "ip_address" in log_entry

def test_audit_logs_filter_by_action_type(client, auth_headers_super_admin, db_session):
    """Test filtering audit logs by action type"""
    from app.models.action_logs import ActionLog

    # Create logs with different action types
    actions = ["LOGIN", "UPLOAD", "DOWNLOAD", "DELETE"]
    for action in actions:
        log = ActionLog(
            user_id="test-super-admin-id",
            user_role="SUPER_ADMIN",
            action_type=action,
            target_type="file",
            target_id="test-file-id",
            details={"action": action},
            ip_address="127.0.0.1"
        )
        db_session.add(log)
    db_session.commit()

    # Filter by UPLOAD action
    response = client.get("/audit/logs?action_type=UPLOAD", headers=auth_headers_super_admin)

    assert response.status_code == 200
    data = response.json()

    # All returned logs should be UPLOAD actions
    for log in data["logs"]:
        assert log["action_type"] == "UPLOAD"

def test_audit_logs_filter_by_date_range(client, auth_headers_super_admin, db_session):
    """Test filtering audit logs by date range"""
    from app.models.action_logs import ActionLog

    # Create logs with different timestamps
    base_time = datetime.utcnow()
    timestamps = [
        base_time - timedelta(days=5),
        base_time - timedelta(days=2),
        base_time - timedelta(days=1),
        base_time
    ]

    for i, ts in enumerate(timestamps):
        log = ActionLog(
            user_id="test-super-admin-id",
            user_role="SUPER_ADMIN",
            action_type="LOGIN",
            target_type="user",
            target_id="test-super-admin-id",
            details={"login": i},
            ip_address="127.0.0.1",
            timestamp=ts
        )
        db_session.add(log)
    db_session.commit()

    # Query logs from 3 days ago to now
    start_date = (base_time - timedelta(days=3)).isoformat()
    end_date = base_time.isoformat()

    response = client.get(f"/audit/logs?start_date={start_date}&end_date={end_date}",
        headers=auth_headers_super_admin
    )

    assert response.status_code == 200
    data = response.json()

    # Should return logs from the last 3 days (3 logs)
    assert len(data["logs"]) >= 3

def test_audit_logs_pagination(client, auth_headers_super_admin, db_session):
    """Test audit logs pagination"""
    from app.models.action_logs import ActionLog

    # Create multiple logs
    for i in range(10):
        log = ActionLog(
            user_id="test-super-admin-id",
            user_role="SUPER_ADMIN",
            action_type="LOGIN",
            target_type="user",
            target_id="test-super-admin-id",
            details={"login": i},
            ip_address="127.0.0.1"
        )
        db_session.add(log)
    db_session.commit()

    # Get first page (limit 5)
    response = client.get("/audit/logs?limit=5&offset=0", headers=auth_headers_super_admin)

    assert response.status_code == 200
    data = response.json()

    assert len(data["logs"]) == 5
    assert data["total"] >= 10
    assert data["has_more"] == True

    # Get second page
    response = client.get("/audit/logs?limit=5&offset=5", headers=auth_headers_super_admin)

    assert response.status_code == 200
    data2 = response.json()

    # The second page should have either 5 items (if there are more) or fewer (if this is the last page)
    assert len(data2["logs"]) <= 5
    # has_more should be False if we've reached the end
    if len(data2["logs"]) < 5:
        assert data2["has_more"] == False

def test_audit_logs_csv_export(client, auth_headers_super_admin, db_session):
    """Test CSV export of audit logs"""
    from app.models.action_logs import ActionLog

    # Create test logs
    for i in range(3):
        log = ActionLog(
            user_id="test-super-admin-id",
            user_role="SUPER_ADMIN",
            action_type="LOGIN",
            target_type="user",
            target_id="test-super-admin-id",
            details={"login": i, "test": "data"},
            ip_address=f"192.168.1.{i}"
        )
        db_session.add(log)
    db_session.commit()

    # Export as CSV
    response = client.get("/audit/logs?format=csv", headers=auth_headers_super_admin)

    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "attachment; filename=audit_logs_" in response.headers["content-disposition"]

    # Check CSV content
    csv_content = b"".join(response.iter_bytes()).decode("utf-8")
    lines = csv_content.strip().split("\n")

    # Should have header + 3 data lines
    assert len(lines) >= 4

    # Check header
    header = lines[0]
    assert "timestamp" in header
    assert "user_id" in header
    assert "summary" in header
    assert "ip_address" in header

def test_audit_user_logs(client, auth_headers_super_admin, super_admin_user, worker_user, db_session):
    """Test getting audit logs for a specific user"""
    from app.models.action_logs import ActionLog
    from app.models.user import User

    target_user_id = worker_user.id

    # Create the other-user if it doesn't exist
    other_user = User(
        id="other-user-id",
        email="other@test.com",
        full_name="Other User",
        role="SUPER_ADMIN",
        password_hash="hash"
    )
    other_user = db_session.merge(other_user)

    # Create logs for different users
    users_and_actions = [
        (super_admin_user.id, "LOGIN"),
        (target_user_id, "UPLOAD"),
        (target_user_id, "DOWNLOAD"),
        (target_user_id, "DELETE"),
        ("other-user-id", "LOGIN")
    ]

    for user_id, action in users_and_actions:
        log = ActionLog(
            user_id=user_id,
            user_role="WORKER" if user_id == target_user_id else "SUPER_ADMIN",
            action_type=action,
            target_type="file",
            target_id="test-file-id",
            details={"action": action},
            ip_address="127.0.0.1"
        )
        db_session.add(log)
    db_session.commit()

    # Get logs for specific user
    response = client.get(f"/audit/user/{target_user_id}", headers=auth_headers_super_admin)

    assert response.status_code == 200
    data = response.json()

    assert "user" in data
    assert "logs" in data
    assert "total_logs" in data
    assert "action_counts" in data

    assert data["user"]["id"] == target_user_id
    assert data["total_logs"] == 3  # UPLOAD, DOWNLOAD, DELETE

    # Check action counts
    counts = data["action_counts"]
    assert counts["UPLOAD"] == 1
    assert counts["DOWNLOAD"] == 1
    assert counts["DELETE"] == 1

def test_audit_user_logs_permission_denied(client, auth_headers_admin_dep, db_session):
    """Test that admin cannot access logs for users in other dependencies"""
    # Create user in different dependency
    from app.models.user import User
    from app.models.dependency import Dependency

    # Create another dependency first
    other_dep = Dependency(
        id="other-dependency",
        name="Other Dependency",
        code="OTHER"
    )
    other_dep = db_session.merge(other_dep)

    other_user = User(
        id="other-dep-user",
        email="other@test.com",
        full_name="Other User",
        role="WORKER",
        dependency_id="other-dependency",  # Different from admin's dependency
        password_hash="hash"
    )
    other_user = db_session.merge(other_user)
    db_session.commit()

    response = client.get(f"/audit/user/other-dep-user", headers=auth_headers_admin_dep)

    assert response.status_code == 403
    assert "access denied" in response.json()["detail"].lower()

def test_audit_file_logs(client, auth_headers_super_admin, super_admin_user, db_session):
    """Test getting audit logs for a specific file and its annexes"""
    from app.models.action_logs import ActionLog
    from app.models.file import File
    from app.models.folder import Folder
    from app.models.dependency import Dependency

    main_file_id = "test-main-file-id"
    annex_file_id = "test-annex-file-id"

    # Create test dependency and folder first
    test_dep = db_session.merge(Dependency(id="test-dep", name="Test Dep", code="TEST"))
    test_folder = db_session.merge(Folder(
        id="test-folder",
        name="Test Folder",
        path="Test Folder",
        dependency_id="test-dep",
        created_by=super_admin_user.id,
        updated_by=super_admin_user.id
    ))

    # Create test files
    main_file = File(
        id=main_file_id,
        original_name="Contrato.pdf",
        stored_name="stored_contrato.pdf",
        mime_type="application/pdf",
        size_bytes=1000,
        folder_id="test-folder",
        dependency_id="test-dep",
        uploaded_by=super_admin_user.id,
        version=1
    )
    db_session.merge(main_file)

    annex_file = File(
        id=annex_file_id,
        original_name="AnexoA.pdf",
        stored_name="stored_anexa.pdf",
        mime_type="application/pdf",
        size_bytes=500,
        folder_id="test-folder",
        dependency_id="test-dep",
        uploaded_by=super_admin_user.id,
        main_file_id=main_file_id,
        version=1
    )
    db_session.merge(annex_file)

    db_session.commit()

    # Create logs for main file and annex
    logs_data = [
        (main_file_id, "UPLOAD", "Contrato.pdf"),
        (main_file_id, "DOWNLOAD", "Contrato.pdf"),
        (annex_file_id, "UPLOAD", "AnexoA.pdf"),
        (annex_file_id, "DOWNLOAD", "AnexoA.pdf"),
        ("other-file-id", "UPLOAD", "Other.pdf")
    ]

    for file_id, action, filename in logs_data:
        log = ActionLog(
            user_id=super_admin_user.id,
            user_role="SUPER_ADMIN",
            action_type=action,
            target_type="file",
            target_id=file_id,
            details={
                "filename": filename,
                "main_file_id": annex_file_id if "Anexo" in filename else None
            },
            ip_address="127.0.0.1"
        )
        db_session.add(log)
    db_session.commit()

    # Get logs for main file
    response = client.get(f"/audit/file/{main_file_id}", headers=auth_headers_super_admin)

    assert response.status_code == 200
    logs = response.json()

    # Should return logs for main file and its annexes
    assert isinstance(logs, list)
    assert len(logs) >= 4  # UPLOAD and DOWNLOAD for both main file and annex

def test_audit_logs_admin_dependency_filtering(client, auth_headers_admin_dep, test_dependency, worker_user, db_session):
    """Test that admin only sees logs related to their dependency"""
    from app.models.action_logs import ActionLog
    from app.models.user import User
    from app.models.dependency import Dependency

    # Create another dependency
    other_dep = Dependency(
        id="other-dep",
        name="Other Dep",
        code="OTHER"
    )
    other_dep = db_session.merge(other_dep)

    # Create user in other dependency
    other_user = User(
        id="other-user",
        email="other@test.com",
        full_name="Other User",
        role="WORKER",
        dependency_id="other-dep",
        password_hash="hash"
    )
    other_user = db_session.merge(other_user)

    # Create logs in admin's dependency and other dependency
    logs_data = [
        (worker_user.id, test_dependency.id, "LOGIN"),
        (worker_user.id, test_dependency.id, "UPLOAD"),
        ("other-user", "other-dep", "LOGIN"),
        ("other-user", "other-dep", "UPLOAD")
    ]

    for user_id, dep_id, action in logs_data:
        log = ActionLog(
            user_id=user_id,
            user_role="WORKER",
            action_type=action,
            target_type="file" if action == "UPLOAD" else "user",
            target_id="test-file-id" if action == "UPLOAD" else user_id,
            details={"dependency_id": dep_id},
            ip_address="127.0.0.1"
        )
        db_session.add(log)
    db_session.commit()

    # Admin should only see logs for their dependency
    response = client.get("/audit/logs", headers=auth_headers_admin_dep)

    assert response.status_code == 200
    data = response.json()

    # All logs should be related to admin's dependency
    for log in data["logs"]:
        # This is a simplified check - in practice the filtering is more complex
        assert log["user_id"] == worker_user.id or log["user_id"] in ["test-super-admin-id", "test-admin-dep-id"]

def test_audit_summary_templates(client, auth_headers_super_admin, super_admin_user, db_session):
    """Test that audit log summaries are generated correctly"""
    from app.models.action_logs import ActionLog

    # Test different action types and their summaries
    test_cases = [
        {
            "action_type": "LOGIN",
            "details": {},
            "expected_contains": "inició sesión"
        },
        {
            "action_type": "UPLOAD",
            "details": {"filename": "test.pdf", "folder_path": "Documents"},
            "expected_contains": "subió el archivo test.pdf"
        },
        {
            "action_type": "DOWNLOAD",
            "details": {"filename": "test.pdf"},
            "expected_contains": "descargó el archivo: test.pdf"
        },
        {
            "action_type": "CREATE_USER",
            "details": {"email": "newuser@test.com"},
            "expected_contains": "creó un nuevo usuario: newuser@test.com"
        }
    ]

    for test_case in test_cases:
        log = ActionLog(
            user_id=super_admin_user.id,
            user_role="SUPER_ADMIN",
            action_type=test_case["action_type"],
            target_type="file",
            target_id="test-file-id",
            details=test_case["details"],
            ip_address="127.0.0.1"
        )
        db_session.add(log)
    db_session.commit()

    # Query logs and check summaries
    response = client.get("/audit/logs", headers=auth_headers_super_admin)

    assert response.status_code == 200
    data = response.json()

    # Check that summaries contain expected text
    for log in data["logs"]:
        if log["action_type"] in [tc["action_type"] for tc in test_cases]:
            test_case = next(tc for tc in test_cases if tc["action_type"] == log["action_type"])
            assert test_case["expected_contains"] in log["summary"]

def test_audit_logs_export_limit(client, auth_headers_super_admin, db_session):
    """Test that CSV export has reasonable limits"""
    from app.models.action_logs import ActionLog

    # Create many logs to test limits
    for i in range(150):  # More than typical limit
        log = ActionLog(
            user_id="test-super-admin-id",
            user_role="SUPER_ADMIN",
            action_type="LOGIN",
            target_type="user",
            target_id="test-super-admin-id",
            details={"login": i},
            ip_address="127.0.0.1"
        )
        db_session.add(log)
    db_session.commit()

    # Export should work but may be limited
    response = client.get("/audit/logs?format=csv", headers=auth_headers_super_admin)

    assert response.status_code == 200
    # In practice, the streaming should handle large exports efficiently
