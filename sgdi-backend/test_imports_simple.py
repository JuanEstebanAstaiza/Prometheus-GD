#!/usr/bin/env python3
"""Simple test to verify model imports work"""

try:
    from app.models import User
    print("✅ User import successful")
except ImportError as e:
    print(f"❌ User import failed: {e}")
    exit(1)

try:
    from app.models import Dependency, Folder, File, ActionLog
    print("✅ All model imports successful")
except ImportError as e:
    print(f"❌ Model imports failed: {e}")
    exit(1)

print("🎉 All imports working!")
