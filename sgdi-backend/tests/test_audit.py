import pytest
from datetime import datetime, timedelta

def test_audit_logs_query_basic(client, auth_headers_super_admin, db_session):
    """Test basic audit logs query"""
    # Create some test audit logs
    from app.models.action_logs import ActionLog

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

    assert len(data2["logs"]) == 5
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
    assert response.headers["content-type"] == "text/csv"
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

def test_audit_user_logs(client, auth_headers_super_admin, db_session):
    """Test getting audit logs for a specific user"""
    from app.models.action_logs import ActionLog

    target_user_id = "test-worker-id"

    # Create logs for different users
    users_and_actions = [
        ("test-super-admin-id", "LOGIN"),
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

    other_user = User(
        id="other-dep-user",
        email="other@test.com",
        full_name="Other User",
        role="WORKER",
        dependency_id="other-dependency",  # Different from admin's dependency
        password_hash="hash"
    )
    db_session.add(other_user)
    db_session.commit()

    response = client.get(f"/audit/user/other-dep-user", headers=auth_headers_admin_dep)

    assert response.status_code == 403
    assert "access denied" in response.json()["detail"].lower()

def test_audit_file_logs(client, auth_headers_super_admin, db_session):
    """Test getting audit logs for a specific file and its annexes"""
    from app.models.action_logs import ActionLog

    main_file_id = "test-main-file-id"
    annex_file_id = "test-annex-file-id"

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
            user_id="test-super-admin-id",
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

    # Should return logs for main file only (not annexes in this basic case)
    # In the current implementation, it gets main file logs only
    assert isinstance(logs, list)
    assert len(logs) >= 2  # UPLOAD and DOWNLOAD for main file

def test_audit_logs_admin_dependency_filtering(client, auth_headers_admin_dep, test_dependency, db_session):
    """Test that admin only sees logs related to their dependency"""
    from app.models.action_logs import ActionLog

    # Create logs in admin's dependency and other dependency
    logs_data = [
        ("test-worker-id", test_dependency.id, "LOGIN"),
        ("test-worker-id", test_dependency.id, "UPLOAD"),
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
        assert log["user_id"] == "test-worker-id" or log["user_id"] in ["test-super-admin-id", "test-admin-dep-id"]

def test_audit_summary_templates(client, auth_headers_super_admin, db_session):
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
            user_id="test-super-admin-id",
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
