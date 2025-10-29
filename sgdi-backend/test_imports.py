#!/usr/bin/env python3
"""Test script to verify all models can be imported"""

try:
    from app.models import User, Dependency, Folder, File, ActionLog, BackupRecord, RefreshToken, Audit
    print("✅ All models imported successfully!")

    # Test that Base is available
    from app.models import Base
    print("✅ Base imported successfully!")

    print("🎉 All imports working correctly!")
except ImportError as e:
    print(f"❌ Import error: {e}")
    exit(1)
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    exit(1)
