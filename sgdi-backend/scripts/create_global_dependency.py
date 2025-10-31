#!/usr/bin/env python3
"""
Script to create the GLOBAL dependency for the Super Administrator.

This script creates a special "GLOBAL" dependency that is visible to all users,
where the Super Admin can upload documents that everyone can see (like policies,
general documents, etc.).

Usage:
    python scripts/create_global_dependency.py
"""

import os
import sys
import uuid
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import SessionLocal, engine, Base
from app.models.dependency import Dependency
from app.models.folder import Folder
from app.models.user import User
from app.core.logging_config import setup_logging

# Setup logging
setup_logging()

def create_global_dependency():
    """Create the GLOBAL dependency and assign it to Super Admin"""

    print("Creating GLOBAL dependency...")

    # Create database session
    db = SessionLocal()

    try:
        # Check if GLOBAL dependency already exists
        existing_global = db.query(Dependency).filter(
            Dependency.code == "GLOBAL"
        ).first()

        if existing_global:
            print(f"SUCCESS: GLOBAL dependency already exists (ID: {existing_global.id})")
            global_dependency = existing_global
        else:
            # Get or create system user for dependency creation
            system_user = db.query(User).filter(User.role == "SUPER_ADMIN").first()
            
            if not system_user:
                print("ERROR: No Super Admin user found. Please run seed_superadmin.py first.")
                sys.exit(1)

            # Create the GLOBAL dependency
            global_dependency = Dependency(
                id=str(uuid.uuid4()),
                code="GLOBAL",
                name="Global / Corporativo"
            )

            db.add(global_dependency)
            db.flush()

            # Create root folder for GLOBAL dependency
            root_folder = Folder(
                id=str(uuid.uuid4()),
                name="GLOBAL",
                path="GLOBAL",
                parent_id=None,
                dependency_id=global_dependency.id,
                created_by=system_user.id,
                updated_by=system_user.id
            )

            db.add(root_folder)
            db.flush()

            # Create some default folders
            default_folders = [
                {"name": "Políticas"},
                {"name": "Manuales"},
                {"name": "Formatos"},
                {"name": "Comunicados"}
            ]

            for folder_data in default_folders:
                subfolder = Folder(
                    id=str(uuid.uuid4()),
                    name=folder_data["name"],
                    path=f"GLOBAL/{folder_data['name']}",
                    parent_id=root_folder.id,
                    dependency_id=global_dependency.id,
                    created_by=system_user.id,
                    updated_by=system_user.id
                )
                db.add(subfolder)

            db.commit()
            db.refresh(global_dependency)

            print("SUCCESS: GLOBAL dependency created successfully!")
            print(f"  Dependency ID: {global_dependency.id}")
            print(f"  Code: {global_dependency.code}")
            print(f"  Name: {global_dependency.name}")
            print(f"  Root Folder: GLOBAL")
            print(f"  Default subfolders created: {len(default_folders)}")

        # Assign GLOBAL dependency to Super Admin
        print("\nAssigning GLOBAL dependency to Super Admin...")
        super_admin = db.query(User).filter(User.role == "SUPER_ADMIN").first()
        
        if super_admin:
            super_admin.dependency_id = global_dependency.id
            db.commit()
            print(f"SUCCESS: Super Admin ({super_admin.email}) assigned to GLOBAL dependency")
        else:
            print("WARNING: No Super Admin found to assign GLOBAL dependency")

        # Create physical directory
        storage_path = Path(os.getenv("STORAGE_PATH", "/app/storage"))
        global_dir = storage_path / "GLOBAL"
        global_dir.mkdir(parents=True, exist_ok=True)
        
        for folder_data in default_folders:
            subfolder_dir = global_dir / folder_data["name"]
            subfolder_dir.mkdir(parents=True, exist_ok=True)

        print(f"\nPhysical directories created at: {global_dir}")

    except Exception as e:
        print(f"ERROR: Failed to create GLOBAL dependency: {e}")
        db.rollback()
        sys.exit(1)

    finally:
        db.close()

def main():
    """Main function"""
    print("SGDI Global Dependency Setup Script")
    print("=" * 50)

    # Ensure database tables exist
    print("Ensuring database tables exist...")
    Base.metadata.create_all(bind=engine)

    # Create the GLOBAL dependency
    create_global_dependency()

    print("\nSetup completed successfully!")
    print("\nNOTE: All users will be able to VIEW files in the GLOBAL dependency.")
    print("Only Super Admin can UPLOAD/MODIFY/DELETE files in GLOBAL.\n")

if __name__ == "__main__":
    main()

