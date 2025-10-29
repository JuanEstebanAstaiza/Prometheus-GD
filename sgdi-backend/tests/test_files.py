import pytest
import hashlib
from io import BytesIO
from pathlib import Path

def test_upload_main_file_only(client, auth_headers_worker, test_dependency, worker_user, db_session):
    """Test uploading a main file without annexes"""
    # Create test folder first
    from app.models.folder import Folder
    test_folder = Folder(
        id="test-upload-folder",
        name="Upload Test",
        path="Upload Test",
        dependency_id=test_dependency.id,
        created_by=worker_user.id,
        updated_by=worker_user.id
    )
    test_folder = db_session.merge(test_folder)
    db_session.commit()

    # Create test file content
    file_content = b"Test PDF content for upload"
    files = {"file": ("test.pdf", BytesIO(file_content), "application/pdf")}
    data = {"folder_id": test_folder.id}

    response = client.post("/files/upload", files=files, data=data, headers=auth_headers_worker)

    assert response.status_code == 201
    data = response.json()

    assert "main_file" in data
    assert data["main_file"]["original_name"] == "test.pdf"
    assert data["main_file"]["mime_type"] == "application/pdf"
    assert data["main_file"]["size_bytes"] == len(file_content)
    assert data["main_file"]["version"] == 1
    assert data["annex_files"] is None
    assert data["annex_folder"] is None

def test_upload_with_annexes(client, auth_headers_worker, test_dependency, worker_user, db_session):
    """Test uploading a main file with annexes"""
    # Create test folder
    from app.models.folder import Folder
    test_folder = Folder(
        id="test-annex-folder",
        name="Annex Test",
        path="Annex Test",
        dependency_id=test_dependency.id,
        created_by=worker_user.id,
        updated_by=worker_user.id
    )
    test_folder = db_session.merge(test_folder)
    db_session.commit()

    # Main file and annexes
    main_content = b"Main contract content for testing"
    annex_a_content = b"Annex A content for testing"
    annex_b_content = b"Annex B content for testing"

    files = {
        "file": ("Contrato.pdf", BytesIO(main_content), "application/pdf"),
        "anexos": [
            ("AnexoA.pdf", BytesIO(annex_a_content), "application/pdf"),
            ("AnexoB.xlsx", BytesIO(annex_b_content), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        ]
    }
    data = {"folder_id": test_folder.id}

    response = client.post("/files/upload", files=files, data=data, headers=auth_headers_worker)

    assert response.status_code == 201
    data = response.json()

    # Check main file
    assert "main_file" in data
    assert data["main_file"]["original_name"] == "Contrato.pdf"
    assert data["main_file"]["size_bytes"] == len(main_content)

    # Check annex files
    assert "annex_files" in data
    assert len(data["annex_files"]) == 2

    annex_names = [annex["original_name"] for annex in data["annex_files"]]
    assert "AnexoA.pdf" in annex_names
    assert "AnexoB.xlsx" in annex_names

    # Check annex folder
    assert "annex_folder" in data
    assert data["annex_folder"]["name"].startswith("Anexos-Contrato-")

    # Verify annex files have main_file_id set
    for annex in data["annex_files"]:
        assert annex["main_file_id"] == data["main_file"]["id"]

def test_upload_invalid_folder(client, auth_headers_worker):
    """Test upload to non-existent folder"""
    files = {"file": ("test.pdf", BytesIO(b"content"), "application/pdf")}
    data = {"folder_id": "non-existent-folder"}

    response = client.post("/files/upload", files=files, data=data, headers=auth_headers_worker)

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

def test_upload_wrong_dependency(client, auth_headers_worker, db_session):
    """Test upload to folder in different dependency"""
    # Create folder in different dependency
    from app.models.dependency import Dependency
    from app.models.folder import Folder

    other_dep = Dependency(id="other-dep", name="Other Dep", code="OTHER")
    other_dep = db_session.merge(other_dep)

    other_folder = Folder(
        id="other-folder",
        name="Other Folder",
        path="Other Folder",
        dependency_id="other-dep",
        created_by="other-user",
        updated_by="other-user"
    )
    other_folder = db_session.merge(other_folder)
    db_session.commit()

    files = {"file": ("test.pdf", BytesIO(b"content"), "application/pdf")}
    data = {"folder_id": "other-folder"}

    response = client.post("/files/upload", files=files, data=data, headers=auth_headers_worker)

    assert response.status_code == 403
    assert "dependency" in response.json()["detail"].lower()

def test_download_file_checksum_verification(client, auth_headers_worker, test_dependency, db_session):
    """Test downloading a file and verifying checksum"""
    # Create test folder
    from app.models.folder import Folder
    test_folder = Folder(
        id="test-download-folder",
        name="Download Test",
        path="Download Test",
        dependency_id=test_dependency.id,
        created_by="test-worker-id",
        updated_by="test-worker-id"
    )
    test_folder = db_session.merge(test_folder)

    # Create test file
    from app.models.file import File
    import uuid
    from app.services.storage_service import storage_service

    file_content = b"Test content for download checksum verification"
    checksum = hashlib.sha256(file_content).hexdigest()

    file_record = File(
        id=str(uuid.uuid4()),
        original_name="checksum_test.pdf",
        stored_name="stored_checksum_test.pdf",
        mime_type="application/pdf",
        size_bytes=len(file_content),
        checksum_sha256=checksum,
        folder_id=test_folder.id,
        dependency_id=test_dependency.id,
        uploaded_by="test-worker-id",
        version=1
    )
    db_session.add(file_record)
    db_session.commit()

    # Create actual file on disk
    file_path = storage_service.get_file_path(test_dependency.code, test_folder.path, "stored_checksum_test.pdf")
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(file_content)

    # Download file
    response = client.get(f"/files/{file_record.id}/download", headers=auth_headers_worker)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"] == 'attachment; filename="checksum_test.pdf"'
    assert response.headers["x-checksum-sha256"] == checksum

    # Verify downloaded content
    downloaded_content = b"".join(response.iter_bytes())
    assert downloaded_content == file_content

    # Verify checksum of downloaded content
    downloaded_checksum = hashlib.sha256(downloaded_content).hexdigest()
    assert downloaded_checksum == checksum

def test_update_file_versioning(client, auth_headers_worker, test_dependency, db_session):
    """Test updating file content with versioning"""
    # Create test folder
    from app.models.folder import Folder
    test_folder = Folder(
        id="test-version-folder",
        name="Version Test",
        path="Version Test",
        dependency_id=test_dependency.id,
        created_by="test-worker-id",
        updated_by="test-worker-id"
    )
    test_folder = db_session.merge(test_folder)

    # Create test file
    from app.models.file import File
    import uuid
    from app.services.storage_service import storage_service

    original_content = b"Original file content"
    original_checksum = hashlib.sha256(original_content).hexdigest()

    file_record = File(
        id=str(uuid.uuid4()),
        original_name="version_test.pdf",
        stored_name="stored_version_test.pdf",
        mime_type="application/pdf",
        size_bytes=len(original_content),
        checksum_sha256=original_checksum,
        folder_id=test_folder.id,
        dependency_id=test_dependency.id,
        uploaded_by="test-worker-id",
        version=1
    )
    db_session.add(file_record)
    db_session.commit()

    # Create original file on disk
    original_path = storage_service.get_file_path(test_dependency.code, test_folder.path, "stored_version_test.pdf")
    original_path.parent.mkdir(parents=True, exist_ok=True)
    original_path.write_bytes(original_content)

    # Update file with new content
    new_content = b"Updated file content with new version"
    new_checksum = hashlib.sha256(new_content).hexdigest()

    files = {"file": ("updated_version.pdf", BytesIO(new_content), "application/pdf")}
    response = client.put(f"/files/{file_record.id}", files=files, headers=auth_headers_worker)

    assert response.status_code == 200
    data = response.json()

    # Check version incremented
    assert data["version"] == 2
    assert data["original_name"] == "updated_version.pdf"
    assert data["size_bytes"] == len(new_content)

    # Verify new file exists
    new_stored_name = data["stored_name"]
    new_file_path = storage_service.get_file_path(test_dependency.code, test_folder.path, new_stored_name)
    assert new_file_path.exists()
    assert new_file_path.read_bytes() == new_content

def test_hard_delete_cascade_annexes(client, auth_headers_super_admin, test_dependency, db_session):
    """Test hard delete cascades to annexes"""
    # Create test folder
    from app.models.folder import Folder
    test_folder = Folder(
        id="test-cascade-folder",
        name="Cascade Test",
        path="Cascade Test",
        dependency_id=test_dependency.id,
        created_by="test-super-admin-id",
        updated_by="test-super-admin-id"
    )
    test_folder = db_session.merge(test_folder)

    # Create main file
    from app.models.file import File
    import uuid
    from app.services.storage_service import storage_service

    main_file_id = str(uuid.uuid4())
    main_file = File(
        id=main_file_id,
        original_name="main_contract.pdf",
        stored_name="stored_main.pdf",
        mime_type="application/pdf",
        size_bytes=100,
        checksum_sha256="checksum_main",
        folder_id=test_folder.id,
        dependency_id=test_dependency.id,
        uploaded_by="test-super-admin-id",
        version=1
    )
    db_session.add(main_file)

    # Create annex files
    annex1_id = str(uuid.uuid4())
    annex1 = File(
        id=annex1_id,
        original_name="annex1.pdf",
        stored_name="stored_annex1.pdf",
        mime_type="application/pdf",
        size_bytes=50,
        checksum_sha256="checksum_annex1",
        folder_id=test_folder.id,
        dependency_id=test_dependency.id,
        uploaded_by="test-super-admin-id",
        version=1,
        main_file_id=main_file_id
    )
    db_session.add(annex1)

    annex2_id = str(uuid.uuid4())
    annex2 = File(
        id=annex2_id,
        original_name="annex2.xlsx",
        stored_name="stored_annex2.xlsx",
        mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        size_bytes=75,
        checksum_sha256="checksum_annex2",
        folder_id=test_folder.id,
        dependency_id=test_dependency.id,
        uploaded_by="test-super-admin-id",
        version=1,
        main_file_id=main_file_id
    )
    db_session.add(annex2)
    db_session.commit()

    # Create files on disk
    for file_record in [main_file, annex1, annex2]:
        file_path = storage_service.get_file_path(test_dependency.code, test_folder.path, file_record.stored_name)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(b"test content for " + file_record.original_name.encode())

    # Hard delete main file
    response = client.delete(f"/files/{main_file_id}?hard=true", headers=auth_headers_super_admin)

    assert response.status_code == 200
    data = response.json()
    assert data["deleted"] == True
    assert len(data["deleted_files"]) == 3  # main + 2 annexes

    # Verify files are deleted from DB
    from app.models.file import File
    remaining_files = db_session.query(File).filter(
        File.id.in_([main_file_id, annex1_id, annex2_id])
    ).count()
    assert remaining_files == 0

    # Verify files moved to trash (or deleted from disk)
    # Note: In test environment, files might not be moved to trash

def test_soft_delete_file(client, auth_headers_worker, test_dependency, db_session):
    """Test soft delete marks file as deleted but keeps record"""
    # Create test folder and file
    from app.models.folder import Folder
    from app.models.file import File
    import uuid

    test_folder = Folder(
        id="test-soft-delete-folder",
        name="Soft Delete Test",
        path="Soft Delete Test",
        dependency_id=test_dependency.id,
        created_by="test-worker-id",
        updated_by="test-worker-id"
    )
    test_folder = db_session.merge(test_folder)

    file_record = File(
        id=str(uuid.uuid4()),
        original_name="soft_delete_test.pdf",
        stored_name="stored_soft_delete.pdf",
        mime_type="application/pdf",
        size_bytes=50,
        checksum_sha256="checksum_soft",
        folder_id=test_folder.id,
        dependency_id=test_dependency.id,
        uploaded_by="test-worker-id",
        version=1,
        is_deleted=False
    )
    db_session.add(file_record)
    db_session.commit()

    # Soft delete file
    response = client.delete(f"/files/{file_record.id}", headers=auth_headers_worker)

    assert response.status_code == 200
    data = response.json()
    assert data["deleted"] == True
    assert "marked as deleted" in data["message"]

    # Verify file is marked as deleted in DB
    db_session.refresh(file_record)
    assert file_record.is_deleted == True

def test_get_file_annexes(client, auth_headers_worker, test_dependency, db_session):
    """Test getting annex files for a main file"""
    # Create test folder
    from app.models.folder import Folder
    test_folder = Folder(
        id="test-annexes-folder",
        name="Annexes Test",
        path="Annexes Test",
        dependency_id=test_dependency.id,
        created_by="test-worker-id",
        updated_by="test-worker-id"
    )
    test_folder = db_session.merge(test_folder)

    # Create main file
    from app.models.file import File
    import uuid

    main_file_id = str(uuid.uuid4())
    main_file = File(
        id=main_file_id,
        original_name="main_file.pdf",
        stored_name="stored_main.pdf",
        mime_type="application/pdf",
        size_bytes=100,
        checksum_sha256="checksum_main",
        folder_id=test_folder.id,
        dependency_id=test_dependency.id,
        uploaded_by="test-worker-id",
        version=1
    )
    db_session.add(main_file)

    # Create annex files
    annex_files = []
    for i in range(3):
        annex = File(
            id=str(uuid.uuid4()),
            original_name=f"annex_{i}.pdf",
            stored_name=f"stored_annex_{i}.pdf",
            mime_type="application/pdf",
            size_bytes=50 + i * 10,
            checksum_sha256=f"checksum_annex_{i}",
            folder_id=test_folder.id,
            dependency_id=test_dependency.id,
            uploaded_by="test-worker-id",
            version=1,
            main_file_id=main_file_id
        )
        db_session.add(annex)
        annex_files.append(annex)

    db_session.commit()

    # Get annexes
    response = client.get(f"/files/{main_file_id}/anexos", headers=auth_headers_worker)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3

    # Verify all annexes are returned
    returned_ids = [annex["id"] for annex in data]
    expected_ids = [annex.id for annex in annex_files]

    for expected_id in expected_ids:
        assert expected_id in returned_ids

    # Verify all have main_file_id set correctly
    for annex in data:
        assert annex["main_file_id"] == main_file_id

def test_upload_permissions_worker_in_dependency(client, auth_headers_worker, worker_user, db_session):
    """Test that worker can upload to folders in their dependency"""
    # Create folder in worker's dependency
    from app.models.folder import Folder

    test_folder = Folder(
        id="worker-upload-folder",
        name="Worker Upload Test",
        path="Worker Upload Test",
        dependency_id=worker_user.dependency_id,
        created_by=worker_user.id,
        updated_by=worker_user.id
    )
    test_folder = db_session.merge(test_folder)
    db_session.commit()

    # Upload file
    files = {"file": ("worker_upload.pdf", BytesIO(b"Worker uploaded content"), "application/pdf")}
    data = {"folder_id": test_folder.id}

    response = client.post("/files/upload", files=files, data=data, headers=auth_headers_worker)

    assert response.status_code == 201

def test_upload_permissions_worker_wrong_dependency(client, auth_headers_worker, db_session):
    """Test that worker cannot upload to folders in other dependencies"""
    # Create folder in different dependency
    from app.models.dependency import Dependency
    from app.models.folder import Folder

    other_dep = Dependency(id="wrong-dep", name="Wrong Dep", code="WRONG")
    other_dep = db_session.merge(other_dep)

    wrong_folder = Folder(
        id="wrong-folder",
        name="Wrong Folder",
        path="Wrong Folder",
        dependency_id="wrong-dep",
        created_by="wrong-user",
        updated_by="wrong-user"
    )
    wrong_folder = db_session.merge(wrong_folder)
    db_session.commit()

    # Try to upload
    files = {"file": ("unauthorized.pdf", BytesIO(b"Unauthorized content"), "application/pdf")}
    data = {"folder_id": "wrong-folder"}

    response = client.post("/files/upload", files=files, data=data, headers=auth_headers_worker)

    assert response.status_code == 403
