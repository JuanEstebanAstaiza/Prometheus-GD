#!/usr/bin/env python3
"""
Script to ensure models/__init__.py is correctly populated for Docker builds.
"""

import os

# Content for models/__init__.py
INIT_CONTENT = '''# This file contains model imports for the SGDI application
# Import Base from database module
from ..core.database import Base

# Import all model classes
from .user import User
from .dependency import Dependency
from .folder import Folder
from .file import File
from .action_logs import ActionLog
from .backup import BackupRecord
from .refresh_tokens import RefreshToken
from .audit import Audit

# Make sure this file has content to prevent it from being emptied
__version__ = "1.0.0"
'''

def main():
    init_file = "app/models/__init__.py"

    # Ensure the directory exists
    os.makedirs("app/models", exist_ok=True)

    # Write the content
    with open(init_file, 'w') as f:
        f.write(INIT_CONTENT)

    print("✅ Archivo __init__.py restaurado")

if __name__ == "__main__":
    main()