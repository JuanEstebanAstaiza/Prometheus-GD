import pytest
from app.models import Folder

def test_create_root_folder(client, auth_headers_super_admin, test_dependency):
    """Test creating root folder for dependency"""
    response = client.post("/folders",
        json={
            "name": test_dependency.name,
            "dependency_id": test_dependency.id
        },
        headers=auth_headers_super_admin
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == test_dependency.name
    assert data["dependency_id"] == test_dependency.id
    assert data["path"] == test_dependency.name
    assert data["parent_id"] is None

def test_create_subfolder(client, auth_headers_super_admin, test_dependency, db_session):
    """Test creating subfolder"""
    # First create root folder
    root_response = client.post("/folders",
        json={
            "name": test_dependency.name,
            "dependency_id": test_dependency.id
        },
        headers=auth_headers_super_admin
    )
    root_folder = root_response.json()

    # Create subfolder
    response = client.post("/folders",
        json={
            "name": "Subfolder",
            "parent_id": root_folder["id"],
            "dependency_id": test_dependency.id
        },
        headers=auth_headers_super_admin
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Subfolder"
    assert data["parent_id"] == root_folder["id"]
    assert data["path"] == f"{test_dependency.name}/Subfolder"
    assert data["dependency_id"] == test_dependency.id

def test_folder_tree_view(client, auth_headers_super_admin, test_dependency):
    """Test folder tree view"""
    # Create folder structure
    root_response = client.post("/folders",
        json={
            "name": test_dependency.name,
            "dependency_id": test_dependency.id
        },
        headers=auth_headers_super_admin
    )
    root_folder = root_response.json()

    # Create subfolders
    sub1_response = client.post("/folders",
        json={
            "name": "Documents",
            "parent_id": root_folder["id"],
            "dependency_id": test_dependency.id
        },
        headers=auth_headers_super_admin
    )

    sub2_response = client.post("/folders",
        json={
            "name": "Images",
            "parent_id": root_folder["id"],
            "dependency_id": test_dependency.id
        },
        headers=auth_headers_super_admin
    )

    # Get tree
    response = client.get(f"/dependencies/{test_dependency.id}/folders/tree",
        headers=auth_headers_super_admin
    )

    assert response.status_code == 200
    tree = response.json()
    assert len(tree) == 1
    assert tree[0]["name"] == test_dependency.name
    assert len(tree[0]["children"]) == 2

    child_names = [child["name"] for child in tree[0]["children"]]
    assert "Documents" in child_names
    assert "Images" in child_names

def test_rename_folder_path_propagation(client, auth_headers_super_admin, test_dependency, db_session):
    """Test that renaming a folder propagates path changes to children"""
    # Create folder structure: Root -> FolderA -> FolderB
    root_response = client.post("/folders",
        json={
            "name": test_dependency.name,
            "dependency_id": test_dependency.id
        },
        headers=auth_headers_super_admin
    )
    root_folder = root_response.json()

    folder_a_response = client.post("/folders",
        json={
            "name": "FolderA",
            "parent_id": root_folder["id"],
            "dependency_id": test_dependency.id
        },
        headers=auth_headers_super_admin
    )
    folder_a = folder_a_response.json()

    folder_b_response = client.post("/folders",
        json={
            "name": "FolderB",
            "parent_id": folder_a["id"],
            "dependency_id": test_dependency.id
        },
        headers=auth_headers_super_admin
    )
    folder_b = folder_b_response.json()

    # Verify initial paths
    assert folder_a["path"] == f"{test_dependency.name}/FolderA"
    assert folder_b["path"] == f"{test_dependency.name}/FolderA/FolderB"

    # Rename FolderA to FolderRenamed
    response = client.put(f"/folders/{folder_a['id']}",
        json={"name": "FolderRenamed"},
        headers=auth_headers_super_admin
    )

    assert response.status_code == 200
    updated_folder_a = response.json()
    assert updated_folder_a["name"] == "FolderRenamed"
    assert updated_folder_a["path"] == f"{test_dependency.name}/FolderRenamed"

    # Check that FolderB path was updated
    folder_b_response = client.get(f"/folders/{folder_b['id']}",
        headers=auth_headers_super_admin
    )
    updated_folder_b = folder_b_response.json()
    assert updated_folder_b["path"] == f"{test_dependency.name}/FolderRenamed/FolderB"

def test_move_folder_path_propagation(client, auth_headers_super_admin, test_dependency, db_session):
    """Test that moving a folder propagates path changes to children"""
    # Create folder structure: Root -> FolderA -> FolderB
    # And another folder: Root -> FolderC
    root_response = client.post("/folders",
        json={
            "name": test_dependency.name,
            "dependency_id": test_dependency.id
        },
        headers=auth_headers_super_admin
    )
    root_folder = root_response.json()

    folder_a_response = client.post("/folders",
        json={
            "name": "FolderA",
            "parent_id": root_folder["id"],
            "dependency_id": test_dependency.id
        },
        headers=auth_headers_super_admin
    )
    folder_a = folder_a_response.json()

    folder_b_response = client.post("/folders",
        json={
            "name": "FolderB",
            "parent_id": folder_a["id"],
            "dependency_id": test_dependency.id
        },
        headers=auth_headers_super_admin
    )
    folder_b = folder_b_response.json()

    folder_c_response = client.post("/folders",
        json={
            "name": "FolderC",
            "parent_id": root_folder["id"],
            "dependency_id": test_dependency.id
        },
        headers=auth_headers_super_admin
    )
    folder_c = folder_c_response.json()

    # Move FolderA under FolderC
    response = client.put(f"/folders/{folder_a['id']}",
        json={"parent_id": folder_c["id"]},
        headers=auth_headers_super_admin
    )

    assert response.status_code == 200
    updated_folder_a = response.json()
    assert updated_folder_a["parent_id"] == folder_c["id"]
    assert updated_folder_a["path"] == f"{test_dependency.name}/FolderC/FolderA"

    # Check that FolderB path was updated
    folder_b_response = client.get(f"/folders/{folder_b['id']}",
        headers=auth_headers_super_admin
    )
    updated_folder_b = folder_b_response.json()
    assert updated_folder_b["path"] == f"{test_dependency.name}/FolderC/FolderA/FolderB"

def test_delete_folder_empty(client, auth_headers_super_admin, test_dependency):
    """Test deleting empty folder"""
    # Create folder
    folder_response = client.post("/folders",
        json={
            "name": "EmptyFolder",
            "dependency_id": test_dependency.id
        },
        headers=auth_headers_super_admin
    )
    folder = folder_response.json()

    # Delete folder
    response = client.delete(f"/folders/{folder['id']}",
        headers=auth_headers_super_admin
    )

    assert response.status_code == 200
    assert response.json()["deleted"] == True

def test_delete_folder_with_contents_force(client, auth_headers_super_admin, test_dependency):
    """Test deleting folder with contents using force"""
    # Create folder with subfolder
    folder_response = client.post("/folders",
        json={
            "name": "ParentFolder",
            "dependency_id": test_dependency.id
        },
        headers=auth_headers_super_admin
    )
    parent_folder = folder_response.json()

    subfolder_response = client.post("/folders",
        json={
            "name": "ChildFolder",
            "parent_id": parent_folder["id"],
            "dependency_id": test_dependency.id
        },
        headers=auth_headers_super_admin
    )
    subfolder = subfolder_response.json()

    # Try to delete without force (should fail)
    response = client.delete(f"/folders/{parent_folder['id']}",
        headers=auth_headers_super_admin
    )

    assert response.status_code == 200
    assert response.json()["deleted"] == False
    assert "contains" in response.json()["message"].lower()

    # Delete with force
    response = client.delete(f"/folders/{parent_folder['id']}?force=true",
        headers=auth_headers_super_admin
    )

    assert response.status_code == 200
    assert response.json()["deleted"] == True

def test_folder_permissions_super_admin(client, auth_headers_super_admin, test_dependency):
    """Test that super admin can create folders in any dependency"""
    response = client.post("/folders",
        json={
            "name": "SuperAdminFolder",
            "dependency_id": test_dependency.id
        },
        headers=auth_headers_super_admin
    )

    assert response.status_code == 201

def test_folder_permissions_admin_dep(client, auth_headers_admin_dep, admin_dep_user, test_dependency):
    """Test that admin dep can create folders in their dependency"""
    # Update test_dependency to be the admin's dependency
    test_dependency.id = admin_dep_user.dependency_id
    test_dependency.code = "ADMINDEP"
    test_dependency.name = "Admin Dep Test"

    response = client.post("/folders",
        json={
            "name": "AdminDepFolder",
            "dependency_id": admin_dep_user.dependency_id
        },
        headers=auth_headers_admin_dep
    )

    assert response.status_code == 201

def test_folder_permissions_admin_dep_wrong_dependency(client, auth_headers_admin_dep, test_dependency):
    """Test that admin dep cannot create folders in other dependencies"""
    response = client.post("/folders",
        json={
            "name": "WrongDepFolder",
            "dependency_id": test_dependency.id  # Different dependency
        },
        headers=auth_headers_admin_dep
    )

    assert response.status_code == 403

def test_folder_validation_duplicate_name(client, auth_headers_super_admin, test_dependency):
    """Test folder name uniqueness validation"""
    # Create first folder
    client.post("/folders",
        json={
            "name": "DuplicateName",
            "dependency_id": test_dependency.id
        },
        headers=auth_headers_super_admin
    )

    # Try to create second folder with same name in same location
    response = client.post("/folders",
        json={
            "name": "DuplicateName",
            "dependency_id": test_dependency.id
        },
        headers=auth_headers_super_admin
    )

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]

def test_monthly_folder_creation_simulation(client, auth_headers_super_admin, test_dependency, db_session):
    """Test monthly folder creation (simulation of scheduled job)"""
    # This simulates what the monthly folder job would do
    from datetime import datetime
    current_month = datetime.utcnow().strftime("%Y-%m")
    monthly_folder_name = f"{current_month}"

    # Create monthly folder
    response = client.post("/folders",
        json={
            "name": monthly_folder_name,
            "dependency_id": test_dependency.id
        },
        headers=auth_headers_super_admin
    )

    assert response.status_code == 201
    folder = response.json()
    assert folder["name"] == monthly_folder_name
    assert folder["path"] == monthly_folder_name

def test_folder_path_computation_complex(client, auth_headers_super_admin, test_dependency):
    """Test complex folder path computation"""
    # Create deep folder structure
    level1_response = client.post("/folders",
        json={
            "name": "Level1",
            "dependency_id": test_dependency.id
        },
        headers=auth_headers_super_admin
    )
    level1 = level1_response.json()

    level2_response = client.post("/folders",
        json={
            "name": "Level2",
            "parent_id": level1["id"],
            "dependency_id": test_dependency.id
        },
        headers=auth_headers_super_admin
    )
    level2 = level2_response.json()

    level3_response = client.post("/folders",
        json={
            "name": "Level3",
            "parent_id": level2["id"],
            "dependency_id": test_dependency.id
        },
        headers=auth_headers_super_admin
    )
    level3 = level3_response.json()

    # Verify paths
    assert level1["path"] == "Level1"
    assert level2["path"] == "Level1/Level2"
    assert level3["path"] == "Level1/Level2/Level3"
