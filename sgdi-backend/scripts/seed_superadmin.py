#!/usr/bin/env python3
"""
Script to seed the initial superadmin user.

This script creates the first superadmin user in the system.
It reads configuration from environment variables and creates
the user if it doesn't already exist.

Environment Variables:
- SUPERADMIN_EMAIL: Email for the superadmin user (default: admin@sgdi.local)
- SUPERADMIN_PASSWORD: Password for the superadmin user (required)
- SUPERADMIN_FULL_NAME: Full name for the superadmin user (default: "System Administrator")

Usage:
    python scripts/seed_superadmin.py

Or set environment variables:
    SUPERADMIN_EMAIL=admin@example.com SUPERADMIN_PASSWORD=securepass python scripts/seed_superadmin.py
"""

import os
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import SessionLocal, engine, Base
from app.core.security import get_password_hash
from app.models.user import User
from app.core.logging_config import setup_logging

# Setup logging
setup_logging()

def create_superadmin():
    """Create the initial superadmin user"""

    # Read configuration from environment
    superadmin_email = os.getenv("SUPERADMIN_EMAIL", "admin@sgdi.local")
    superadmin_password = os.getenv("SUPERADMIN_PASSWORD")
    superadmin_full_name = os.getenv("SUPERADMIN_FULL_NAME", "System Administrator")

    if not superadmin_password:
        print("ERROR: SUPERADMIN_PASSWORD environment variable is required")
        sys.exit(1)

    if len(superadmin_password) < 8:
        print("ERROR: SUPERADMIN_PASSWORD must be at least 8 characters long")
        sys.exit(1)

    print(f"Creating superadmin user: {superadmin_email}")

    # Create database session
    db = SessionLocal()

    try:
        # Check if superadmin already exists
        existing_superadmin = db.query(User).filter(
            User.email == superadmin_email
        ).first()

        if existing_superadmin:
            if existing_superadmin.role == "SUPER_ADMIN":
                print(f"SUCCESS: Superadmin user already exists: {superadmin_email}")
                return
            else:
                print(f"ERROR: User with email {superadmin_email} exists but is not a superadmin")
                sys.exit(1)

        # Create the superadmin user
        hashed_password = get_password_hash(superadmin_password)

        superadmin_user = User(
            email=superadmin_email,
            full_name=superadmin_full_name,
            password_hash=hashed_password,
            role="SUPER_ADMIN",
            dependency_id=None,  # Superadmin has no dependency
            is_active=True
        )

        db.add(superadmin_user)
        db.commit()
        db.refresh(superadmin_user)

        print("SUCCESS: Superadmin user created successfully!")
        print(f"  Email: {superadmin_email}")
        print(f"  Full Name: {superadmin_full_name}")
        print(f"  Role: SUPER_ADMIN")
        print(f"  User ID: {superadmin_user.id}")
        print("\nIMPORTANT: Store these credentials securely and delete this output!")

    except Exception as e:
        print(f"ERROR: Failed to create superadmin user: {e}")
        db.rollback()
        sys.exit(1)

    finally:
        db.close()

def main():
    """Main function"""
    print("SGDI Superadmin Seeding Script")
    print("=" * 40)

    # Ensure database tables exist
    print("Ensuring database tables exist...")
    Base.metadata.create_all(bind=engine)

    # Create the superadmin user
    create_superadmin()

    print("\nSeeding completed successfully!")

if __name__ == "__main__":
    main()