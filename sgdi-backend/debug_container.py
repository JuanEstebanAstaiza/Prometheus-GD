#!/usr/bin/env python3
"""
Debug script to check what's happening inside the container
"""

import os
import sys

print("=== DEBUG CONTAINER ===")
print(f"Python version: {sys.version}")
print(f"Current working directory: {os.getcwd()}")

# Check if app directory exists
if os.path.exists('app'):
    print("✅ app directory exists")
    if os.path.exists('app/models'):
        print("✅ app/models directory exists")
        files = os.listdir('app/models')
        print(f"Files in app/models: {files}")

        if '__init__.py' in files:
            print("✅ __init__.py exists")
            with open('app/models/__init__.py', 'r') as f:
                content = f.read()
                print(f"Content of __init__.py:\n{content}")
        else:
            print("❌ __init__.py does not exist")
    else:
        print("❌ app/models directory does not exist")
else:
    print("❌ app directory does not exist")

# Try to import models
print("\n=== TESTING IMPORTS ===")
try:
    from app.models import User, Dependency, Folder, File
    print("✅ All model imports successful!")
except ImportError as e:
    print(f"❌ Import error: {e}")

    # Try individual imports
    try:
        from app.core.database import Base
        print("✅ Base import successful")
    except ImportError as e:
        print(f"❌ Base import failed: {e}")

print("=== END DEBUG ===")
